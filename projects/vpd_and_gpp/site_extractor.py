from pathlib import Path


import xarray as xr
import numpy as np
import pandas as pd
import math

from pyrealm import pmodel
from pyrealm.utilities import convert_vp_to_vpd, convert_sh_to_vpd
from pyrealm.param_classes import HygroParams
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

import os
from sklearn import preprocessing
import seaborn as sns

# WFDE5 1979 - 2019
# - Tair (air temperature)
# - Qair (specific humidity)
# - PSurf (surface pressure)
# - SWdown (downwelling shortwave radiation)
# SNU FAPAR 1982 - 2021
# - FAPAR
# NOAA CO2 monthly
# - CO2

root = Path("/rds/general/project/lemontree/live")
project = root / "projects/vpd_and_gpp"

# Load site data and convert to an xarray dataset that can be used to spatially index
# the global gridded data
site_data = pd.read_csv(project / 'site_data.csv')

site_data_xarray = xr.Dataset(
    data_vars = {
        "lat": ("site_id", site_data['Lat']), 
        "lon": ("site_id", site_data['Long'])
    },
    coords = {'site_id': site_data['Ecoregion_Location']}
)




# January 2014 to December 2023
yearMin = 1982
yearMax = 2016

lenyears = yearMax-yearMin+1
yearRange = range(yearMin,yearMax+1)
dateMin    = pd.to_datetime('1982-01-01')
dateMax    = pd.to_datetime('2016-12-01')

# Define date range of data
date_range = pd.period_range(dateMin, dateMax ,freq='D')
date_range = date_range[~((date_range.month == 2) & (date_range.day == 29))]

# Convert pandas period index to datetime index for xarray:
date_range = date_range.to_timestamp()

# Number of timeslices
No_time    = len(date_range)

# 
File directories:

wfde5address = '/Users/ndharwood/Documents/GLOBUS Data/'

faparaddress = '/Users/ndharwood/Documents/Local - CDO OUTPUT/Forcing Datasets/'

# Output dataset paths:
potgpp_saveaddress = '/Users/ndharwood/Documents/Local - CDO OUTPUT/Lag scheme Investigation/'

# csv output path:
csv_saveaddress = '/Users/ndharwood/Documents/Local - CDO OUTPUT/Lag scheme Investigation/Site CSVs/'
# Variables.  Nested lists to deal with the WFDE5 dataset naming system (especially tricky Tmin & Tmax strings)
#   e.g. Tmax = 'Tair_WFDE5v2_CRU_daily_max_1982_del29feb', in this case:
#     vardir = 'Tmax', varfile = 'Tair', vartype = 'max'

variables = [['PSurf', 'PSurf', 'means'], ['Qair', 'Qair', 'means'], ['SWdown', 'SWdown', 'means'],
                                  ['Tair', 'Tair', 'means'], ['Tmax', 'Tair', 'max'], ['Tmin', 'Tair', 'min']]

# To demonstrate how the string extraction works on this tricky naming system:  
for vardir, varfile, vartype in variables:
    print(vardir, varfile, vartype)
PSurf PSurf means
Qair Qair means
SWdown SWdown means
Tair Tair means
Tmax Tair max
Tmin Tair min
Extract Site Points
To demonstrate how the coordinate extraction works, here is an example of a single site extraction dictionary that can then be used in the for loop below:

crd = pd.DataFrame({'lat': [61.84741],
'lon': [24.29477],
'stid': ['FI-Hyy']})
crd_ix = crd.set_index('stid').to_xarray()

Full list of 22 FLUXNET2015 sites across multiple biomes to be extracted from the WFDE5 forcing datasets:

# Dictionary of Sites, and convert to dataset.  Scalable - Add sites here
#   then set station ID as index: results in dataset of 2 arrays (lat/lon) indexed by stid

