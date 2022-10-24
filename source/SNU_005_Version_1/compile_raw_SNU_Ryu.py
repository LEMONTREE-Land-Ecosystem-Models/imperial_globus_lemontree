"""Compile daily files to monthly.

This script is used to compile individual daily files from SNU into monthly files.

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
    },
    "LAI": {
        "file_var": "LAI",
        "data_var": "LAI",
    },
    "PAR": {
        "file_var": "PAR",
        "data_var": "PAR",
    },
    "Rg": {
        "file_var": "Rg",
        "data_var": "Rg",
    },
    "NIRv": {
        "file_var": "NIRv",
        "data_var": "NIRv",
    },
    "MCD43C4": {
        "file_var": "NIRv",
        "data_var": "MCD43C4 qc",
    },
}


# Get the details for this variable
var_info = var_dict.get(var, None)

if var_info is None:
    raise ValueError(f"Unknown variable: {var}")

file_var = var_info["file_var"]

# Recursive search for all files across years - directory structure is variable - and
# then filter down to the requested year
input_file_dir = os.path.join(dir_root, f"{file_var}_daily_005d_V1")
input_year_files = Path(input_file_dir).rglob(f"{file_var}_Daily_005d.*.nc")

year_filter = [(yr_regex.search(p.name).groups(), p) for p in input_year_files]
year_filter.sort()
year_files = [(int(dy), fl) for ((yr, dy), fl) in year_filter if int(yr) == year]

# Create dates and split by months
days = np.array([d - 1 for d, _ in year_files])
dates = np.datetime64(str(year), "D") + days.astype("timedelta64[D]")
months = dates.astype("datetime64[M]").astype(int) % 12 + 1

# Create lat and long dimensions using cell centres: note _deliberate_
# overrun at end of sequence to avoid clipping last value
res = 0.05
longitude = np.arange(-180 + res / 2, 180, res)
latitude = np.arange(90 - res / 2, -90, -res)

# Loop over months
for this_month in np.arange(1, 13):

    # Reduce to monthly files - should preserve order
    month_files = [df for df, m in zip(year_files, months) if m == this_month]

    # Make a 3D array in uint16 to complete for the year following
    # CF TZYX recommendation
    base_grid = np.ndarray((len(month_files), len(latitude), len(longitude)))

    # Loop over the files
    for day_idx, (day_num, this_file) in enumerate(month_files):

        report_mem(process, f"Loading day: {day_idx}; ")

        # Load the data and reduce to the data array (this is really just about
        # handling NIRv and the NIRv QA - all the rest are single data variable)
        mat = xarray.load_dataset(this_file)
        mat = mat[var_info["data_var"]]

        # insert into the correct day of year
        base_grid[day_idx - 1, :, :] = mat.T

    # Reporting
    report_mem(process, "Data loaded; ")

    sys.stdout.write(f"Range: {np.nanmin(base_grid)} {np.nanmax(base_grid)}\n")
    sys.stdout.flush()

    xds = xarray.DataArray(
        base_grid,
        coords=[
            dates[months == this_month],
            xarray.DataArray(latitude, attrs=mat["lat"].attrs),
            xarray.DataArray(longitude, attrs=mat["lon"].attrs),
        ],
        dims=["time", "latitude", "longitude"],
        name=var_info["data_var"],
        attrs=mat.attrs,
    )

    report_mem(process, "DataArray created; ")

    # Save to disk - creating output directory
    out_dir = os.path.join(dir_root, f"{var}_{outdir_suffix}")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{var}_{year}_{this_month}.nc")

    xds.to_netcdf(
        out_file, encoding={var_info["data_var"]: {"zlib": True, "complevel": 6}}
    )
