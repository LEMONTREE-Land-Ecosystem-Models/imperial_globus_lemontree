from itertools import groupby
import os
import re
from pathlib import Path

"""
This script was used to locate missing days with the original SNU_Ryu data files
for FPAR and LAI. Directories with aribtrary nesting of 20 years of daily files 
for each variable.
"""

# Location of the root directory
dir_root = '/rds/general/project/lemontree/ephemeral/SNU_data_sharing_Sep_2022/'

# Regex for the file date
yr_regex = re.compile('A([0-9]{4})([0-9]{3})')

# Hard code leap years
leap = [1972, 1976, 1980, 1984, 1988, 1992, 1996, 2000, 2004, 2008, 2016, 2020]

# Loop over variables
for var in ('FPAR', 'LAI', 'NIRv', 'Rg', 'PAR'):

    # Get the directory path and the file glob
    var_path = f'{var}_daily_005d_V1'
    var_glob = f'{var}_Daily_005d.*.nc'

    input_file_dir = os.path.join(dir_root, var_path)
    input_year_files = Path(input_file_dir).rglob(var_glob)

    # Jeepers, this is quick. 15K files almost instantly.
    year_day = [yr_regex.search(p.name).groups() for p in input_year_files]

    # Sort and group by year
    year_day.sort()
    year_groups = groupby(year_day, key=lambda x: x[0])

    for yr, data in year_groups:
        nday = 366 if int(yr) in leap else 365
        target = range(1, nday + 1)
        days = [int(x[1]) for x in data]
        missing = set(target).difference(days)
        if missing:
            missing = ', '.join([str(x) for x in missing])
            print(f"{var} - {yr}: {missing}")
        else:
            print(f"{var} - {yr}: All found")
