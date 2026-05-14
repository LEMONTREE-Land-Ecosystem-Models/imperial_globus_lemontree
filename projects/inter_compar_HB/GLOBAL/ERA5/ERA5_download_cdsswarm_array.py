import os
from itertools import product
from pathlib import Path
import tomllib

import cdsswarm

"""
[DO 2026-04-21]

This script downloads ERA5 data from CDS using the CDS API. The script runs as a job
array, setting a per job CDSAPI key.

The script uses the cdsswarm package to manage the download task list efficiently. It
uses a limited number of workers to submit monthly tasks, and allows the submission,
acceptance and running of tasks to continue alongside data download.
"""

# Get job array index
job_index = int(os.environ.get("PBS_ARRAY_INDEX"))

# Set up CDS credentials to be used by job
cdsapi_path = Path("~/cdsapi.toml").expanduser().resolve()
cdsapi_info = tomllib.load(open(cdsapi_path, "rb"))

os.environ["CDSAPI_URL"] = cdsapi_info["url"]
os.environ["CDSAPI_KEY"] = cdsapi_info["key"][job_index - 1]

# Set the variable and year range for the jobs
job_subsets = (
    (
        "maximum_2m_temperature_since_previous_post_processing",
        range(1980, 1981),  # range(1980, 2003),
    ),
    (
        "maximum_2m_temperature_since_previous_post_processing",
        range(2003, 2004),  # range(2003, 2026),
    ),
    (
        "minimum_2m_temperature_since_previous_post_processing",
        range(1980, 1981),  # range(1980, 2003),
    ),
    (
        "minimum_2m_temperature_since_previous_post_processing",
        range(2003, 2004),  # range(2003, 2026),
    ),
)

var, years = job_subsets[job_index - 1]

# Check an output directory on the ephemeral directory.
output_dir = Path("/rds/general/project/lemontree/ephemeral/ERA5_swarm_array")
output_dir.mkdir(exist_ok=True)
progress_file = open(output_dir / "progress.log", "a")

# Set the months, days and time
months = [f"{m:02}" for m in range(1, 13)]
days = [f"{d:02}" for d in range(1, 32)]
time = [f"{h:02}:00" for h in range(0, 24)]

# Build the task list
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
    for year, month in product(years, months)
]

results = cdsswarm.download(task_list, num_workers=4)
