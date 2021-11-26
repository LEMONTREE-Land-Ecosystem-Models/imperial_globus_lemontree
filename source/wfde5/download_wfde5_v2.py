import sys
import os

import cdsapi

"""
[DO 2021-11-26]

This script downloads the main data files from the WFDE5 v2 from CDS using
the CDS API. 

I have deliberately chosen to download zip compressed files not .tar.gz
because the contents of zip files are accessible without unpacking the 
file, unlike a TAR file within a GZ archive:

```
import zipfile
import netcdf4

z = zipfile.ZipFile('WFDE5_v2.0_near_surface_specific_humidity_1992.zip')

# Check file list
z.filelist

# [<ZipInfo filename='Qair_WFDE5_CRU_199208_v2.0.nc' filemode='-rw-rw-r--' file_size=223449722>,
#  ...
#  <ZipInfo filename='Qair_WFDE5_CRU_199207_v2.0.nc' filemode='-rw-rw-r--' file_size=222896203>]

f = z.open('Qair_WFDE5_CRU_199208_v2.0.nc')
nc = netCDF4.Dataset('placeholder_for_file_name', mode='r',  memory=f.read())
```


The script expects to find a .cdsapi file giving CDS credentials in the 
users home directory
"""

# Set roots

dir_root  = '/rds/general/project/lemontree/live/source/wfde5/wfde5_v2'

# Make the download directory
if not os.path.exists(dir_root):
    os.makedirs(dir_root)


# Requires CDS conditions to be accepted online and then needs
# to find a $HOME/.cdsapirc with a key
c = cdsapi.Client()

# Elevation - no temporal series
outfile = os.path.join(dir_root, f"Elev/WFDE5_v2.0_Elev.zip")
outdir = os.path.dirname(outfile)

if not os.path.exists(outdir):
     os.makedirs(outdir)

# Skip already downloaded files
if not os.path.exists(outfile):

    c.retrieve(
        'derived-near-surface-meteorological-variables',
        {
            'version': '2.0',
            'format': 'zip',
            'variable': 'grid_point_altitude',
            'reference_dataset': 'cru',
        },
        outfile)


# Other variables - time series
variables = (('Tair', 'near_surface_air_temperature'), 
             ('Qair', 'near_surface_specific_humidity'),
             ('Wind', 'near_surface_wind_speed',) 
             ('Rainf','rainfall_flux',) 
             ('Snowf','snowfall_flux'),
             ('PSurf','surface_air_pressure',) 
             ('LWdown','surface_downwelling_longwave_radiation'),
             ('SWdown','surface_downwelling_shortwave_radiation'))
             )

for short_name, long_name in variables:
    for yr in range(1979, 2020):
            
            outfile = os.path.join(dir_root, short_name, 
                                   f"WFDE5_v2.0_{short_name}_{yr}.zip")
            outdir = os.path.dirname(outfile)
            
            if not os.path.exists(outdir):
                os.makedirs(outdir)
        
            # Skip already downloaded files
            if os.path.exists(outfile):
                continue
            
            c.retrieve(
                'derived-near-surface-meteorological-variables',
                {
                    'version': '2.0',
                    'format': 'zip',
                    'variable': long_name,
                    'month': [
                        '01', '02', '03',
                        '04', '05', '06',
                        '07', '08', '09',
                        '10', '11', '12',
                    ],
                    'year': [str(yr)],
                    'reference_dataset': 'cru',
                },
                outfile)

