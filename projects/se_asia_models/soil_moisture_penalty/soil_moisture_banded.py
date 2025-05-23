# This is a draft of the Python code for running the GPP models
import gc
import os
import time
from itertools import pairwise
from pathlib import Path

import numpy as np
from pyrealm.splash.splash import SplashModel
from pyrealm.core.calendar import Calendar
import rioxarray  # noqa: F401, provides engine = 'rasterio'
import xarray

# Paths
project_root = Path("/rds/general/project/lemontree/live/")
chelsa_path = project_root / "source/CHELSA"
elev_path = project_root / "source/GMTED2010/mn30/mn30.tiff"
output_path = project_root / "projects/se_asia_models/soil_moisture_penalty/data"

# Set the bounds
# The bounds were used to test memory usage. With the following bounds:
#
# longitude_bounds = [92.0, 95.0]  # [92.0, 141.0] --> 3/49
# latitude_bounds = [29.0, 27.0]  # [29.0, -11.0] --> 2/40
#
# PBS reported: Memory usage:
# 6406900kb
# Suggesting the usage with the full region is:
# >>> (6406900 / (3*2)) * (49*40) / 1024**2
# 1996 Gb !?


array_index = int(os.getenv("PBS_ARRAY_INDEX"))
lat_pairs = list(pairwise(np.arange(29, -12, -2)))
this_pair = lat_pairs[array_index]

longitude_bounds = [92.0, 141.0]
latitude_bounds = [float(this_pair[0]), float(this_pair[1])]

print(f"Processing latitude bounds: {latitude_bounds}")

# -------------------------------------------------------------------------------------
# Data loading and subsetting
# - Load the constant data (elevation/patm) and the full CO2 time series
# - Then loop over years.
# -------------------------------------------------------------------------------------

# Load the GMTED 2010 elevation at 30 arc seconds
elevation_ds = xarray.open_dataset(elev_path, engine="rasterio")

# Load the elevation for the region of interest
elevation_data = elevation_ds.sel(
    y=slice(*latitude_bounds),
    x=slice(*longitude_bounds),
)["band_data"].to_numpy()

# Define a function to load a year of CHELSA data from 12 monthly tiff files. There may
# be a way to load these using an xarray multifile dataset, but the inputs lack an
# explicit time dimension on which to concatenate the files.


def load_chelsa_data(path_format, year, latitude_bounds, longitude_bounds):
    """Load a year of CHELSA data into a numpy array.

    The path_format should be a string containing the '{month:02d}' placeholder so that
    the function can iterate over the file names and '{year}' to select the year and
    label the time axis.
    """

    # List to hold the individal month arrays
    month_data = []

    # Iterate over the months, opening the month datasets in order, adding a proper time
    # dimension and appending them to the list of monthly datasets
    for month in np.arange(1, 13):
        dataset = xarray.open_dataset(
            chelsa_path / path_format.format(month=month, year=year), engine="rasterio"
        )
        dataset = dataset.rename_dims({"band": "time"})
        dataset = dataset.rename_vars({"band": "time"})
        dataset = dataset.assign_coords(time=[np.datetime64(f"{year}-{month:02d}")])

        # Extract the variable into a data array and reduce to float32 to decrease
        # memory footprint
        month_data.append(
            dataset["band_data"]
            .sel(
                y=slice(*latitude_bounds),
                x=slice(*longitude_bounds),
            )
            .astype("float32")
        )

    # Concatenate the loaded datasets along the time dimension and return the result.
    # Need to use join="override" here to avoid occassional problem where negligible
    # differences in the floating point representation of the coordinates get
    # interpreted as _different_ coordinates.
    return xarray.concat(month_data, dim="time", join="override")


# -------------------------------------------------------------------------------------
# Year  variable data and modelling
# - CHELSA is 1979 - 2018
# - SNU fAPAR is 1982 - 2021
# - NOAA CO2 is 1979 - 2023
# - PATM is constant
#
# Calculate for 1982 to 2018
# -------------------------------------------------------------------------------------

