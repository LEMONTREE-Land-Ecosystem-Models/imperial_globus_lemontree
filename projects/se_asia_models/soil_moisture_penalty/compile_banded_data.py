# This Python script uses xarray to compile the output of soil_moisture_banded.py from
# 2° latitudinal banded files to a single file for the whole region of interest

from pathlib import Path

import xarray

# Paths
project_root = Path("/rds/general/project/lemontree/live/")
output_path = project_root / "projects/se_asia_models/soil_moisture_penalty/data"

# Loop over the years
for year in range(1982, 2019):
    # Get all the files for the year
    year_bands = list(output_path.glob(f"*{year}*"))

    # Open as a multifile dataset
    mfds = xarray.open_mfdataset(year_bands)

    # Write to file
    out_encoding = {"dtype": "float32", "zlib": True, "complevel": 6}
    mfds.to_netcdf(
        output_path / f"soil_moisture_{year}.nc",
        encoding={
            "monthly_wn": out_encoding,
            "total_annual_aet": out_encoding,
            "total_annual_pet": out_encoding,
        },
    )
