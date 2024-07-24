"""Convert SNU data to annual grids

This script converts the updated SNU data (see standardise_and_add_coords.py) into
annual grids.
The code:

# * Reshapes to two dimensional lat long arrays by unstacking the cell_id multi index.
# * Reindexes using the full set of latitude  and longitude values from the land mask to
#   fill in values along those dimensions where no land cells occur (should just be
#   missing latitudes thanks to Antarctica, but still playing safe)
# * Rename the dimensions to comply with CF standards.
# * Save as compressed float32 to save space
"""

import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_dataset("snu_fpar_cf_v1.nc")

# Get the unique years
years = set(ds["time"].dt.year.data)

for this_year in years:
    # Get a data array (ditching the landmask) of the fAPAR data for the year.
    ds_sub = ds["fAPAR"].isel({"time": ds["time"].dt.year == this_year})

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
        f"annual_grids/snu_fpar_cf_v1_{this_year}.nc",
        encoding={"fAPAR": {"zlib": True, "complevel": 6}},
    )
