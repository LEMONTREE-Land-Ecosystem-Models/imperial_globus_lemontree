import os
import sys
import datetime
import re
from pathlib import Path

import numpy as np
import xarray
import psutil

"""
This script is used to compile individual daily files from SNU into more easily useable
annual files. It also uses encoding to compress the file sizes from float32 to uint16.

The script is intended to be submitted with an array job to loop over years with the
following environment variables set:

* variable name in VAR - used to identify sets of attributes for processing
* output dir suffix in OUTDIR_SUFFIX
* the earliest year to process in YEARONE
"""

# TODO - look at gathering to save space - cf-python implements reading and
#        unpacking back to 2D really elegantly but xarray and netcdf4 read the
#        fine but need unpacking separately (not built in)

# Environment variables
var = os.getenv("VAR")
outdir_suffix = os.getenv("OUTDIR_SUFFIX")
yearone = int(os.getenv("YEARONE"))

arrind = os.getenv("PBS_ARRAY_INDEX")
year = yearone + int(arrind) - 1

sys.stdout.write(
    f"In Py and running:\n  VAR: {var}\n  "
    f"OUTDIR_SUFFIX: {outdir_suffix}\n"
    f"  YEAR: {year}\n"
)
sys.stdout.flush()


# Other variables
# Regex for the file date
yr_regex = re.compile("A([0-9]{4})([0-9]{3})")

# # Hard code leap years
# leap = [1972, 1976, 1980, 1984, 1988, 1992, 1996, 2000, 2004, 2008, 2016, 2020]

# Location of the root directory
dir_root = "/rds/general/project/lemontree/ephemeral/SNU_data_sharing_Sep_2022"

# Get memory profiler
process = psutil.Process(os.getpid())


def report_mem(process, prefix="") -> None:
    """Report on memory usage."""
    mem = process.memory_info()[0] / float(2**30)
    sys.stdout.write(f"{prefix}Memory usage: {mem}\n")
    sys.stdout.flush()


# Variable dictionary
var_dict = {
    "FPAR": {
        "file_var": "FPAR",
        "data_var": "FPAR",
        "scale_factor": 64000,  # Mapping 0 - 1 into 0 - 64000
        "add_offset": 0,
        "fill": -10,
        # Throw away values over 1 and set <0 to zero
        "discard_above": 1,
        "clamp_below": 0,
        "encode_type": np.uint16,
        "missing_value": 65535,
    },
    "LAI": {
        "file_var": "LAI",
        "data_var": "LAI",
        "scale_factor": 6400,  # Mapping 0 - 10 into 0 - 64000
        "add_offset": 0,
        "fill": -10,
        # No edits to raw data
        "discard_above": None,
        "clamp_below": None,
        "encode_type": np.uint16,
        "missing_value": 65535,
    },
    "PAR": {
        "file_var": "PAR",
        "data_var": "PAR",
        "scale_factor": 500,  # Mapping 0 - 128 into 0 - 64000
        "add_offset": 0,
        "fill": -10,
        # Set <0  to zero
        "discard_above": None,
        "clamp_below": 0,
        "encode_type": np.uint16,
        "missing_value": 65535,
    },
    "Rg": {
        "file_var": "Rg",
        "data_var": "Rg",
        "scale_factor": 1280,  # Mapping 0 - 50 into 0 - 64000
        "add_offset": 0,
        "fill": -10,
        # Set <0  to zero
        "discard_above": None,
        "clamp_below": 0,
        "encode_type": np.uint16,
        "missing_value": 65535,
    },
    "NIRv": {
        "file_var": "NIRv",
        "data_var": "NIRv",
        "scale_factor": 75000,  # Mapping -0.1 - 0.755 into 0 - 64000
        "add_offset": -0.1,
        "fill": -1,
        # Set inf values to NA using arbitrary large value
        "discard_above": 1e7,
        "clamp_below": None,
        "encode_type": np.uint16,
        "missing_value": 65535,
    },
    "MCD43C4": {
        "file_var": "NIRv",
        "data_var": "MCD43C4 qc",
        "scale_factor": None,  # Already integer encoding
        "add_offset": None,
        "fill": 255,
        # Throw away values over 1 and set <0 to zero
        "discard_above": None,
        "clamp_below": None,
        "encode_type": np.uint8,
        "missing_value": 255,
    },
}


# Get the details for this variable
var_info = var_dict.get(var, None)

if var_info is None:
    raise ValueError(f"Unknown variable: {var}")

