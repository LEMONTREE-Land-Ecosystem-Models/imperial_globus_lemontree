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

* variable name in VAR
* output dir suffix in OUTDIR_SUFFIX
* optional packing flag in PACK, packs the float into uint16
* the earliest year to process in YEARONE
"""

# TODO - look at gathering to save space - cf-python implements reading and
#        unpacking back to 2D really elegantly but xarray and netcdf4 read the
#        fine but need unpacking separately (not built in)

# Environment variables
var = os.getenv("VAR")
outdir_suffix = os.getenv("OUTDIR_SUFFIX")
pack = bool(os.getenv("PACK")) | False
yearone = int(os.getenv("YEARONE"))

arrind = os.getenv("PBS_ARRAY_INDEX")
year = yearone + int(arrind) - 1

sys.stdout.write(
    f"In Py and running:\n  VAR: {var}\n  "
    f"OUTDIR_SUFFIX: {outdir_suffix}\n" 
    f"  YEAR: {year}\n  PACKING: {pack}\n"
)
sys.stdout.flush()


# Other variables
# Regex for the file date
yr_regex = re.compile('A([0-9]{4})([0-9]{3})')

# Hard code leap years
leap = [1972, 1976, 1980, 1984, 1988, 1992, 1996, 2000, 2004, 2008, 2016, 2020]


# Location of the root directory
dir_root = "/rds/general/project/lemontree/ephemeral/SNU_data_sharing_Sep_2022"

# Get memory profiler
process = psutil.Process(os.getpid())

def report_mem(process, prefix='') -> None:
    """Report on memory usage."""
    mem = process.memory_info()[0] / float(2 ** 30)
    sys.stdout.write(f"{prefix}Memory usage: {mem}\n")
    sys.stdout.flush()

# Variable dictionary
var_dict = {
    "FPAR": {
        # "canonical_name": "fraction_of_surface_downwelling_photosynthetic_radiative_flux_absorbed_by_vegetation",
        "scale_factor": 64000,  # Mapping 0 - 1 into 0 - 64000
        "add_offset": None,
        "unit": "1",
        "fill": -10
        },
    "LAI": {
        # "canonical_name": "leaf_area_index",
        "scale_factor": 6400,  # Mapping 0 - 10 into 0 - 64000
        "add_offset": None,
        "unit": "1",
        "fill": -10
        },
    "PAR": {
        # "canonical_name": "surface_downwelling_photosynthetic_radiative_flux_in_air",
        "scale_factor": 800,  # Mapping 0 - 80 into 0 - 64000
        "add_offset": None,
        "unit": "W m-2",
        "fill": -10
        },
    "Rg": {
        # "canonical_name": "????",
        "scale_factor": 1280,  # Mapping 0 - 50 into 0 - 64000
        "add_offset": None,
        "unit": "1",
        "fill": -10
        },
    "NIRv": {
        # "canonical_name": "????",
        "scale_factor": 10000,  # Mapping -0.1 - 0.5 into 0 - 60000
        "add_offset": -0.1,
        "unit": "1",
        "fill": -1
        }
}

# Get the details for this variable
var_info = var_dict.get(var, None)

if var_info is None:
    raise ValueError(f"Unknown variable: {var}")

# Recursive search for all files across years - directory structure is variable - and
# then filter down to the requested year
input_file_dir = os.path.join(dir_root, f'{var}_daily_005d_V1')
input_year_files = Path(input_file_dir).rglob(f'{var}_Daily_005d.*.nc')

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
base_grid = np.ndarray((len(year_files), len(latitude), len(longitude)), dtype="uint16")

# Loop over the files
for day_idx, this_file in year_files:

    report_mem(process, f"Loading day: {day_idx}; ")

    # Load
    mat = xarray.load_dataarray(this_file)

    # Set missing values
    mat = mat.where(mat != var_info['fill'])

    # Encode to uint16
    mat_np


    # insert into the correct day of year
    base_grid[day_idx, :, :] = mat_data_unpack


# Reporting
report_mem(process, "Data loaded; ")

sys.stdout.write(f"Range: {np.nanmin(base_grid)} {np.nanmax(base_grid)}\n")
sys.stdout.flush()

# Create the xarray object holding the data
dates = sorted(
    [datetime.datetime(year, 1, 1) + datetime.timedelta(d - 1) for d in days]
)


print("dates created", end="\n", flush=True)


# Optional manual conversion to uint16
#  - xarray does provide the 'encoding' argument to to_netcdf(), but the memory
#    management of this (make copy, set NA, cast copy) uses 2.5 x data in RAM, with
#    some odd spikes. This conversion does that manually and sets attributes directly
if pack:

    print(f"Scaling: {base_grid.shape}", end="\n", flush=True)


    out_data =  np.round(base_grid * scale_factor, 0)
    print(f"Scaled: {np.nanmin(out_data)} - {np.nanmax(out_data)}", end="\n", flush=True)
    
    out_data[np.isnan(out_data)] = 65535
    print("Filled", end="\n", flush=True)
    
    out_data = out_data.astype('uint16')
    print("Cast", end="\n", flush=True)

    # Reporting
    report_mem(process, "Conversion complete; ")

    xds = xarray.DataArray(
        out_data,
        coords=[dates, latitude, longitude],
        dims=["time", "latitude", "longitude"],
        name=var,
        attrs={
            "units": unit,
            "scale_factor": 1 / scale_factor,
            "_FillValue": 65535,
            "standard_name": canonical_name,
        }
    )
else:
    xds = xarray.DataArray(
        base_grid,
        coords=[dates, latitude, longitude],
        dims=["time", "latitude", "longitude"],
        name=var,
        attrs={
            "units": unit,
            "standard_name": canonical_name,
        },
    )

report_mem(process, "DataArray created; ")

# Save to disk - creating output directory
out_dir = os.path.join(dir_root, f"{var}_{outdir_suffix}")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, f"{var}_{year}.nc")

xds.to_netcdf(out_file, encoding={var: {"zlib": True, "complevel": 6}})
