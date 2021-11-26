import sys
import os
import simplejson
import warnings

# urllib3 issues a lot of InsecureRequestWarnings
if not sys.warnoptions:
    warnings.simplefilter("ignore")

# Import the download functions from the tools directory
sys.path.append('/rds/general/project/lemontree/live/tools')
import ceda_file_downloader

"""
[DO 2021-11-26]

This script downloads the main data files from the CRU TS 4.04. I have chosen
to download the decadal files rather than the single larger ensemble files
to make it easier to cherry pick time subsets or for testing. 

I have deliberately chosen to download the .gz compressed versions to save
bandwidth and file storage and these should be directly readable.

The script expects to find a JSON file giving CEDA credentials in the users
home directory
"""

# Load the credentials from the home directory of the user running the script

ceda_cred_json = os.path.expanduser('~/ceda_credentials.json')
with open(ceda_cred_json) as cj:
    credentials = simplejson.load(cj)

# Set roots

url_root = "https://dap.ceda.ac.uk/badc/cru/data/cru_ts/cru_ts_4.04/"
dir_root  = '/rds/general/project/lemontree/live/source/cru_ts/cru_ts_4.0.4'

# Make the download directory
if not os.path.exists(dir_root):
    os.makedirs(dir_root)

# Load doc files

docfiles = ["00README_catalogue_and_licence.txt",
            "Release_Notes_CRU_TS4.04.txt",
            "Release_Notes_CRU_TS4.04_observations.txt"]

for each_file in docfiles:
    
    url = url_root + each_file
    outfile = os.path.join(dir_root, each_file)
    
    ceda_file_downloader.download(url, outfile, credentials)

# Load data files

variables = ('cld','dtr','frs','pet','pre','tmn','tmp','tmx','vap','wet')
decades = list(range(1900, 2020, 10)) + [2019]
decades = [f"{f + 1}.{t}" for f, t in zip(decades[:-1], decades[1:])]

for var in variables:
    for dec in decades:
        pass
        
        url_end = f"data/{var}/cru_ts4.04.{dec}.{var}.dat.nc.gz"
        
        outdir = os.path.join(dir_root, os.path.dirname(url_end))
        outfile = os.path.join(dir_root, url_end)
        
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        
        # Skip already downloaded files
        if os.path.exists(outfile):
            continue
        
        url = url_root + url_end
        
        ceda_file_downloader.download(url, outfile, credentials)
        
        