# Use 65535 in files as missing data
NULL_VALUE = var_info["missing_value"]

# Recursive search for all files across years - directory structure is variable - and
# then filter down to the requested year
input_file_dir = os.path.join(dir_root, f"{var}_daily_005d_V1")
input_year_files = Path(input_file_dir).rglob(f"{var}_Daily_005d.*.nc")

# Jeepers, this is quick. 15K files almost instantly.
year_filter = [(yr_regex.search(p.name).groups(), p) for p in input_year_files]
year_filter.sort()
year_files = [(int(dy), fl) for ((yr, dy), fl) in year_filter if int(yr) == year]

# Create lat and long dimensions using cell centres: note _deliberate_
# overrun at end of sequence to avoid clipping last value
res = 0.05
longitude = np.arange(-180 + res / 2, 180, res)
latitude = np.arange(90 - res / 2, -90, -res)

# Make a 3D array in uint16 to complete for the year following CF TZYX recommendation
base_grid = np.ndarray(
    (len(year_files), len(latitude), len(longitude)), dtype=var_info["encode_type"]
)

# Loop over the files
for day_idx, this_file in year_files:

    report_mem(process, f"Loading day: {day_idx}; ")

    # Load the data and reduce to the data array (this is really just about handling
    # NIRv and the NIRv QA - all the rest are single data variable)
    mat = xarray.load_dataset(this_file)
    mat = mat[var_info["data_var"]]

    # Set missing values - note that the test in DataArray.where() identifies the values
    # to _keep_, and the other values are replaced by the second value (default NA)
    mat = mat.where(mat != var_info["fill"])

    # Data tidying - set nulls first and then clamp. Need to explicitly exclude nulls
    # from clamping operations.
    if var_info["discard_above"] is not None:
        mat = mat.where(mat <= var_info["discard_above"])

    if var_info["clamp_below"] is not None:
        mat = mat.where(
            (mat >= var_info["clamp_below"]) | mat.isnull(), var_info["clamp_below"]
        )

    # Encode
    if (var_info["add_offset"] is not None) and (var_info["scale_factor"] is not None):
        mat_np = np.round(
            (mat + var_info["add_offset"]) * var_info["scale_factor"], 0
        ).astype(var_info["encode_type"])
    else:
        mat_np = mat.astype(var_info["encode_type"])

    mat_np = mat_np.where(mat.notnull(), NULL_VALUE)

    # insert into the correct day of year
    base_grid[day_idx - 1, :, :] = mat_np.T


# Reporting
report_mem(process, "Data loaded; ")

sys.stdout.write(f"Range: {np.nanmin(base_grid)} {np.nanmax(base_grid)}\n")
sys.stdout.flush()

# Create the xarray object holding the data
days = np.array([d - 1 for d, _ in year_files])
dates = np.datetime64(str(year), "D") + days.astype("timedelta64[D]")


print("dates created", end="\n", flush=True)

#  Manual unit16 encoding
#  - xarray does provide the 'encoding' argument to to_netcdf(), but the memory
#    management of this (make copy, set NA, cast copy) uses 2.5 x data in RAM, with
#    some odd spikes. This script does that manually and sets attributes directly.

# Extend the existing variable attributes
var_attrs = {
    **mat.attrs,
    "_FillValue": NULL_VALUE,
}

if var_info["scale_factor"] is not None:
    var_attrs["scale_factor"] = 1 / var_info["scale_factor"]

if var_info["add_offset"] is not None:
    var_attrs["add_offset"] = 1 / var_info["add_offset"]

if var_info["discard_above"] is not None:
    var_attrs[
        "discard_above"
    ] = f"Values above {var_info['discard_above']} set to missing"

if var_info["clamp_below"] is not None:
    var_attrs[
        "clamp_below"
    ] = f"Values below {var_info['clamp_below']} set to {var_info['clamp_below']}"

xds = xarray.DataArray(
    base_grid,
    coords=[
        dates,
        xarray.DataArray(latitude, attrs=mat["lat"].attrs),
        xarray.DataArray(longitude, attrs=mat["lon"].attrs),
    ],
    dims=["time", "latitude", "longitude"],
    name=var_info["data_var"],
    attrs=var_attrs,
)

report_mem(process, "DataArray created; ")

# Save to disk - creating output directory
out_dir = os.path.join(dir_root, f"{var}_{outdir_suffix}")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, f"{var}_{year}.nc")

xds.to_netcdf(out_file, encoding={var_info["data_var"]: {"zlib": True, "complevel": 6}})
