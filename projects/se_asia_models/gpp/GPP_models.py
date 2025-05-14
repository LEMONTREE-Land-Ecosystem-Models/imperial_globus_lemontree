# This is a draft of the Python code for running the GPP models

from pathlib import Path

import numpy as np
from pyrealm.pmodel import PModelEnvironment, PModel
import rasterio
from rasterio.windows import Window

# Paths

chelsa_path = Path("/rds/general/project/lemontree/live/source/CHELSA")


# Define the CHELSA region of interest (ROI) for Southeast Asia - we need to open one of
# the CHELSA files to convert that lat/long of the ROI into row and column indices.
dataset = rasterio.open(chelsa_path / "tas/CHELSA_tas_03_1990_V.2.1.tif")

rows, cols = rasterio.transform.rowcol(
    dataset.transform, xs=[88.0, 153.0], ys=[26.0, -12.0]
)

# This window can be used to extract the data for the region of interest
se_asia_chelsa_window = Window(
    col_off=cols[0], row_off=rows[0], width=np.diff(cols), height=np.diff(rows)
)

# Load the variables for the model and correct units

# Temperature, converting from Kelvin/10 to Celsius
temperature_ds = rasterio.open(chelsa_path / "tas/CHELSA_tas_03_1990_V.2.1.tif")
temperature_data = temperature_ds.read(indexes=1, window=se_asia_chelsa_window)
temperature_data = (temperature_data / 10) - 273.15

# VPD is already in Pa
vpd_ds = rasterio.open(chelsa_path / "vpd/CHELSA_vpd_03_1990_V.2.1.tif")
vpd_data = vpd_ds.read(indexes=1, window=se_asia_chelsa_window)

# PPFD is calculated from RSDS in MJ/m2/day to umol/m2/s. The saved data is itself
# saved as integer and scaled by a factor of 0.001.
# NOTE: the filename format here is different from tas and vpd.
rsds_ds = rasterio.open(chelsa_path / "rsds/CHELSA_rsds_1990_03_V.2.1.tif")
ppfd_data = rsds_ds.read(indexes=1, window=se_asia_chelsa_window)

# The data are integer values (max 26299)
# * scale by a factor of 0.001 to MJ/m2/day (max 26.299)
# * and by 1e6 to J/m2/day (max 26299000)
# * and then 24 * 60 * 60 to J/m2/s (max ~304)
# * and then from J/m2/s (= W/m2) to µmol/m2/s (1W ~ 4.57 µmol m2 s1 and roughly 44% is
#   photosynthetically active radiation) so 4.57 * 0.44 ~ 2.04 (max ~621)
ppfd_data = (ppfd_data * 0.001 * 1e6) / (24 * 60 * 60) * 2.04


# Load the data into the PModel environment and run the model
env = PModelEnvironment(
    tc=temperature_data,
    vpd=vpd_data,
    patm=101325.0,
    co2=400.0,
    ppfd=ppfd_data,
    fapar=1,
)
pmodel = PModel(env=env)
