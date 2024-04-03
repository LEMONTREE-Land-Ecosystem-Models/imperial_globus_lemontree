import datetime
import gzip
import os
from pathlib import Path

import xarray
import numpy as np

root = Path("/rds/general/project/lemontree/live")

# Load the land cells to grid translation table
land_map = xarray.load_dataset(root / "source/WFD/SWDown/WFD-land-lat-long-z.nc")

# Load the requested year and get the files to compile
year = os.getenv("YEAR")
paths = list((root / "source/WFD/SWDown/").glob(f"SWdown_WFD_{year}*"))
paths.sort()

data = []

for each_file in paths:

    # Load the data on the land coords
    with gzip.open(each_file) as fp:
        ds = xarray.load_dataset(fp, decode_times=False)

    # Create the full grid and insert the data into the right locations
    swdown = np.full((ds["SWdown"].shape[0], 360, 720), fill_value=np.nan, dtype=float)
    swdown[:, land_map["Grid_lat"] - 1, land_map["Grid_lon"] - 1] = ds["SWdown"]

    # Build the date coordinates - timestp gives a multiple of 3 hours from an origin
    origin_iso = datetime.datetime.strptime(
        ds["timestp"].attrs["time_origin"].strip(), "%Y-%b-%d %H:%M:%S"
    ).isoformat()
    origin = np.datetime64(origin_iso).astype("datetime64[ns]")
    times = origin + np.timedelta64(60 * 60 * 3, "s") * ds["timestp"].to_numpy()

    # Append the data to the list
    data.append(
        xarray.DataArray(
            swdown,
            coords={
                "time": times,
                "lat": np.arange(89.75, -90, -0.5),
                "lon": np.arange(-179.75, 180, 0.5),
            },
            name="swdown",
        )
    )

    # Progress report
    print(each_file)


# Concatenate along time axis
year_data = xarray.concat(data, dim="time")

# Make sure the output directory exists
grid_out_dir = root / "source/WFD/SWDown_gridded"
grid_out_dir.mkdir(exist_ok=True)

# Write the gridded data out
year_data.to_netcdf(
    grid_out_dir / f"WFD_SWDOWN_{year}.nc",
    encoding={"swdown": {"zlib": True, "complevel": 6}},
)
