"""Encodes monthly files from double to uint16.

This script uses xarray encoding to compress the file sizes from float32 to uint16.

The script is intended to be submitted with an array job to loop over years with the
following environment variables set:

* variable name in VAR - used to identify sets of attributes for processing
* output dir suffix in OUTDIR_SUFFIX
* the earliest year to process in YEARONE
"""

import os
import re
import sys
from pathlib import Path

import numpy as np
import psutil
import xarray

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
yr_regex = re.compile("_([0-9]{4})_")

# Location of the root directory
dir_root = "/rds/general/project/lemontree/live/incoming"

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
        "scale_factor": 59000,  # Mapping -0.1 - 1.0 into 0 - 64900
        "add_offset": -0.1,
        "fill": -1,
        # Set inf and values > 1.0 (all above ~1.5) to NA 
        "discard_above": 1.0,
        "clamp_below": None,
        "encode_type": np.uint16,
        "missing_value": 65535,
    },
    "MCD43C4": {
        "file_var": "MCD43C4",
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
file_var = var_info["file_var"]

# Get the files to encode
input_file_dir = os.path.join(dir_root, f"{file_var}_raw")
input_year_files = Path(input_file_dir).glob(f"{file_var}*.nc")

year_filter = [(yr_regex.search(p.name).groups(), p) for p in input_year_files]
year_filter.sort()
year_files = [fl for ((yr,), fl) in year_filter if int(yr) == year]

# Loop over months
for this_month in year_files:

    # Load the data
    mat = xarray.load_dataset(this_month)
    mat = mat[file_var]

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

    # Manual unit16 encoding
    # - xarray does provide the 'encoding' argument to to_netcdf(), but the memory
    #   management of this (make copy, set NA, cast copy) uses 2.5 x data in RAM, with
    #   some odd spikes. This script does that manually and sets attributes directly.

    if (var_info["add_offset"] is not None) and (var_info["scale_factor"] is not None):
        mat_cast = np.round(
            (mat - var_info["add_offset"]) * var_info["scale_factor"], 0
        ).astype(var_info["encode_type"])
    else:
        mat_cast = mat.astype(var_info["encode_type"])

    # Set the NULL VALUE
    mat_cast = mat_cast.where(mat.notnull(), NULL_VALUE)

    # Reporting
    report_mem(process, "Data loaded; ")

    # Extend the existing variable attributes
    var_attrs = {
        **mat.attrs,
        "_FillValue": NULL_VALUE,
    }

    if var_info["scale_factor"] is not None:
        var_attrs["scale_factor"] = 1 / var_info["scale_factor"]

    if var_info["add_offset"] is not None:
        var_attrs["add_offset"] = var_info["add_offset"]

    if var_info["discard_above"] is not None:
        var_attrs[
            "discard_above"
        ] = f"Values above {var_info['discard_above']} set to missing"

    if var_info["clamp_below"] is not None:
        var_attrs[
            "clamp_below"
        ] = f"Values below {var_info['clamp_below']} set to {var_info['clamp_below']}"

    # Remove the 'fill' attribute - old NA value
    if "fill" in var_attrs:
        del var_attrs["fill"]

    xds = xarray.DataArray(
        mat_cast,
        coords=[mat["time"], mat["latitude"], mat["longitude"]],
        dims=["time", "latitude", "longitude"],
        name=file_var,
        attrs=var_attrs,
    )

    report_mem(process, "DataArray created; ")

    # Save to disk - creating output directory
    out_dir = os.path.join(dir_root, f"{var}_{outdir_suffix}")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, this_month.name)

    xds.to_netcdf(out_file, encoding={file_var: {"zlib": True, "complevel": 6}})
