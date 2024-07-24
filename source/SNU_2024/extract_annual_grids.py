"""Convert SNU data to annual grids

This script converts the updated SNU data (see standardise_and_add_coords.py) into
annual grids.

The code:
* Sets up the multi-index of latitude and longitude onto cell_id
* Reshapes to two dimensional lat long arrays by unstacking the cell_id multi index.
* Reindexes using the full set of latitude  and longitude values from the land mask to
  fill in values along those dimensions where no land cells occur (should just be
  missing latitudes thanks to Antarctica, but still playing safe)
* Rename the dimensions to comply with CF standards.
* Save as compressed float32 to save space
"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path


root = Path("/rds/general/project/lemontree/live/source/SNU_2024")


# Open the dataset
ds = xr.open_dataset(root / "snu_fpar_cleaned_v1.nc")

# Get the unique years
years = set(ds["time"].dt.year.data)

for this_year in years:
    # Get a data array (ditching the landmask) of the fAPAR data for the year.
    ds_sub = ds["fAPAR"].isel({"time": ds["time"].dt.year == this_year})

    # Create a multi-dimensional index onto cell id
    mindex = pd.MultiIndex.from_arrays(
        [
            ds_sub["cell_longitude"].data,
            ds_sub["cell_latitude"].data,
        ],
        names=["cell_longitude", "cell_latitude"],
    )
    mindex_coords = xr.Coordinates.from_pandas_multiindex(mindex, "cell_id")
    ds_sub = ds_sub.assign_coords(mindex_coords)

    # Unstack the cell_id multi_index to lat and long
    reshaped = ds_sub.unstack("cell_id")

    # Add missing coordinates from the global grid
    reshaped = reshaped.reindex(
        indexers={
            "cell_latitude": ds["latitude"].data,
            "cell_longitude": ds["longitude"].data,
        },
        fill_value=np.nan,
    )

    # Rename dimensions and convert to float32
    reshaped = reshaped.rename(
        {"cell_latitude": "latitude", "cell_longitude": "longitude"}
    )
    reshaped = reshaped.astype("float32")

    # Compress and save
    reshaped.to_netcdf(
        root / f"annual_grids/snu_fpar_cf_v1_{this_year}.nc",
        encoding={"fAPAR": {"zlib": True, "complevel": 6}},
    )
