import datetime
import gzip
import sys
from pathlib import Path

import xarray
import numpy as np

from pyrealm.splash.splash import SplashModel
from pyrealm.core.calendar import Calendar

# This is not run as an array job because the water balance calculations need to be run
# in series across years not in parallel

root = Path("/rds/general/project/lemontree/live")

# CRU TS data: Mean monthly temperature (°C), total monthly precipitation (mm) and mean
# monthly cloud cover (%)
# Dimensions:  (lon: 720, lat: 360, time: 120)

# Get a list of the CRU files needed: tmp, pre and cld
tmp_files = sorted(list((root / "source/cru_ts/cru_ts_4.07/data/tmp").glob("*.gz")))
pre_files = sorted(list((root / "source/cru_ts/cru_ts_4.07/data/pre").glob("*.gz")))
cld_files = sorted(list((root / "source/cru_ts/cru_ts_4.07/data/cld").glob("*.gz")))

# Bundle those up into dictionaries by decade
data_by_decade = [
    {'tmp': t, 'pre': p, 'cld': c} 
    for t, p, c in zip(tmp_files, pre_files, cld_files)
]

# Load elevation data
elev = xarray.load_dataarray(
    root / "source/wfde5/wfde5_v2/Elev/ASurf_WFDE5_CRU_v2.0.nc"
)
# elev = elev.isel(lat=slice(170, 190), lon=slice(350, 370))

elev_np = elev.to_numpy()

def process_data(decade_files):
    """CRU data loader.
    
    Helper function to:
    * load the three forcing variables for a decade 
    * interpolate from monthly to daily observations 
    * convert cloud cover to sunshine fraction as (1 - cld/100)
    """

    data = dict()

    # Loop over the three variable files
    for var, file in decade_files.items():

        # Read the monthly data from the gz file.
        with gzip.open(file) as fp:
            monthly_data = xarray.load_dataset(fp.read())[var]
            # monthly_data = monthly_data.isel(lat=slice(170, 190), lon=slice(350, 370))

        # Use forward fill (ffill) to go from monthly to daily observations, which
        # requires:
        # 1. That the dates by adjusted to fill from month start to end, not
        #    from mid month to mid month using the provided dates
        month_dates = monthly_data['time'].to_numpy().astype('datetime64[M]')
        monthly_data = monthly_data.assign_coords(
            time= month_dates.astype('datetime64[ns]')
        )
        
        # 2. That there is a final date at the end of the time series to fill to
        pad_data = monthly_data.isel(time=-1)
        next_month = month_dates[-1] + np.timedelta64(1, "M")
        pad_data.coords["time"] = next_month.astype("datetime64[ns]")
        monthly_data = xarray.concat([monthly_data, pad_data], dim="time")

        # Convert monthly precipitation to daily:
        if var == "pre":
            monthly_data /= monthly_data['time'].dt.days_in_month

        # Now forward fill the data and ditch the padded entry
        data[var] =  monthly_data.resample(time='1D').ffill().isel(time=slice(0,-1))

    # Convert cloud cover
    data['sf'] = 1 - data['cld']/100
    del data['cld']

    return data

# Get the first decade to set up elevation and to run the initial soil moisture spinup
first_decade = process_data(data_by_decade[0])

# Calendar object
dates = first_decade['tmp']['time'].to_numpy().astype('datetime64[D]')
calendar = Calendar(dates)

# Broadcast elevation across dates
elev_by_date = np.broadcast_to(elev_np[None, ...], first_decade['tmp'].shape)

# Broadcast latitude across sites and dates
lat = first_decade['tmp']['lat'].to_numpy()
lat_by_date_and_lon = np.broadcast_to(lat[None, :, None], first_decade['tmp'].shape)

# Initialise the splash model
splash = SplashModel(
    tc=first_decade['tmp'].to_numpy(), 
    pn=first_decade['pre'].to_numpy(), 
    sf=first_decade['sf'].to_numpy(),
    dates=calendar,
    elv=elev_by_date,
    lat=lat_by_date_and_lon,
)

# Spin up the first year
init_wn = splash.estimate_initial_soil_moisture(verbose=True)

for decade_files in data_by_decade:

    sys.stdout.write(
        f"Processing decade {str(decade_files['tmp'])[-23:-14]} "
        f"at {datetime.datetime.now().isoformat(timespec='seconds')}\n"
    )

    # This is repetitive - refits first decade, but clearer to read and develop
    this_decade = process_data(decade_files)

    # Calendar object
    dates = this_decade['tmp']['time'].to_numpy().astype('datetime64[D]')
    calendar = Calendar(dates)

    # Broadcast elevation across dates
    elev_by_date = np.broadcast_to(elev_np[None, ...], this_decade['tmp'].shape)

    # Broadcast latitude across sites and dates
    lat = this_decade['tmp']['lat'].to_numpy()
    lat_by_date_and_lon = np.broadcast_to(lat[None, :, None], this_decade['tmp'].shape)

    # Initialise the splash model
    splash = SplashModel(
        tc=this_decade['tmp'].to_numpy(), 
        pn=this_decade['pre'].to_numpy(), 
        sf=this_decade['sf'].to_numpy(),
        dates=calendar,
        elv=elev_by_date,
        lat=lat_by_date_and_lon,
    )

    # Fit the water balance and capture the aet, wn and ro
    aet_out, wn_out, ro_out = splash.calculate_soil_moisture(init_wn)

    # Build a dataset of the soil moisture, precipitation, pet and aet for the decade
    output_data = xarray.Dataset(
        data_vars=dict(
            aet=(('time','lat','lon'), aet_out), 
            wn=(('time','lat','lon'), wn_out), 
            pre=(('time','lat','lon'), this_decade['pre'].to_numpy()), 
            pet=(('time','lat','lon'), splash.evap.pet_d)),
        coords = dict(
            time= dates.astype('datetime64[ns]'), 
            lat=elev['lat'], 
            lon=elev['lon']
        )
    )

    # Output annual files
    annual_files = output_data.groupby(output_data['time'].dt.year)

    for year, annual_data in annual_files:
        outfile = root / f"derived/splash_cru_ts4.07/data/splash_cru_ts4.07_{year}.nc"
        annual_data.to_netcdf(outfile)

    # Update the initial soil moisture to feed into the next decade
    init_wn = wn_out[-1]