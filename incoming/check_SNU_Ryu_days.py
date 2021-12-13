import os
import sys
import glob

"""
This script was used to locate missing days with the original SNU_Ryu data files
for FPAR and LAI. Flat directory of 20 years of daily files for each variable.
"""

for var in ('FPAR', 'LAI'):
    for year in range(2000,2020):
        # var should be one of FPAR or LAI
        if var == 'FPAR':
            dir_path = 'fPAR_daily_0.05deg'
            file_glob = f'FPAR_Daily^.{year}*'
        elif var == 'LAI':
            dir_path = 'LAI_daily_0.05deg'
            file_glob = f'LAI_Daily^.{year}*'
        
        # Location of the root directory
        dir_root = '/rds/general/project/lemontree/live/incoming/SNU_Ryu/'
        
        input_file_pattern = os.path.join(dir_root, dir_path, file_glob)
        input_year_files = glob.glob(input_file_pattern)
        
        # Get the days and missing days
        days = sorted([int(f.split('.')[3]) for f in input_year_files])
        missing = [str(d) for d in range(1, 367) if d not in days]
        print(f'{var} {year} {len(input_year_files)} found. Missing: {",".join(missing)}')