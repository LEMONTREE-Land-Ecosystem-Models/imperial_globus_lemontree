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

class ProcessData():
    """CRU data loader.
    
    Helper class to:
    * load the three forcing variables for a decade 
    * interpolate from monthly to daily observations 
    * convert cloud cover to sunshine fraction as (1 - cld/100)

    Provides the get_daily_data method to interpolate daily data for individual years,
    which uses a lower memory footprint than using an entire decade of daily values.
    """

    def __init__(self, decade_files):

        self.monthly_data = dict()

        # Loop over the three variable files
        for var, file in decade_files.items():

            # Read the monthly data from the gz file.
            with gzip.open(file) as fp:
                var_data = xarray.load_dataset(fp.read())[var]

            # Use forward fill (ffill) to go from monthly to daily observations, which
            # requires:
            # 1. That the dates by adjusted to fill from month start to end, not
            #    from mid month to mid month using the provided dates
            month_dates = var_data['time'].to_numpy().astype('datetime64[M]')
            var_data = var_data.assign_coords(
                time= month_dates.astype('datetime64[ns]')
            )
            
            # 2. That there is a final date at the end of the time series to fill to
            pad_data = var_data.isel(time=-1)
            next_month = month_dates[-1] + np.timedelta64(1, "M")
            pad_data.coords["time"] = next_month.astype("datetime64[ns]")
            var_data = xarray.concat([var_data, pad_data], dim="time")

            # Convert monthly precipitation to daily:
            if var == "pre":
                var_data /= var_data['time'].dt.days_in_month

            # Now store the monthly data
            self.monthly_data[var] =  var_data

        # Convert cloud cover
        self.monthly_data['sf'] = 1 - self.monthly_data['cld']/100
        del self.monthly_data['cld']

        # Remove low temperatures by clipping to -25
        self.monthly_data['tmp'] = self.monthly_data['tmp'].clip(min=-25)

        # # TODO - does it make more sense to remove these values entirely - this will
        # # disrupt predictions for cold months rather than having an arbitrary floor
        # self.monthly_data['tmp'] = self.monthly_data['tmp'].where(
        #     self.monthly_data['tmp'] >= -25
        # )

        # Get the years provided by this instance (remembering to exclude the last
        # padded day)
        self.dates = self.monthly_data['tmp']['time']
        self.years = np.unique(self.dates[:-1].dt.year)

    def get_daily_data(self, year):

        daily_data = dict()

        # Get the year indices, adding a final padded value to get the first day of the
        # following year as a padded value to fill to.
        year_indices = np.where(self.dates.dt.year == year)[0]
        year_indices = np.concatenate([year_indices, [year_indices.max() + 1]])

        # Loop over the variables
        for var, var_data in self.monthly_data.items():

            # Now:
            # - extract the requested year, 
            # - forward fill the data on a daily resample 
            # - ditch the last padded entry to give only the year
            year_data = var_data.isel(time=year_indices)
            year_data = year_data.resample(time='1D').ffill()
            daily_data[var] =  year_data.isel(time=slice(0,-1))

        return daily_data

# Get the first decade to set up elevation and to run the initial soil moisture spinup
first_decade = ProcessData(data_by_decade[0])

first_year = first_decade.get_daily_data(1901)

# Calendar object
dates = first_year['tmp']['time'].to_numpy().astype('datetime64[D]')
calendar = Calendar(dates)

# Broadcast elevation across dates
elev_by_date = np.broadcast_to(elev_np[None, ...], first_year['tmp'].shape)

# Broadcast latitude across sites and dates
lat = first_year['tmp']['lat'].to_numpy()
lat_by_date_and_lon = np.broadcast_to(lat[None, :, None], first_year['tmp'].shape)

# Initialise the splash model
splash = SplashModel(
    tc=first_year['tmp'].to_numpy(), 
    pn=first_year['pre'].to_numpy(), 
    sf=first_year['sf'].to_numpy(),
    dates=calendar,
    elv=elev_by_date,
    lat=lat_by_date_and_lon,
)

# Spin up the first year - some issues with convergence so doing something approximate
init_wn = splash.estimate_initial_soil_moisture(verbose=True, max_iter=30, max_diff=1.5)

for decade_files in data_by_decade:

    sys.stdout.write(
        f"Processing decade {str(decade_files['tmp'])[-23:-14]} "
        f"at {datetime.datetime.now().isoformat(timespec='seconds')}\n"
    )

    # Load the decadal data
    this_decade = ProcessData(decade_files)

    # Loop over the available years
    for year in this_decade.years:

        sys.stdout.write(
            f"Processing {year} "
            f"at {datetime.datetime.now().isoformat(timespec='seconds')}\n"
        )

        this_year = this_decade.get_daily_data(year)

        # Calendar object
        dates = this_year['tmp']['time'].to_numpy().astype('datetime64[D]')
        calendar = Calendar(dates)

        # Broadcast elevation across dates
        elev_by_date = np.broadcast_to(elev_np[None, ...], this_year['tmp'].shape)

        # Broadcast latitude across sites and dates
        lat = this_year['tmp']['lat'].to_numpy()
        lat_by_date_and_lon = np.broadcast_to(lat[None, :, None], this_year['tmp'].shape)

        # Initialise the splash model
        splash = SplashModel(
            tc=this_year['tmp'].to_numpy(), 
            pn=this_year['pre'].to_numpy(), 
            sf=this_year['sf'].to_numpy(),
            dates=calendar,
            elv=elev_by_date,
            lat=lat_by_date_and_lon,
        )

        # Fit the water balance and capture the aet, wn and ro
        aet_out, wn_out, ro_out = splash.calculate_soil_moisture(init_wn)

        # Build a dataset of the soil moisture, precipitation, pet and aet for the year
        output_data = xarray.Dataset(
            data_vars=dict(
                aet=(('time','lat','lon'), aet_out), 
                wn=(('time','lat','lon'), wn_out), 
                pre=(('time','lat','lon'), this_year['pre'].to_numpy()), 
                pet=(('time','lat','lon'), splash.evap.pet_d)),
            coords = dict(
                time= dates.astype('datetime64[ns]'), 
                lat=elev['lat'], 
                lon=elev['lon']
            )
        )

        # Output annual file
        outfile = root / f"derived/splash_cru_ts4.07/data/splash_cru_ts4.07_{year}.nc"
        output_data.to_netcdf(outfile)

        # Update the initial soil moisture to feed into the next year
        init_wn = wn_out[-1]