crd = pd.DataFrame({'lat': [52.1666, 50.30493, 46.242, 45.9459, 45.5598, 39.3232,  42.5378, 41.8494, -31.3764, -25.0197, -30.1913, 15.4028, -17.1175, -2.8567, 5.27877,  47.21022, 50.95,   61.84741, 56.4615, 46.8153, 53.6289,  62.255],
                    'lon': [5.7436, 5.99812, -89.3477, -90.2723, -84.7138,-86.4131,-72.1715, 13.5881, 115.7138, 31.4969, 120.6541, -15.4322,145.6301, -54.9589,-52.92486, 8.41044, 13.5126, 24.29477, 32.9221, 9.8559, -106.1978, 129.168],
                    'stid': ['NL-Loo','BE-Vie','US-Syv','US-PFa','US-UMB','US-MMS','US-Ha1','IT-Col','AU-Gin', 'ZA-Kru', 'AU-GWW', 'SN-Dhr','AU-Rob', 'BR-Sa1','GF-Guy', 'CH-Cha', 'DE-Gri','FI-Hyy', 'RU-Fyo','CH-Dav','CA-Oas', 'RU-Skp']})
crd_ix = crd.set_index('stid').to_xarray()
all_data = []

for yr in yearRange:
    
    # hold each variable, input them to xr.merge() to create single list of all vars for 1 year
    thisyear_data = []
    
    for vardir, varfile, vartype in variables:
        # Extract the data from current file
        fname = os.path.join(wfde5address, f'{vardir}/{varfile}_WFDE5v2_CRU_daily_{vartype}_{yr}_del29feb.nc')
        da    = xr.open_dataset(fname)
        data  = da.sel(lat=crd_ix.lat, lon=crd_ix.lon, method="nearest")
        
        # rename to avoid duplicated var names in path and append to thisyear_data list
        data = data.rename({varfile: vardir})
        thisyear_data.append(data)
        
    # Extend the list of year by year data with the merge of these variables
    all_data.append(xr.merge(thisyear_data))
    
# Concatenate all of the year blocks along the time axis
combined = xr.concat(all_data, 'time')
WFDE5 Forcings - Site-level Run
# Load CO2 File

# This is daily CO2, with:
#   date and co2 columns only
#   missing data interpolated, all feb 29's removed (leap days) 
daily_co2 = wfde5address + 'daily_in_situ_co2_mlo_interpolated.csv'
co2 = pd.read_csv(daily_co2, na_values='NaN', index_col = 0)

# coerce 'object' (date col) to datetime - for date subset below
co2['date'] = pd.to_datetime(co2['date'])

# Subset Date of interest
co2 = co2[co2.date.between(dateMin, dateMax)]

# Get just the data as a numpy array
co2_estimate = co2.co2.to_numpy()
# Load in Arrays (from 'combined' dataset - point-extracted data):
#   Surface Pressure, mean temp, min temp, max temp and specific humidity Files

patm        = xr.DataArray.to_masked_array(combined.PSurf)
tmin_day    = xr.DataArray.to_masked_array(combined.Tmin)
tmax_day    = xr.DataArray.to_masked_array(combined.Tmax)
spechum_day = xr.DataArray.to_masked_array(combined.Qair)
temp_day    = xr.DataArray.to_masked_array(combined.Tair)
# WFDE5 Temperature File Units: Convert kelvin to celsius
tmin_day = tmin_day - 273.15
tmax_day = tmax_day - 273.15
temp_day = temp_day - 273.15

# Mask Temperature arrays - Remove values less than -25 celsius
#   n.b. (mask) fill value default is 1e+20 - setting to 0 or -25 would affect the water density function
#     can change fill value if needed (e.g. np.nan)
tmin_day = np.ma.masked_less_equal(tmin_day, -25 )
tmax_day = np.ma.masked_less_equal(tmax_day, -25 )
temp_day = np.ma.masked_less_equal(temp_day, -25 )
# Generate the VPD Dataset using specific humidity, min and max temperature

