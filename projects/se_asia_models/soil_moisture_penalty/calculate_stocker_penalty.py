# This Python script calculates the long run aridity index for the region and then the
# monthly Stocker soil moisture penalties

from pathlib import Path
import re

import numpy as np
import xarray
from pyrealm.pmodel.functions import calc_soilmstress_stocker


# Paths
project_root = Path("/rds/general/project/lemontree/live/")
output_path = project_root / "projects/se_asia_models/soil_moisture_penalty/data"

# Get a list of only the compiled data files (in case the 2° banded outputs are still
# present)
compiled_data = re.compile("soil_moisture_([0-9]){4}.nc")
soil_moisture_files = list(
    f
    for f in output_path.glob("soil_moisture_*.nc")
    if compiled_data.match(str(f.name))
)

soil_moisture_files.sort()

# Calculate aridity index
first_loop = True
for annual_file in soil_moisture_files:
    with xarray.open_dataset(annual_file) as ds:
        if first_loop:
            total_aet = ds["total_annual_aet"].compute()
            total_pet = ds["total_annual_pet"].compute()
            first_loop = False
        else:
            total_aet += ds["total_annual_aet"].compute()
            total_pet += ds["total_annual_pet"].compute()

aridity_index = total_aet / total_pet

# Write aridity index to file
aridity_index.name = "aridity_index"
aridity_index.to_netcdf(
    output_path / "aridity_index.nc",
    encoding={
        "aridity_index": {"dtype": "float32", "zlib": True, "complevel": 6},
    },
)

# Calculate soil moisture penalty

# - Broadcast aridity index from single annual grid to months
aridity_index = np.broadcast_to(
    aridity_index.to_numpy()[None, :, :], (12, *aridity_index.shape)
)

for annual_file in soil_moisture_files:
    # Open the input dataset
    with xarray.open_dataset(annual_file) as ds:
        # Calculate the penalty factor
        soil_penalty = calc_soilmstress_stocker(
            soilm=ds["monthly_wn"].to_numpy() / 150, meanalpha=aridity_index
        )

        # Write to a netCDF file
        soil_penalty_ds = xarray.Dataset(
            data_vars={"stocker_penalty": (("time", "y", "x"), soil_penalty)},
            coords=ds.coords,
        )
        soil_penalty_ds.to_netcdf(
            output_path / ("stocker_penalty_" + annual_file.name[-7:]),
            encoding={
                "stocker_penalty": {"dtype": "float32", "zlib": True, "complevel": 6},
            },
        )
