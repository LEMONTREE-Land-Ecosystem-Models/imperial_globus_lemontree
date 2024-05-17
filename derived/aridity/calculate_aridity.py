from pathlib import Path

import xarray
import re
import numpy as np
from pyrealm.pmodel.functions import calc_soilmstress_stocker, calc_soilmstress_mengoli

root = Path("/rds/general/project/lemontree/live")

# Get a sorted list of the splash output files with years added to the list of files
splash_files = [
    (int(re.search("([0-9]{4})(?=\.nc)", str(file)).group()), file) 
    for file in sorted(Path(root / "derived/splash_cru_ts4.07/data").glob("*.nc"))
]

annual_ai_arrays = list()

for year, file in splash_files:

    data = xarray.load_dataset(file)

    # Annual total precipitation and PET and hence aridity index by year and across
    # climatology - setting np.inf to np.nan
    annual_AI = data["pet"].sum(dim='time') / data["pre"].sum(dim='time')
    annual_AI = annual_AI.where(annual_AI < np.inf, np.nan)
    annual_AI = annual_AI.expand_dims(dim={'time': [year]})

    annual_ai_arrays.append(annual_AI)

    # ----------------------------------
    # Soil moisture and soilmstress to grid
    # ----------------------------------

    # Calculate soil moisture stress

    relative_soilm = data['wn']/150
    soilmstress_mengoli = calc_soilmstress_mengoli(
        aridity_index=np.broadcast_to(annual_AI.to_numpy(), relative_soilm.shape),
        soilm=relative_soilm.to_numpy()
    )

    soilm_data = xarray.Dataset(
        {
            "soilmstress_mengoli": xarray.DataArray(
                soilmstress_mengoli,  coords=relative_soilm.coords
            ),
        }
    )

    # Export soil moisture data by year
    outpath = root / f"derived/aridity/data/soilmstress_mengoli_{year}.nc"
    soilm_data.to_netcdf(outpath)

# Export the annual aridity indices
annual_ai_data = xarray.concat(annual_ai_arrays, dim='time')
annual_ai_data.rename(time='year')
annual_ai_data.name = 'aridity_index'
annual_ai_data.to_netcdf(root / "derived/aridity/data/annual_aridity_indices.nc")