# Convert atmospheric pressure from Pa to kPa  (VPD conversion functions need kPa input for patm)
patm = patm / 1000

# Set the conversion to be used
hygro_par = HygroParams(magnus_option='Allen1998')

# Calculate VPD with both temperature extremes and average
vpd_min_day = convert_sh_to_vpd(spechum_day, ta=tmin_day, patm = patm, hygro_params=hygro_par)
vpd_max_day = convert_sh_to_vpd(spechum_day, ta=tmax_day, patm = patm, hygro_params=hygro_par)
vpd_rng_day = np.ma.stack([vpd_min_day, vpd_max_day])
vpd_day     = vpd_rng_day.mean(axis=0)
# Load Irradiance

# Shortwave downwelling radiation - load
swr_day     = xr.DataArray.to_masked_array(combined.SWdown)

#Convert SWR from W/m^2 to kJ/m^2/day: where 1 W/m2 = 86.4 KJ/m2/d
swr_day = swr_day * 86.4
fAPAR Dataset:
The GIMMS fAPAR3g dataset cannot be point-extracted on a local machine due to a chunking issue (see https://www.unidata.ucar.edu/blogs/developer/entry/chunking_data_why_it_matters).
Other fAPAR datasets may work better.
For now, prepare the fAPAR site-level data using an HPC run with the following python code in hashes:
#fapar_load = os.path.join(faparaddress, 'fAPAR3g_v2_1982_2016_DAILY_del29feb.nc')
#fapar_day = xr.open_dataset(fapar_load)
#fapar_day = fapar_day.sel(LAT=crd_ix.lat, LON=crd_ix.lon, method="nearest")
#fapar_day = xr.Dataset.squeeze(fapar_day, dim = ['Z'])
#fapar_day = xr.DataArray.to_masked_array(fapar_day.FAPAR_FILLED)
# Processed fAPAR  -  Site data from HPC run

fapar_load = os.path.join(faparaddress, 'fAPAR_sites_extracted_1.nc')
fapar_day = xr.open_dataset(fapar_load)
# Convert xarray array to masked numpy array to run P Model below
fapar_day = xr.DataArray.to_masked_array(fapar_day.FAPAR_FILLED)
fapar_day.shape
(12745, 22)
# Pre-run final dataset Processing:



# Convert SWR from kJ/d/m2 in input source to PPFD in mols/d/m2
ppfd_day = swr_day * 2.04 / 1000



# RESHAPE CO2.  (n.b. reshape(-1, 1, 1) for global analyses. This is for gridcell (point) selection)

#   Objects for reshape:
# No_time defined in 'objects' section above
inputarraylen = len(temp_day[0]) #broadcast to len of cols in a forcing input dataset (temp_day here)

# Reshape 1D CO2 array into 3D to make it usable:
co2_estimate = np.broadcast_to(co2_estimate.reshape(-1,1), (No_time, inputarraylen))



# Convert VPD and atmospheric pressure from kPa to Pa
patm    = patm * 1000
## Clip negative VPD estimates to zero and convert to Pa
vpd_day = np.ma.clip(vpd_day, 0, np.inf) * 1000
print(fapar_day.shape, flush = True)
print(temp_day.shape, flush = True)
print(co2_estimate.shape, flush = True)
print(patm.shape, flush = True)
print(vpd_day.shape, flush = True)
print(ppfd_day.shape, flush = True)
(12745, 22)
(12745, 22)
(12745, 22)
(12745, 22)
(12745, 22)
(12745, 22)
P Model Run
# Calculate the Photosynthetic Environment
penv = pmodel.PModelEnvironment(tc=temp_day, co2=co2_estimate, patm=patm, vpd=vpd_day)


# Run the P Model:
pmod = pmodel.PModel(penv)
pyrealm/pmodel.py:164: RuntimeWarning: overflow encountered in exp
pyrealm/pmodel.py:616: RuntimeWarning: invalid value encountered in sqrt
pyrealm/pmodel.py:624: RuntimeWarning: overflow encountered in exp
# Estimate the Potential GPP
pmod.estimate_productivity(fapar = 1, ppfd=ppfd_day)
# Generate Pot GPP Dataset and output to NetCDF
pot_gpp = pmod.gpp

# Take lat, lon, time and stid from the 'combined' Dataset (above) - i.e. the initial load-in loop of forcing inputs
coords = combined.coords

# Construct the 'Dataset' (like a NetCDF file), determine Dims and varname
da         = xr.DataArray(pot_gpp, coords = coords, dims = ['time', 'stid'])
ds_pot_gpp = da.to_dataset(name = 'Pot_gpp')


# Output to .nc file, encode for compression:
#ds_pot_gpp.to_netcdf(potgpp_saveaddress + 'Pot_GPP_1982-2016_site_level_run1.nc', encoding = {"Pot_gpp": {'dtype': 'float32','zlib': True, 'complevel': 6}})
Load out fAPAR and GPP as CSV
# Convert to Pandas dataframe
df_fapar = pd.DataFrame(fapar_day, index = date_range, columns = combined.stid)
df_potgpp = pd.DataFrame(pot_gpp, index = date_range, columns = combined.stid)
df_fapar
NL-Loo	BE-Vie	US-Syv	US-PFa	US-UMB	US-MMS	US-Ha1	IT-Col	AU-Gin	ZA-Kru	...	AU-Rob	BR-Sa1	GF-Guy	CH-Cha	DE-Gri	FI-Hyy	RU-Fyo	CH-Dav	CA-Oas	RU-Skp
1982-01-01	0.250000	0.415000	0.220000	0.210000	0.210	0.320000	0.400000	0.400000	0.185000	0.445000	...	0.915000	0.935000	0.605000	0.340	0.190000	NaN	0.022500	0.045000	0.130000	NaN
1982-01-02	0.255968	0.419516	0.221129	0.209355	0.210	0.320806	0.398710	0.400161	0.185968	0.446935	...	0.911613	0.934516	0.605484	0.340	0.192742	NaN	0.030887	0.044677	0.132742	NaN
1982-01-03	0.261935	0.424032	0.222258	0.208710	0.210	0.321613	0.397419	0.400323	0.186935	0.448871	...	0.908226	0.934032	0.605968	0.340	0.195484	NaN	0.039274	0.044355	0.135484	NaN
1982-01-04	0.267903	0.428548	0.223387	0.208065	0.210	0.322419	0.396129	0.400484	0.187903	0.450806	...	0.904839	0.933548	0.606452	0.340	0.198226	NaN	0.047661	0.044032	0.138226	NaN
1982-01-05	0.273871	0.433065	0.224516	0.207419	0.210	0.323226	0.394839	0.400645	0.188871	0.452742	...	0.901452	0.933065	0.606936	0.340	0.200968	NaN	0.056048	0.043710	0.140968	NaN
...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...	...
2016-11-27	0.402667	0.548000	0.301333	0.267333	0.252	0.336000	0.475000	0.484333	0.236000	0.444333	...	0.857667	0.901000	0.682000	0.548	0.313333	0.227333	0.227333	0.154833	0.235000	0.270
2016-11-28	0.399500	0.546000	0.298500	0.263000	0.249	0.332000	0.472500	0.484500	0.234500	0.449500	...	0.854500	0.902000	0.679000	0.546	0.305000	0.215500	0.221750	0.149250	0.232500	0.265
2016-11-29	0.396333	0.544000	0.295667	0.258667	0.246	0.328000	0.470000	0.484667	0.233000	0.454667	...	0.851333	0.903000	0.676000	0.544	0.296667	0.203667	0.216167	0.143667	0.230000	0.260
2016-11-30	0.393167	0.542000	0.292833	0.254333	0.243	0.324000	0.467500	0.484833	0.231500	0.459833	...	0.848167	0.904000	0.673000	0.542	0.288333	0.191833	0.210583	0.138083	0.227500	0.255
2016-12-01	0.390000	0.540000	0.290000	0.250000	0.240	0.320000	0.465000	0.485000	0.230000	0.465000	...	0.845000	0.905000	0.670000	0.540	0.280000	0.180000	0.205000	0.132500	0.225000	0.250
12745 rows × 22 columns

# Save out Site point data as .csv

#df_fapar.to_csv(csv_saveaddress + 'fAPAR_1982-2016_site_point_data_loadout1.csv', na_rep = 'NaN')
#df_potgpp.to_csv(csv_saveaddress + 'Pot_GPP_1982-2016_site_point_data_loadout1.csv', na_rep = 'NaN')
Plot Comparison - Dual axis variable plot
x = fapar_day
y = pot_gpp

# Convert to Pandas dataframe for plotting
x = pd.DataFrame(x, index = date_range, columns = combined.stid)
y = pd.DataFrame(y, index = date_range, columns = combined.stid)
x["key"], y["key"] = "fAPAR", "Potential GPP"

#moving index into a column 
x = x.reset_index()
y = y.reset_index()
#and changing it to datetime values that seaborn can understand
#only necessary because your example contains pd.Period data
x["index"] = pd.to_datetime(x["index"].astype(str))
y["index"] = pd.to_datetime(y["index"].astype(str))
df = pd.concat([x, y]).melt(["index", "key"], var_name="station", value_name="value")
df
index	key	station	value
0	1982-01-01	fAPAR	NL-Loo	0.250000
1	1982-01-02	fAPAR	NL-Loo	0.255968
2	1982-01-03	fAPAR	NL-Loo	0.261935
3	1982-01-04	fAPAR	NL-Loo	0.267903
4	1982-01-05	fAPAR	NL-Loo	0.273871
...	...	...	...	...
560775	2016-11-27	Potential GPP	RU-Skp	NaN
560776	2016-11-28	Potential GPP	RU-Skp	NaN
560777	2016-11-29	Potential GPP	RU-Skp	NaN
560778	2016-11-30	Potential GPP	RU-Skp	NaN
560779	2016-12-01	Potential GPP	RU-Skp	NaN
560780 rows × 4 columns

Subset 5-year Period and Plot:

# Plot Output PATHS:

plot1_saveaddress = '/Users/ndharwood/Documents/Local - CDO OUTPUT/Lag scheme Investigation/'
mask = (df['index'] > '1982-01-01') & (df['index'] <= '1987-01-01')
subsetdf = df.loc[mask]

sns.set(font_scale = 1.75)

fg = sns.relplot(data=subsetdf[subsetdf['key']=='fAPAR'], x="index", y="value", kind="line", row="station", height=6, aspect=4.5/1, 
                 facet_kws={'sharey': False, 'sharex': True}, label = 'fAPAR')

for station, ax in fg.axes_dict.items():  
    ax1 = ax.twinx()
    fig = sns.lineplot(data=subsetdf[(subsetdf['key'] == 'Potential GPP') & (subsetdf['station'] == station)], x='index', y='value', color='orange',
                       ci=None, ax=ax1, label = 'Potential GPP', legend = False)
    ax.set_ylabel('fAPAR')
    ax1.set_ylabel('GPP')
    

lines, labels = fg.fig.axes[0].get_legend_handles_labels()
lines2, labels2 = fg.fig.axes[-1].get_legend_handles_labels()
fg.axes[0,0].legend(lines+lines2, labels+labels2, loc='upper right')


fg.set_xlabels("Date", clear_inner=False)


# SAVE OUT
#plt.savefig(plot1_saveaddress + '22_site_plot_1982-1987.png', dpi=200, bbox_inches='tight')
#plt.show()
