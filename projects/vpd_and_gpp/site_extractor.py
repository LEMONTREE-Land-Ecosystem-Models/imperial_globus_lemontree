"""Extract monthly mean values for P Model drivers for VPD and GPP project.

This script extracts the model driver values for the P Model from 2010 - 2019 from the
WFDE5 dataset, the SNU FAPAR dataset and the NOAA global CO2 series, using the nearest
global grid cell for a set of defined sites being used in the project. All variables are
resampled to monthly means and then compiled into a single driver dataset.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

# Set up the root and project paths
root = Path("/rds/general/project/lemontree/live")
project = root / "projects/vpd_and_gpp"

# Load site data and convert to an xarray dataset that can be used
#  to spatially index the global gridded data
site_coords = pd.read_csv(project / "site_data.csv")

site_coords_xarray = xr.Dataset(
    data_vars={
        "lat": ("site_id", site_coords["Lat"]),
        "lon": ("site_id", site_coords["Long"]),
    },
    coords={"site_id": site_coords["Ecoregion_Location"]},
)

# Data sources:
# * WFDE5 1979 - 2019
#   - Tair (air temperature)
#   - Qair (specific humidity)
#   - PSurf (surface pressure)
#   - SWdown (downwelling shortwave radiation)
# * SNU FAPAR 1982 - 2021
#   - FAPAR
# * NOAA CO2 monthly
#   - CO2


# Define a set of common timestamps and a shared timeslice to select the focal data
start_date = np.datetime64("2010-01")
end_date = np.datetime64("2020-01")
timestamps = np.arange(start_date, end_date, np.timedelta64(1, "M")).astype(
    "datetime64[ns]"
)
timeslice = slice(np.datetime64("2010-01-01 00:00"), np.datetime64("2019-12-31 23:59"))

# Create an empty directory to collect processed data arrays to build the new dataset
compiled_data = {}

# -----------------
# WFDE5 DATA
# -----------------
wfde_path = root / "source/wfde5/wfde5_v2/"
wfde_vars = ["PSurf", "Qair", "SWdown", "Tair"]

for var in wfde_vars:
    # Get a list of all the files across years for this variable. The open_mfdataset
    # creates a meta-dataset across multiple files that can then be used to select data.
    # The contents of the files are not loaded until actually needed for processing.
    var_directory = wfde_path / var
    print(var_directory)
    wfde_files = list(var_directory.rglob("*.nc"))
    wfde_data = xr.open_mfdataset(wfde_files)

    # Find the cell closest to the provided site coordinates
    site_data = wfde_data.sel(
        lat=site_coords_xarray["lat"], lon=site_coords_xarray["lon"], method="nearest"
    )

    # Drop to the target time range
    site_data = site_data.sel(time=timeslice)

    # Aggregate to monthly mean values and call compute to load and process the data
    monthly_site_data = site_data.resample(time="1ME").mean().compute()

    # The lat lon coordinates are taken from the grid, so reset to the site to
    # standardise across sources
    monthly_site_data = monthly_site_data.assign_coords(
        lat=site_coords_xarray["lat"], lon=site_coords_xarray["lon"], time=timestamps
    )

    # Save the data array specific variable into the compiled data
    compiled_data[var] = monthly_site_data[var]

# -----------------
# FAPAR data
# -----------------
# Again - collect all the available files and open them as a meta-dataset
fapar_path = root / "source/SNU_005_Version_1/FPAR_daily_by_month/"
fapar_files = list(fapar_path.rglob("*.nc"))
fapar_data = xr.open_mfdataset(fapar_files)

# Find the cell closest to the provided site coordinates - need to rename the variables
# to match the site data names first
fapar_data = fapar_data.rename({"latitude": "lat", "longitude": "lon"})
site_data = fapar_data.sel(
    lat=site_coords_xarray["lat"], lon=site_coords_xarray["lon"], method="nearest"
)

# Drop to the target time range
site_data = site_data.sel(time=timeslice)

# Aggregate to monthly mean values and compute the actual data
monthly_site_data = site_data.resample(time="1ME").mean().compute()

# Standardise the coordinates from the grid to the sites
monthly_site_data = monthly_site_data.assign_coords(
    lat=site_coords_xarray["lat"], lon=site_coords_xarray["lon"], time=timestamps
)

# Store the data array of the required variable
compiled_data["FAPAR"] = monthly_site_data["FPAR"]

# -----------------
# NOAA CO2 data
# -----------------

# Load the data, skipping past the lengthy header
co2_file = root / "source/NOAA_CO2/co2_mm_gl.csv"
co2_noaa = pd.read_csv(co2_file, skiprows=55)

# Add a proper time stamp as an index and reduce to the average monthly CO2 variable
co2_noaa["time"] = pd.to_datetime(dict(year=co2_noaa.year, month=co2_noaa.month, day=1))
co2_noaa = co2_noaa.set_index("time")
co2_noaa = co2_noaa[["average"]]

# Rename average to something more meaningful
co2_noaa = co2_noaa.rename(columns={"average": "co2"})

# Drop to date range
co2_noaa = co2_noaa.to_xarray()
co2_noaa = co2_noaa.sel(time=timeslice)
co2_noaa = co2_noaa.assign_coords(time=timestamps)

# Broadcast data to sites and add data array to compiled data
co2_noaa, _ = xr.broadcast(co2_noaa, site_coords_xarray)
compiled_data["co2"] = co2_noaa["co2"]

# -----------------
# COMPILE AND EXPORT
# -----------------
compiled_dataset = xr.Dataset(compiled_data)
compiled_dataset.to_netcdf(project / "compiled_site_data.nc")
