import os
import sys
import glob
import datetime

import scipy.io as sio
import numpy as np
import xarray
import psutil

# TODO - look at gathering to save space - cf-python implements reading and
#        unpacking back to 2D really elegantly but xarray and netcdf4 read the
#        fine but need unpacking separately (not built in)

# Needs to be submitted with an array job to loop over years with env variables:
# * variable name in VAR
# * output dir suffix in OUTDIR_SUFFIX
# * optional packing flag in PACK, packs the float into uint16

var = os.getenv("VAR")
outdir_suffix = os.getenv("OUTDIR_SUFFIX")
pack = bool(os.getenv("PACK")) | False

arrind = os.getenv("PBS_ARRAY_INDEX")
year = 1999 + int(arrind)

sys.stdout.write(
    f"In Py and running:\n  VAR: {var}\n  OUTDIR_SUFFIX: {outdir_suffix}\n" 
    f"  YEAR: {year}\n  PACKING: {pack}\n"
)
sys.stdout.flush()

# Get memory profiler
process = psutil.Process(os.getpid())

def report_mem(process, prefix=''):

    mem = process.memory_info()[0] / float(2 ** 30)
    sys.stdout.write(f"{prefix}Memory usage: {mem}\n")
    sys.stdout.flush()


# var should be one of FPAR or LAI
if var == "FPAR":
    canonical_name = "fraction_of_surface_downwelling_photosynthetic_radiative_flux_absorbed_by_vegetation"
    dir_path = "source_format/fPAR_daily_0.05deg"
    file_glob = f"FPAR_Daily*{year}*.mat"
    scale_factor = 1 / 64000  # Mapping 0 - 1 into 0 - 64000
    unit = "1"
elif var == "LAI":
    canonical_name = "leaf_area_index"
    dir_path = "source_format/LAI_daily_0.05deg"
    file_glob = f"LAI_Daily*{year}*.mat"
    scale_factor = 1 / 6400  # Mapping 0 - 10 into 0 - 64000
    unit = "1"
else:
    sys.stderr.write("Unknown or missing VAR value")
    sys.exit()

# Location of the root directory
dir_root = "/rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/"

# Get the files
input_file_pattern = os.path.join(dir_root, dir_path, file_glob)
input_year_files = glob.glob(input_file_pattern)

# Get the day of year and convert to date
days = [int(f.split(".")[-2]) for f in input_year_files]

# Get a list of zero-based indices for iterating over days in base
# matrix (might not start Jan 1st)
day_ord = np.argsort(np.argsort(days))

# Create lat and long dimensions using cell centres: note _deliberate_
# overrun at end of sequence to avoid clipping last value
res = 0.05
longitude = np.arange(-180 + res / 2, 180, res)
latitude = np.arange(90 - res / 2, -90, -res)

# Get the landmask for unpacking data - note that this is (lat, long)
landmask = sio.loadmat(os.path.join(dir_root, "source_format/Landmask.005d.mat"))[
    "data"
]

# The issue here is that the packing of the values into the daily files
# uses column major ordering, not row major, so need to do some shuffling
# to get array indices that will insert the data into the grid correctly.
land_cell_idx_col_major = np.nonzero(landmask.flatten(order="F"))
land_cell_idx = np.unravel_index(land_cell_idx_col_major, landmask.shape, order="F")

# Make a 3D array to complete for the year following CF TZYX recommendation
base_grid = np.ndarray((len(days), len(latitude), len(longitude)), dtype="float32")

# Loop over the files
for day_idx, this_file in zip(day_ord, input_year_files):

    report_mem(process, f"Loading day: {day_idx}; ")

    # Extract and unpack
    mat = sio.loadmat(this_file)
    mat_data = mat["data"]

    # insert the values into an empty matrix
    mat_data_unpack = np.empty_like(landmask, dtype="float32")
    mat_data_unpack[:] = np.nan
    mat_data_unpack[land_cell_idx] = mat_data.flatten()

    # insert into the correct day of year
    base_grid[day_idx, :, :] = mat_data_unpack


# Reporting
report_mem(process, "Data loaded; ")

# Create the xarray object holding the data
dates = sorted(
    [datetime.datetime(year, 1, 1) + datetime.timedelta(d - 1) for d in days]
)
xds = xarray.DataArray(
    base_grid,
    coords=[dates, latitude, longitude],
    dims=["time", "latitude", "longitude"],
    name=canonical_name,
    attrs={"units": unit},
)

report_mem(process, "Array created; ")

# Save to disk - creating output directory
out_dir = os.path.join(dir_root, f"{var}_{outdir_suffix}")
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, f"{var}_{year}.nc")

# Set up the output encoding - compress either output but
# with pack set to True, configures the packing into uint16

if pack:
    encoding = {
        canonical_name: {
            "zlib": True,
            "complevel": 6,
            "dtype": "uint16",
            "scale_factor": scale_factor,
            "_FillValue": 65535,
        }
    }
else:
    encoding = {canonical_name: {"zlib": True, "complevel": 6}}


xds.to_netcdf(out_file, encoding=encoding)
