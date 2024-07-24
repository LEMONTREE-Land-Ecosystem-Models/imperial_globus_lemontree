"""Restructure SNU data to add useability.

This code renames the variables in the raw SNU data to more obvious values and then
provides correct coordinates along the data dimensions, including a multi index for
latitude and longitude along the cell_id index. The raw data stores only land cell
values along the cell_id index but does not provide a mapping of that dimension onto
geographic coordinates, which is added here.
"""

import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path


root = Path("/rds/general/project/lemontree/live/source/SNU_2024")

# Open the dataset
ds = xr.open_dataset(root / "snu_fpar_raw_v1.nc")

# Change the misleading dimension names to standards
ds = ds.rename_dims({"x": "time", "y": "cell_id", "x2": "latitude", "y2": "longitude"})

# Assign missing coordinates to time, latitude and longitude dimensions
# - note that xarray currently stores time as nano-second precision, which is not ideal
#   as we'd like to make it clear that these are monthly representative values.
ds = ds.assign_coords(
    coords={
        "time": np.arange(
            np.datetime64("1982-01"), np.datetime64("2022-01"), np.timedelta64(1, "M")
        ).astype("datetime64[ns]"),
        "latitude": np.arange(89.975, -90, step=-0.05),
        "longitude": np.arange(-179.975, 180, step=0.05),
    }
)

# Provide an actual mapping from the binary landmask to the actual ordering of the cell
# id dimension. The mapping is not provided but the sequential land cell ids are
# assigned by decreasing latitude for each longitudinal band: the first land cell_id is
# in Wrangel Island (-179.975° E) in the Russian Arctic and increases south across land
# cells until the south pole before switching to the next longitudinal band west.
#
# This code:
# * stacks the landmask dimensions into a 1 dimensional array,
# * reduces the dataset to only locations where the land mask is set
# * This gives the correct sequence of longitude and latitude values along the cell_id
#   dimension, which can then be added as coordinates onto the cell_id dimension using a
#   multi-index.

landmsk_all_cells = ds["landmsk"].stack({"cell_id": ["longitude", "latitude"]})
landmsk_land_cells = landmsk_all_cells[landmsk_all_cells > 0]

# Create the multi-dimensional index onto cell id
mindex = pd.MultiIndex.from_arrays(
    [
        landmsk_land_cells["longitude"].data,
        landmsk_land_cells["latitude"].data,
    ],
    names=["cell_longitude", "cell_latitude"],
)
mindex_coords = xr.Coordinates.from_pandas_multiindex(mindex, "cell_id")
ds = ds.assign_coords(mindex_coords)

# Save a properly dimensioned and extended version of the original data.
ds.to_netcdf(root / "snu_fpar_cleaned_v1.nc")
