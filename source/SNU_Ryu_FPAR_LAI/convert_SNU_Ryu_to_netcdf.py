import os
import sys
import glob
import datetime

import scipy.io as sio
import numpy as np
import xarray

# TODO - look at gathering to save space - cf-python implements reading and
#        unpacking back to 2D really elegantly but xarray and netcdf4 read the 
#        fine but need unpacking separately (not built in)

# Needs to be submitted with an array job to loop over years and 
# specify the variable via an environment variable SCRIPT_VAR

var = os.getenv('SCRIPT_VAR')
arrind = os.getenv('PBS_ARRAY_INDEX')
year = 1999 + int(arrind)

# var should be one of FPAR or LAI
if var == 'FPAR':
    dir_path = 'fPAR_daily_0.05deg'
    file_glob = f'FPAR_Daily^.{year}*'
    unit = 'XXX'
elif var == 'LAI':
    dir_path = 'LAI_daily_0.05deg'
    file_glob = f'LAI_Daily^.{year}*'
    unit='XXX'
else:
    sys.stderr.write('Unknown or missing SCRIPT_VAR value')
    sys.exit()

# Location of the root directory
dir_root = '/rds/general/project/lemontree/live/incoming/SNU_Ryu/source_format'

# Get the files 
input_file_pattern = os.path.join(dir_root, dir_path, file_glob)
input_year_files = glob.glob(input_file_pattern)

# Get the day of year and convert to date
days = [int(f.split('.')[-2]) for f in input_year_files]

# Get a list of zero-based indices for iterating over days in base
# matrix (might not start Jan 1st)
day_ord = np.argsort(np.argsort(days))

# Build numpy array for a year of 0.05 degree data
longitude = np.arange(0.025, 360, 0.05)
latitude = np.arange(0.025, 180, 0.05)

# Get the landmask for unpacking data - note that this is (lat, long)
landmask = sio.loadmat(os.path.join(dir_root, 'Landmask.005d.mat'))['data']

# The issue here is that the packing of the values into the daily files
# uses column major ordering, not row major, so need to do some shuffling
# to get array indices that will insert the data into the grid correctly.
land_cell_idx_col_major = np.nonzero(landmask.flatten(order='F'))
land_cell_idx = np.unravel_index(land_cell_idx_col_major, landmask.shape, order='F')

# Make a 3D array to complete for the year
base_grid = np.ndarray((len(latitude), len(longitude),  len(days)), 
                       dtype='float32')

# Loop over the files
for day_idx, this_file in zip(day_ord, input_year_files):
    
    # Extract and unpack
    mat = sio.loadmat(this_file)
    mat_data = mat['data']

    # insert the values into an empty matrix
    mat_data_unpack = np.empty_like(landmask, dtype='float32')
    mat_data_unpack[:] = np.nan
    mat_data_unpack[land_cell_idx] = mat_data.flatten()
    
    # insert into the correct day of year
    base_grid[:, :, day_idx] = mat_data_unpack

# Create the xarray object holding the data
dates = sorted([datetime.datetime(year, 1, 1) + datetime.timedelta(d - 1) for d in days])
xds = xarray.DataArray(base_grid, 
                       coords=[latitude, longitude, dates], 
                       dims=['latitude', 'longitude', 'time'])

xds.name = var

# Save to disk
outfile = os.path.join(dir_root, f'{var}_{year}.nc')
xds.to_netcdf(outfile, encoding={var: {'zlib': True, 'complevel': 6}})
