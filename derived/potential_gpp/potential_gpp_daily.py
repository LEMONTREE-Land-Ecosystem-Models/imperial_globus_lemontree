import gzip
import datetime
from pathlib import Path

import xarray
import numpy as np
import pandas

from pyrealm.core.hygro import convert_vp_to_vpd
from pyrealm.core.pressure import calc_patm
from pyrealm.pmodel import PModelEnvironment, PModel


root = Path("/rds/general/project/lemontree/live")

# CRU TS data: Mean monthly temperature (°C) and Mean monthly vapour pressure (hPa)
# Dimensions:  (lon: 720, lat: 360, time: 120)

tmp_files = sorted(list((root / "source/cru_ts/cru_ts_4.07/data/tmp").glob("*.gz")))
vap_files = sorted(list((root / "source/cru_ts/cru_ts_4.07/data/vap").glob("*.gz")))

# Bundle those up into dictionaries by decade
cru_data_by_decade = [{"tmp": t, "vap": v} for t, v in zip(tmp_files, vap_files)]

# CO2 DATA: Load interpolated merge of CMIP3 CO2 forcings and NOAA Mauna Loa
# observations. See derived/co2/co2_cmip3_noaa_interpolated.py for details.
co2 = pandas.read_csv(root / "derived/co2/co2_cmip3_noaa_interpolated_daily.csv")

# ATMOSPHERIC PRESSURE from elevation
elev = xarray.load_dataarray(
    root / "source/wfde5/wfde5_v2/Elev/ASurf_WFDE5_CRU_v2.0.nc"
).to_numpy()
patm = calc_patm(elv=elev)


# Data loader class for CRU data
class ProcessData:
    """CRU data loader.

    Helper class to:
    * load the forcing variables for a decade
    * provide the get_daily_data method to extract daily data for a given year.
    """

    def __init__(self, decade_files):
        self.monthly_data = dict()

        # Loop over the provided decadal files
        for var, file in decade_files.items():
            # Read the monthly data from the gz file.
            with gzip.open(file) as fp:
                var_data = xarray.load_dataset(fp.read())[var]

            # Use forward fill (ffill) to go from monthly to daily observations, which
            # requires:
            # 1. That the dates by adjusted to fill from month start to end, not
            #    from mid month to mid month using the provided dates
            month_dates = var_data["time"].to_numpy().astype("datetime64[M]")
            var_data = var_data.assign_coords(time=month_dates.astype("datetime64[ns]"))

            # 2. That there is a final date at the end of the time series to fill to
            pad_data = var_data.isel(time=-1)
            next_month = month_dates[-1] + np.timedelta64(1, "M")
            pad_data.coords["time"] = next_month.astype("datetime64[ns]")
            var_data = xarray.concat([var_data, pad_data], dim="time")

            # Now store the monthly data
            self.monthly_data[var] = var_data

        # Remove low temperatures by setting to nan
        self.monthly_data["tmp"] = self.monthly_data["tmp"].where(
            self.monthly_data["tmp"] >= -25
        )

        # Convert VP in hPa to kPA and then to VPD in kPa and then to VPD in Pa and then
        # clip values below zero and discard the VAP data
        self.monthly_data["vpd"] = (
            convert_vp_to_vpd(
                vp=self.monthly_data["vap"] / 10, ta=self.monthly_data["tmp"]
            )
            * 1000
        )
        self.monthly_data["vpd"] = self.monthly_data["vpd"].clip(min=0)
        del self.monthly_data["vap"]

        # Get the years provided by this instance (remembering to exclude the last
        # padded day)
        self.dates = self.monthly_data["tmp"]["time"]
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
            year_data = year_data.resample(time="1D").ffill()
            daily_data[var] = year_data.isel(time=slice(0, -1))

        return daily_data


