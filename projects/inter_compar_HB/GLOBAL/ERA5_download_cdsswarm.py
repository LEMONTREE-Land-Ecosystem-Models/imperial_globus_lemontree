from itertools import product
from pathlib import Path
from time import gmtime, strftime

import cdsapi
import cdsswarm

"""
[DO 2026-04-21]

This script downloads ERA5 data from CDS using the CDS API. The script expects to find a
.cdsapi file giving CDS credentials in the users home directory.

The script maintains two active tasks and iterates through permutations of variable and
year month chunks.
"""

# Create an output directory on the ephemeral directory.
output_dir = Path("/rds/general/project/lemontree/ephemeral/ERA5_swarm")
output_dir.mkdir(exist_ok=True)
progress_file = open(output_dir / "progress.log", "w")

# Generate task list
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
years = [str(y) for y in range(1980, 2026)]
months = [f"{m:02}" for m in range(1, 13)]
days = [f"{d:02}" for d in range(1, 32)]
time = [f"{h:02}:00" for h in range(0, 24)]


task_list = [
    cdsswarm.Task(
        dataset="reanalysis-era5-single-levels",
        request={
            "product_type": ["reanalysis"],
            "variable": [var],
            "year": [year],
            "month": [month],
            "day": days,
            "time": time,
            "data_format": "grib",
        },
        target=output_dir / var / f"{var}_{year}_{month}.grib",
    )
    for var, year, month in product(variables, years, months)
]

results = cdsswarm.download(task_list, num_workers=4)
