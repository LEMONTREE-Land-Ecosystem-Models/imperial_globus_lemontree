import os
import sys
import re
from pathlib import Path

import xarray

"""
This script is used to check the limits on SNU Ryu incoming files. The
following environment variables need to be set:
* variable name in VAR
"""

# Environment variables
var = os.getenv("VAR")

sys.stdout.write(
    f"In Py and running:\n  VAR: {var}\n"
)
sys.stdout.flush()

# Other variables
# Regex for the file date
yr_regex = re.compile('A([0-9]{4})([0-9]{3})')

# Location of the root directory
dir_root = "/rds/general/project/lemontree/ephemeral/SNU_data_sharing_Sep_2022"

# Variable dictionary
var_dict = {
    "FPAR": {
        # "canonical_name": "fraction_of_surface_downwelling_photosynthetic_radiative_flux_absorbed_by_vegetation",
        "scale_factor": 64000,  # Mapping 0 - 1 into 0 - 64000
        "add_offset": None,
        "unit": "1",
        "fill": -10
        },
    "LAI": {
        # "canonical_name": "leaf_area_index",
        "scale_factor": 6400,  # Mapping 0 - 10 into 0 - 64000
        "add_offset": None,
        "unit": "1",
        "fill": -10
        },
    "PAR": {
        # "canonical_name": "surface_downwelling_photosynthetic_radiative_flux_in_air",
        "scale_factor": 800,  # Mapping 0 - 80 into 0 - 64000
        "add_offset": None,
        "unit": "W m-2",
        "fill": -10
        },
    "Rg": {
        # "canonical_name": "????",
        "scale_factor": 1280,  # Mapping 0 - 50 into 0 - 64000
        "add_offset": None,
        "unit": "1",
        "fill": -10
        },
    "NIRv": {
        # "canonical_name": "????",
        "scale_factor": 10000,  # Mapping -0.1 - 0.5 into 0 - 60000
        "add_offset": -0.1,
        "unit": "1",
        "fill": -1
        }
}

# Get the details for this variable
var_info = var_dict.get(var, None)

if var_info is None:
    raise ValueError(f"Unknown variable: {var}")

# Recursive search for all files across years - directory structure is variable - and
# then filter down to the requested year
input_file_dir = os.path.join(dir_root, f'{var}_daily_005d_V1')
input_year_files = Path(input_file_dir).rglob(f'{var}_Daily_005d.*.nc')

# Jeepers, this is quick. 15K files almost instantly.
year_files = [(yr_regex.search(p.name).groups(), p) for p in input_year_files]

# Create an output file
outfile = os.path.join(dir_root, 'limits', f"{var}_limits.csv")

with open(outfile, 'w') as outf:

    # Loop over the files
    for (year, day_idx), this_file in year_files:

        # Load and set missing values
        try:
            mat = xarray.load_dataarray(this_file)
        except OSError:
            outf.write(f"{year},{day_idx},NA,NA # File IO error\n")
            continue

        mat = mat.where(mat != var_info['fill'])

        # Report limits
        outf.write(f"{year},{day_idx},{float(mat.min())},{float(mat.max())}\n")