# Loop over CRU decadal files - could just use an mfdataset here.
for cru_decade in cru_data_by_decade:
    cru_decadal_data = ProcessData(cru_decade)

    # Loop over years within CRU decades
    for year in cru_decadal_data.years:
        # Reporting
        print(
            f"Running {year} "
            f"at {datetime.datetime.now().isoformat(timespec='seconds')}\n",
            flush=True,
        )

        cru_annual_data = cru_decadal_data.get_daily_data(year)

        # Get TMP and VPD as numpy arrays
        tmp = cru_annual_data["tmp"].to_numpy()
        vpd = cru_annual_data["vpd"].to_numpy()

        # Extract appropriate year and broadcast to spatial grid
        co2_year = co2.loc[co2.year == year]
        co2_grid = np.broadcast_to(
            co2_year["average_co2_ppm"].to_numpy()[:, None, None], vpd.shape
        )

        # Broadcast the atmospheric pressure to the time axis
        patm_year = np.broadcast_to(patm[None, ...], vpd.shape)

        # Load PPFD data from WFD (1900 - 1978, 3 hourly) or WFDE5 v2 (1979 - 2018, half
        # hourly) Note that the load step for WFD is time consuming, because it loads
        # the data, but the open_mfdataset for WFDE5 is lazy and so the time consuming
        # step comes when the data is accesssed to be converted to PPFD below.
        if year < 1979:
            swdown_xarr = xarray.load_dataset(
                root / f"source/WFD/SWDown_gridded/WFD_SWDOWN_{year}.nc"
            )
            # The latitude axis is reversed compared to the other datasets and this
            # information gets lost once data are stripped down to numpy arrays, so
            # reverse this here.
            swdown_xarr = swdown_xarr.isel(lat=slice(None, None, -1))
            swdown_var = "swdown"
        else:
            wfde_files = list(
                (root / f"source/wfde5/wfde5_v2/SWdown/{year}").glob(
                    f"SWdown_WFDE5_CRU_{year}*"
                )
            )
            swdown_xarr = xarray.open_mfdataset(wfde_files)
            swdown_var = "SWdown"

        # Calculate the daily mean SWDown
        swdown_daily_mean = swdown_xarr.groupby("time.dayofyear").mean()

        # Get PPFD - slower step for WFDE5. Both sources provide SWDown in W/m2,
        # converted to PPFD inµmol/m2/s using 2.04 µmol W-1.
        ppfd = swdown_daily_mean[swdown_var].to_numpy() * 2.04

        # Fit the P Models with the default Stocker kphio and then with the theoretical
        # maximum value of 1/8
        env = PModelEnvironment(tc=tmp, patm=patm_year, vpd=vpd, co2=co2_grid)

        pmodel_c3_default_kphio = PModel(env=env)
        pmodel_c4_default_kphio = PModel(env=env, method_optchi="c4")

        pmodel_c3_max_kphio = PModel(env=env, kphio=1 / 8)
        pmodel_c4_max_kphio = PModel(env=env, method_optchi="c4", kphio=1 / 8)

        pmodel_c3_default_kphio.estimate_productivity(fapar=1, ppfd=ppfd)
        pmodel_c4_default_kphio.estimate_productivity(fapar=1, ppfd=ppfd)

        pmodel_c3_max_kphio.estimate_productivity(fapar=1, ppfd=ppfd)
        pmodel_c4_max_kphio.estimate_productivity(fapar=1, ppfd=ppfd)

        # Get Mengoli water stress penalty
        water_stress_penalty = xarray.load_dataset(
            root / f"derived/aridity/data/soilmstress_mengoli_{year}.nc"
        )

        # Export data
        # - Need to use nanosecond precision because of xarray/pandas, which leads to
        #   spuriously accurate midnight values. Might need to revisit this.
        # - Export values as single precision float. No need for double precision, save
        #   half the file size.
        # - Compress the data to save more file size.
        time_coords = np.arange(
            np.datetime64(f"{year}-01"),
            np.datetime64(f"{year + 1}-01"),
            np.timedelta64(1, "D"),
        ).astype("datetime64[ns]")

        export_data = xarray.Dataset(
            data_vars=dict(
                pot_gpp_c3_default_kphio=(
                    ["day", "lat", "lon"],
                    pmodel_c3_default_kphio.gpp.astype(np.float32),
                ),
                pot_gpp_c4_default_kphio=(
                    ["day", "lat", "lon"],
                    pmodel_c4_default_kphio.gpp.astype(np.float32),
                ),
                pot_gpp_c3_max_kphio=(
                    ["day", "lat", "lon"],
                    pmodel_c3_max_kphio.gpp.astype(np.float32),
                ),
                pot_gpp_c4_max_kphio=(
                    ["day", "lat", "lon"],
                    pmodel_c4_max_kphio.gpp.astype(np.float32),
                ),
                mean_monthly_water_stress=(
                    ["day", "lat", "lon"],
                    water_stress_penalty["soilmstress_mengoli"]
                    .to_numpy()
                    .astype(np.float32),
                ),
            ),
            coords={
                "day": time_coords,
                "lat": cru_annual_data["tmp"]["lat"],
                "lon": cru_annual_data["tmp"]["lon"],
            },
        )

        export_data.to_netcdf(
            path=root / f"derived/potential_gpp/data/daily_potential_gpp_{year}.nc",
            encoding={
                "pot_gpp_c3_default_kphio": {"zlib": True, "complevel": 6},
                "pot_gpp_c4_default_kphio": {"zlib": True, "complevel": 6},
                "pot_gpp_c3_max_kphio": {"zlib": True, "complevel": 6},
                "pot_gpp_c4_max_kphio": {"zlib": True, "complevel": 6},
                "mean_monthly_water_stress": {"zlib": True, "complevel": 6},
            },
        )
