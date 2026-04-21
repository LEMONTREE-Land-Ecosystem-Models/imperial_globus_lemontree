import os
from itertools import product
from pathlib import Path
import time
import cdsapi

"""
[DO 2026-04-21]

This script downloads ERA5 data from CDS using the CDS API. The script expects to find a
.cdsapi file giving CDS credentials in the users home directory.

The script maintains two active tasks and iterates through permutations of variable and
year chunks. The year chunk size of 4 is chosen as it shows green on the CDS request
website and reduces the total number of jobs and files.
"""

# Create an output directory on the ephemeral directory.
output_dir = Path("/rds/general/project/lemontree/ephemeral/ERA5")
output_dir.mkdir(exist_ok=True)

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
years = list(range(1980, 2026))
n_per_chunk = 4
year_chunks = [years[i : i + n_per_chunk] for i in range(0, len(years), n_per_chunk)]

# Create a generator yielding paired variable and year chunk tuples
data_subsets = product(variables, year_chunks)

# Define a CDSAPI request requesting all hourly observations for a given variable within
# a range of years
dataset = "reanalysis-era5-single-levels"
request_template = {
    "product_type": ["reanalysis"],
    "variable": None,
    "year": None,
    "month": [f"{m:02}" for m in range(1, 13)],
    "day": [f"{d:02}" for d in range(1, 32)],
    "time": [f"{h:02}:00" for h in range(0, 24)],
    "data_format": "grib",
    "download_format": "unarchived",
}

# Launch the client in a mode that allows multiple requests
client = cdsapi.Client(wait_until_complete=False)

# Task list
tasks_list = []

while True:
    # Create requests and add to task list
    if len(tasks_list) < 2:
        try:
            # Get a new data subset from the generator and build the new request
            # dictionary
            new_request_var, new_request_years = next(data_subsets)
            request = request_template.copy()
            request["variable"] = [new_request_var]
            request["year"] = new_request_years

            # Generate the task and add it to the task list, setting the download file
            # path using the variable name and first year
            output_path = output_dir / f"{new_request_var}_{new_request_years[0]}.grib"
            task = client.retrieve(name=dataset, request=request, target=output_path)

            # Add the task to the task list
            tasks_list.append(task)
        except StopIteration:
            pass

    # Monitor the tasks
    for task in tasks_list:
        task.update()
        reply = task.reply
        task.info("Request ID: %s, state: %s" % (reply["request_id"], reply["state"]))

        # Remove failed tasks from the list
        if reply["state"] == "failed":
            task.error("Message: %s", reply["error"].get("message"))
            task.error("Reason:  %s", reply["error"].get("reason"))
            for n in (
                reply.get("error", {})
                .get("context", {})
                .get("traceback", "")
                .split("\n")
            ):
                if n.strip() == "":
                    break
                task.error("  %s", n)
            tasks_list.remove(task)

        if reply["state"] == "completed":
            tasks_list.remove(task)

    time.sleep(30)