for year in np.arange(1982, 2019):
    print(f"Processing {year}: {time.ctime()}")

    # Need to convert monthly data to daily data, so get the number of days per month
    # for the year

    # Load the CHELSA variables for the model and correct units.

    # Temperature, converting from Kelvin/10 to Celsius
    # NOTE: The string formatting here requires a placeholder '{year}' for the year and
    #       then a placeholder '{month:02d}' for the load_chelsa_data function to
    #       iterate over the months as '01' to '12'
    temperature_data = load_chelsa_data(
        path_format="tas/CHELSA_tas_{month:02d}_{year}_V.2.1.tif",
        year=year,
        latitude_bounds=latitude_bounds,
        longitude_bounds=longitude_bounds,
    )

    # Store coordinate data before converting
    coords = temperature_data.coords

    # Now convert temperature to °C and reduce to numpy.
    temperature_data = (temperature_data.to_numpy() / 10) - 273.15

    # Clip out temperatures below -25°C
    temperature_data = np.clip(temperature_data, a_min=-25.0, a_max=None)

    # Precipitation
    precipitation_data = load_chelsa_data(
        path_format="pr/CHELSA_pr_{month:02d}_{year}_V.2.1.tif",
        year=year,
        latitude_bounds=latitude_bounds,
        longitude_bounds=longitude_bounds,
    )

    # Convert units - converting from (kg m-2 month-1 * 100) in file
    # - approximating 1kg m-2 = 1 litre m-2 = 1mm m-2
    # - also reduce to numpy.
    precipitation_data = precipitation_data.to_numpy() / 100

    # Cloud cover, converting from percentage to sunshine fraction as 1 - (clt /100) and
    # reduce to numpy.
    cloud_data = load_chelsa_data(
        path_format="clt/CHELSA_clt_{month:02d}_{year}_V.2.1.tif",
        year=year,
        latitude_bounds=latitude_bounds,
        longitude_bounds=longitude_bounds,
    )

    cloud_data = 1 - (cloud_data.to_numpy() / 100)

    # For some reason, the downloaded CLT data is at a coarser resolution (~3km)
    cloud_data = np.kron(cloud_data, np.ones((1, 3, 3), dtype="float32"))

    # ---------------------------------------------------------------------------------
    # Extract required coordinate data
    # ---------------------------------------------------------------------------------

    # Get the number of days in each month from the time dimension
    data_times = coords["time"].to_numpy().astype("datetime64[D]")
    start_next_year = (
        data_times[0].astype("datetime64[Y]") + np.timedelta64(1, "Y")
    ).astype("datetime64[D]")
    days_per_month = np.diff(np.concat([data_times, [start_next_year]])).astype("int32")

    # Get the sequence of dates in the year
    year_days = np.arange(data_times[0], start_next_year, 1)

    # Get the latitudes from the Y dimension
    latitude = coords["y"].to_numpy().astype("float32")

    # ---------------------------------------------------------------------------------
    # Converting monthly to daily observations
    # ---------------------------------------------------------------------------------

    # CHELSA from monthly to daily
    temperature_data = np.repeat(temperature_data, days_per_month, axis=0)
    cloud_data = np.repeat(cloud_data, days_per_month, axis=0)

    # For precipitation, need to reduce monthly mm to daily mm. Explicitly type the days
    # per month as float32 otherwise the float32 / integer promotes to float64,
    precipitation_data = np.repeat(
        precipitation_data / days_per_month[:, None, None].astype("float32"),
        days_per_month,
        axis=0,
    )

    # ---------------------------------------------------------------------------------
    # Fit the model
    # ---------------------------------------------------------------------------------

    # Broadcast latitudes and elevation
    data_shape = temperature_data.shape
    latitude = np.broadcast_to(latitude[None, :, None], data_shape)
    this_year_elevation = np.broadcast_to(elevation_data, data_shape)

    # Something odd happening with data shapes
    print(
        "\n"
        f"Temperature: {temperature_data.shape} {temperature_data.dtype}\n"
        f"Precipitation: {precipitation_data.shape} {precipitation_data.dtype}\n"
        f"Cloud: {cloud_data.shape} {cloud_data.dtype}\n"
        f"Elevation: {this_year_elevation.shape} {this_year_elevation.dtype}\n"
        f"Latitude: {latitude.shape} {latitude.dtype}\n"
        "\n"
    )

    # Load the data into the PModel environment and run the model
    splash = SplashModel(
        lat=latitude,
        elv=this_year_elevation,
        dates=Calendar(year_days),
        sf=cloud_data,
        tc=temperature_data,
        pn=precipitation_data,
    )

    # On the first year, find the initial soil moisture using stationarity
    if year == 1982:
        initial_soil_moisture = splash.estimate_initial_soil_moisture()

    # Now calculate the daily time series
    aet, wn, _ = splash.calculate_soil_moisture(wn_init=initial_soil_moisture)

    # Set the last day as the input soil moisture for the next year
    initial_soil_moisture = wn[-1]

    # Now package the data
    # - monthly mean soil moisture
    wn_by_month = np.split(wn, np.cumsum(days_per_month)[:-1], axis=0)
    wn_month = np.array([np.nanmean(vals, axis=0) for vals in wn_by_month])

    # Total annual PET and AET
    total_annual_aet = aet.sum(axis=0)
    total_annual_pet = splash.evap.pet_d.sum(axis=0)

    # Create an xarray dataset
    calculated_data = xarray.Dataset(
        data_vars={
            "monthly_wn": (("time", "y", "x"), wn_month),
            "total_annual_aet": (("y", "x"), total_annual_aet),
            "total_annual_pet": (("y", "x"), total_annual_pet),
        },
        coords=coords,
    )

    # Write data out as compressed float32 values.
    out_encoding = {"dtype": "float32", "zlib": True, "complevel": 6}
    calculated_data.to_netcdf(
        output_path / f"soil_moisture_{year}_band_{array_index}.nc",
        encoding={
            "monthly_wn": out_encoding,
            "total_annual_aet": out_encoding,
            "total_annual_pet": out_encoding,
        },
    )

    # Free up memory
    del (
        temperature_data,
        cloud_data,
        precipitation_data,
        this_year_elevation,
        latitude,
        splash,
        wn_by_month,
        wn_month,
        total_annual_aet,
        total_annual_pet,
        calculated_data,
    )
    gc.collect()  # This may not actually be needed :-)
