import os
import re
import sys
from pathlib import Path

import numpy as np
import xarray

"""
This script is used to check the distribution of values in the incoming raw data. The
following environment variables need to be set:

* variable name in VAR
* root directory in DIR
"""

# Environment variables
var = os.getenv("VAR")
# Location of the root directory
dir_root = os.getenv("DIR")

sys.stdout.write(f"In Py and running:\n  VAR: {var}\nDIR: {dir_root}\n")
sys.stdout.flush()

# Variable list - file name, var name, missing values and then histogram bin setup
var_list = {
    "FPAR": ["FPAR", "FPAR", -10, None, None, None],
    "LAI": ["LAI", "LAI", -10, None, None, None],
    "PAR": ["PAR", "PAR", -10, None, None, None],
    "Rg": ["Rg", "Rg", -10, None, None, None],
    "NIRv": ["NIRv", "NIRv", -1, -0.2, 2, 0.1],
    "MCD43C4": ["NIRv", " MCD43C4 qc", 255, None, None, None],
}

if var not in var_list:
    raise ValueError(f"Unknown variable: {var}")

file_var, var_name, missing_value, hist_lo, hist_hi, hist_step = var_list[var]

# Get the monthly compiled files
input_file_dir = os.path.join(dir_root, f"{file_var}_raw")
input_files = list(Path(input_file_dir).rglob("*.nc"))
input_files.sort()

# Create an output file
outfile = Path(input_file_dir) / f"{var_name}_distribution.csv"

# Create the histogram bins
bins = np.arange(hist_lo, hist_hi, hist_step)


with open(outfile, "w", buffering=1024) as outf:

    # Write headers
    outf.write(f"file,N_na,N_inf,lo,{','.join([f'{x:0.2f}' for x in bins])},hi\n")

    # Add lower and upper limits to bins
    bins = np.concatenate([-np.inf, bins, np.inf])

    # Loop over the files
    for this_file in input_files:

        # Load, reduce to required DataArray and set missing values
        try:
            ds = xarray.load_dataset(this_file)
            mat = ds[var_name]
        except (OSError, RuntimeError, ValueError) as e:
            err_string = str(e).replace("\n", " ")
            outf.write(f"{this_file} # {err_string}\n")
            continue

        # Set NAs and count and remove inf
        mat = mat.where(mat != missing_value)
        na_count = int(mat.isnull().sum())
        inf_count = int(np.isinf(mat).sum())
        mat = mat.where(np.isfinite(mat))

        counts, edges = np.histogram(mat, bins)
        # Report limits
        outf.write(
            f"{this_file},{na_count},{inf_count},{','.join([f'{x:0.2f}' for x in bins])}\n"
        )
