import os
import re
import sys
from pathlib import Path

import numpy as np
import xarray

"""
This script is used to check the limits on SNU Ryu incoming files. The
following environment variables need to be set:
* variable name in VAR
"""

# Environment variables
var = os.getenv("VAR")

sys.stdout.write(f"In Py and running:\n  VAR: {var}\n")
sys.stdout.flush()

# Other variables
# Regex for the file date
yr_regex = re.compile("A([0-9]{4})([0-9]{3})")

# Location of the root directory
dir_root = "/rds/general/project/lemontree/ephemeral/SNU_data_sharing_Sep_2022"

# Variable list
var_list = {
    "FPAR": ["FPAR", "FPAR", -10],
    "LAI": ["LAI", "LAI", -10],
    "PAR": ["PAR", "PAR", -10],
    "Rg": ["Rg", "Rg", -10],
    "NIRv": ["NIRv", "NIRv", -1],
    "MCD43C4": ["NIRv", " MCD43C4 qc", 255],
}

if var not in var_list:
    raise ValueError(f"Unknown variable: {var}")

file_var, var_name, missing_value = var_list[var]

# Recursive search for all files across years - directory structure is variable - and
# then filter down to the requested year
input_file_dir = os.path.join(dir_root, f"{file_var}_daily_005d_V1")
input_year_files = Path(input_file_dir).rglob(f"{file_var}_Daily_005d.*.nc")

# Jeepers, this is quick. 15K files almost instantly.
year_files = [(yr_regex.search(p.name).groups(), p) for p in input_year_files]
year_files.sort()

# Create an output file
outfile = os.path.join(dir_root, "limits", var, f"{var_name}_limits.csv")

with open(outfile, "w", buffering=1024) as outf:

    # Loop over the files
    for (year, day_idx), this_file in year_files:

        # Load, reduce to required DataArray and set missing values
        try:
            ds = xarray.load_dataset(this_file)
            mat = ds[var_name]
        except (OSError, RuntimeError, ValueError) as e:
            err_string = str(e).replace("\n", " ")
            outf.write(f"{year},{day_idx},NA,NA,NA,NA # {err_string}\n")
            continue

        # Set NAs and count and remove inf
        mat = mat.where(mat != missing_value)
        na_count = mat.isnull().sum()
        inf_count = np.isinf(mat).sum()
        mat = mat.where(np.isfinite(mat))

        # Report limits
        outf.write(
            f"{year},{day_idx},{na_count},{inf_count},{float(mat.min())},{float(mat.max())}\n"
        )
