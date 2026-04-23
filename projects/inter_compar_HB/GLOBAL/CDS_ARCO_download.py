from itertools import product
from pathlib import Path
import configparser
from datetime import datetime


from obstore.store import HTTPStore
import xarray as xr
from zarr.storage import ObjectStore


"""
[DO 2026-04-23]

This script downloads ERA5 data from CDS via the new ARCO bulk download API. The script
expects to find a .cdsapi file giving CDS credentials in the users home directory.

The script needs to be run in Python 3.13+ environment that provides:

pip install "xarray[io]" zarr httpio fsspec ipython obstore
"""

# Create an output directory on the ephemeral directory.
output_dir = Path("/rds/general/project/lemontree/ephemeral/ERA5_ARCO")
output_dir.mkdir(exist_ok=True)
progress_file = open(output_dir / "progress.log", "w")


# Get the cdsapi key from the RC file in the user home directory.
# NOTE: This requires Python 3.13+ for the allow_unnamed_section argument
cdsapirc_path = Path("~/.cdsapirc").expanduser()
cfg = configparser.ConfigParser(allow_unnamed_section=True)

with open(cdsapirc_path) as cdsapirc_io:
    cfg.read_file(cdsapirc_io)

cdsapi_key = cfg.get(configparser.UNNAMED_SECTION, "key")


# Available variables from
# [(v, ds[v].attrs['long_name']) for v in ds.data_vars]
# [
#     ("blh", "Boundary layer height"),
#     ("cbh", "Cloud base height"),
#     ("d2m", "2 metre dewpoint temperature"),
#     ("fg10", "10 metre wind gust since previous post-processing"),
#     ("msl", "Mean sea level pressure"),
#     ("skt", "Skin temperature"),
#     ("sp", "Surface pressure"),
#     ("ssrd", "Surface solar radiation downwards"),
#     ("sst", "Sea surface temperature"),
#     ("strd", "Surface thermal radiation downwards"),
#     ("t2m", "2 metre temperature"),
#     ("tcc", "Total cloud cover"),
#     ("tp", "Total precipitation"),
#     ("u10", "10 metre U wind component"),
#     ("u100", "100 metre U wind component"),
#     ("v10", "10 metre V wind component"),
#     ("v100", "100 metre V wind component"),
# ]

variables = [
    ("10m_u_component_of_wind", "u10"),
    ("10m_v_component_of_wind", "v10"),
    ("2m_dewpoint_temperature", "d2m"),
    ("2m_temperature", "t2m"),
    ("surface_pressure", "sp"),
    ("total_precipitation", "tp"),
    # ("maximum_2m_temperature_since_previous_post_processing", "??"),
    # ("minimum_2m_temperature_since_previous_post_processing", "??"),
    ("surface_solar_radiation_downwards", "ssrd"),
    ("surface_thermal_radiation_downwards", "sstd"),
]

years = range(1980, 1981)
months = range(1, 13)

# Use the time-chunked data for fast access across spatial dimensions
timechunked_url = "https://arco.datastores.ecmwf.int/cadl-arco-time-002/arco/reanalysis_era5_single_levels/sfc/timeChunked.zarr"

# Use obstore's HTTPStore to create a store with retry configuration,
# and then wrap it in a zarr ObjectStore to read with xarray.
# See https://github.com/developmentseed/obstore/blob/main/obstore/python/obstore/_store/_retry.pyi
# for more details on the retry configuration options.
http_store = HTTPStore(
    timechunked_url,
    client_options={
        "default_headers": {"Authorization": f"Bearer {cdsapi_key}"},
    },
)

store = ObjectStore(http_store, read_only=True)
ds = xr.open_zarr(store)

# Create a generator yielding (variable, year, month) tuples
data_subsets = product(variables, years, months)

for (long_name, var), year, month in data_subsets:
    # Log the start of the subset
    start_time = datetime.now().isoformat(timespec="seconds")

    # Define the subset for the variable and the current month
    month_selector = f"{year}-{month:02}"
    subset = ds[var].sel(time=month_selector)

    # Check a variable directory exists
    var_dir = output_dir / var
    var_dir.mkdir(exist_ok=True)

    subset.to_netcdf(var_dir / f"{var}_{year}_{month:02}.nc")

    # Log the download completion
    progress_file.write(
        f"{start_time}, {datetime.now().isoformat(timespec='seconds')}, "
        f"{var}, {year}, {month}, {round(subset.nbytes / 1024**3, 2)}\n"
    )

    progress_file.flush()
