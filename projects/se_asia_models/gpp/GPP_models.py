# This is a draft of the Python code for running the GPP models

from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from pyrealm.pmodel import PModelEnvironment, PModel
from pyrealm.core.pressure import calc_patm
import rioxarray  # noqa: F401, provides engine = 'rasterio'
import pandas
import xarray

# Paths
project_root = Path("/rds/general/project/lemontree/live/")
chelsa_path = project_root / "source/CHELSA"
elev_path = project_root / "source/GMTED2010/mn30/mn30.tiff"
co2_path = project_root / "source/NOAA_CO2/co2_mm_gl.csv"
fapar_path = project_root / "source/SNU_2024/annual_grids"
output_path = project_root / "projects/se_asia_models/gpp/"

# Set the bounds
longitude_bounds = [88.0, 153.0]
latitude_bounds = [26.0, -12.0]

# -------------------------------------------------------------------------------------
# Data loading and subsetting
# - Load the constant data (elevation/patm) and the full CO2 time series
# - Then loop over years.
# -------------------------------------------------------------------------------------

# Load the GMTED 2010 elevation at 30 arc seconds
elevation_ds = xarray.open_dataset(elev_path, engine="rasterio")

# Load the elevation for the region of interest and calculate atmospheric pressure
elevation_data = elevation_ds.sel(
    y=slice(*latitude_bounds),
    x=slice(*longitude_bounds),
)

patm_data = calc_patm(elevation_data)

# Broadcast the single layer of elevation data to 12 months [from (1, 4560, 7800) to
# (12, 4560, 7800)] and convert to numpy array
shape = list(patm_data["band_data"].shape)
shape[0] = 12
patm = np.broadcast_to(patm_data["band_data"], shape)

# Load the CO2 and extract the 12 values for the year
co2_data_full = pandas.read_csv(co2_path, comment="#")

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
        month_data.append(
            dataset.sel(
                y=slice(*latitude_bounds),
                x=slice(*longitude_bounds),
            )
        )

    # Concatenate the loaded datasets along the time dimension and return the result
    return xarray.concat(month_data, dim="time")


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
    print(f"Processing {year}")

    # Subset CO2 data to the single year
    co2_data = co2_data_full.query(f"year=={year}")["average"].to_numpy()

    # Load fAPAR data for this year and subset to the latitude and longitude bounds
    # - this data is at coarser resolution, handled below.
    fapar_ds = xarray.open_dataset(fapar_path / f"snu_fpar_cf_v1_{year}.nc")
    fapar_data = fapar_ds.sel(
        latitude=slice(*latitude_bounds), longitude=slice(*longitude_bounds)
    )

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
    temperature_data = (temperature_data / 10) - 273.15

    # VPD is already in Pa
    vpd_data = load_chelsa_data(
        path_format="vpd/CHELSA_vpd_{month:02d}_{year}_V.2.1.tif",
        year=year,
        latitude_bounds=latitude_bounds,
        longitude_bounds=longitude_bounds,
    )

    # Load the RSDS data in MJ/m2/day. The raw data is integer and scaled by a factor of
    # 0.001, but the rasterio engine to xarray automatically applies any scale and
    # offset in specified in the file metadata (mask_and_scale=True, by default).
    # NOTE: the filename format here is different from tas and vpd.
    rsds_data = load_chelsa_data(
        path_format="rsds/CHELSA_rsds_{year}_{month:02d}_V.2.1.tif",
        year=year,
        latitude_bounds=latitude_bounds,
        longitude_bounds=longitude_bounds,
    )

    # The RSDS data is in MJ/m2/day and we need to convert to PPFD values in umol/m2/s.
    # The data are integer values (max 26299), automatically scaled on loading by a
    # factor of 0.001 to MJ/m2/day (max 26.299). We then need to:
    # * multiply by 1e6 to J/m2/day (max 26299000)
    # * divide by 24 * 60 * 60 to J/m2/s (max ~304)
    # * and then scale from J/m2/s (= W/m2) to µmol/m2/s (1W ~ 4.57 µmol m2 s1 and roughly
    #   44% is photosynthetically active radiation) so 4.57 * 0.44 ~ 2.04 (max ~621)
    ppfd_data = (rsds_data * 1e6) / (24 * 60 * 60) * 2.04

    # ---------------------------------------------------------------------------------
    # Reconciling data dimensions
    #
    # - The CHELSA data is the target data shape (12 x nrows x ncols)
    # - Atmospheric data is temporally static (nrows x ncols)
    # - CO2 is spatially static (12)
    # - FAPAR is at a lower spatial resolution (0.05° = (1 / 20)° =, and so needs to be
    #   downscaled by a factor of 6 to give 30 arc seconds).
    #
    # At the moment pyrealm _requires_ :
    # * that the inputs are the same shape, not just that they are broadcastable.
    # * that the inputs are numpy arrays.
    # ---------------------------------------------------------------------------------

    # Broadcast CO2 time series to spatial dimensions
    co2_data = np.broadcast_to(co2_data[:, None, None], ppfd_data["band_data"].shape)

    # Tile the fapar data to match resolution using the Kronecker function
    # NOTE: Could do something fancier than tiling here.
    fapar_data_30_arcsec = np.kron(fapar_data["fAPAR"].to_numpy(), np.ones((1, 6, 6)))

    # The fapar data has a different orientation, so need to swap the last two axes
    fapar_data_30_arcsec = np.swapaxes(fapar_data_30_arcsec, 1, 2)

    # ---------------------------------------------------------------------------------
    # Fit the model
    # ---------------------------------------------------------------------------------

    # Load the data into the PModel environment and run the model
    env = PModelEnvironment(
        tc=temperature_data["band_data"].to_numpy(),
        vpd=vpd_data["band_data"].to_numpy(),
        patm=patm_data,
        co2=co2_data,
        ppfd=ppfd_data["band_data"].to_numpy(),
        fapar=fapar_data_30_arcsec,
    )

    pmodel = PModel(env=env)

    # Create a DataArray of the GPP and save
    predicted_gpp = temperature_data["band_data"].copy(data=pmodel.gpp)
    predicted_gpp.name = "PModel_GPP"
    predicted_gpp.to_netcdf(output_path / f"data/se_asia_gpp_{year}.nc")

    # Write out the environment and model summarize() outputs for simple checking
    with open(output_path / f"data/se_asia_gpp_{year}_summary.txt", "w") as f:
        with redirect_stdout(f):
            print(f"P Model and environment summaries for {year}\n")
            env.summarize()
            pmodel.summarize()
