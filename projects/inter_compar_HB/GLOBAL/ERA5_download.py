from itertools import product
from pathlib import Path
from time import gmtime, strftime
import cdsapi

"""
[DO 2026-04-21]

This script downloads ERA5 data from CDS using the CDS API. The script expects to find a
.cdsapi file giving CDS credentials in the users home directory.

The script maintains two active tasks and iterates through permutations of variable and
year month chunks.
"""

# Create an output directory on the ephemeral directory.
output_dir = Path("/rds/general/project/lemontree/ephemeral/ERA5")
output_dir.mkdir(exist_ok=True)
progress_file = open(output_dir / "progress.log", "w")

# Requires CDS conditions to be accepted online and then needs to find a $HOME/.cdsapirc
# with a valid key
c = cdsapi.Client()

variables = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_dewpoint_temperature",
    "2m_temperature",
    "surface_pressure",
    "total_precipitation",
    "maximum_2m_temperature_since_previous_post_processing",
    "minimum_2m_temperature_since_previous_post_processing",
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
]

# Grab variables in chunks of 4 years
years = [str(y) for y in range(1980, 2026)]
months = [f"{m:02}" for m in range(1, 13)]

# Create a generator yielding (variable, year, month) tuples
data_subsets = product(variables, years, months)

# Define a CDSAPI request requesting all hourly observations for a given variable within
# a range of years
dataset = "reanalysis-era5-single-levels"
request_template = {
    "product_type": ["reanalysis"],
    "variable": None,
    "year": None,
    "month": None,
    "day": [f"{d:02}" for d in range(1, 32)],
    "time": [f"{h:02}:00" for h in range(0, 24)],
    "data_format": "grib",
    "download_format": "unarchived",
}

# Launch client - this is running in wait until complete mode, so will download to the
# output path and then continue to the next file.
client = cdsapi.Client()


for var, year, month in data_subsets:
    # Log progress
    progress_file.write(
        f"{strftime('%Y-%m-%d %H:%M:%S', gmtime())}: {var} {year} {month}\n"
    )
    progress_file.flush()

    # Get a new data subset from the generator and build the new request dictionary
    request = request_template.copy()
    request["variable"] = [var]
    request["year"] = [year]
    request["month"] = [month]

    # Check a variable directory exists
    var_dir = output_dir / var
    var_dir.mkdir(exist_ok=True)

    # Run the task
    task = client.retrieve(
        name=dataset, request=request, target=var_dir / f"{var}_{year}_{month}.grib"
    )
