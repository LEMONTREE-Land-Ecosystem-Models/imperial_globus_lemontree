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
co2 = pandas.read_csv(root / "derived/co2/co2_cmip3_noaa_interpolated.csv")

# ATMOSPHERIC PRESSURE from elevation
elev = xarray.load_dataarray(
    root / "source/wfde5/wfde5_v2/Elev/ASurf_WFDE5_CRU_v2.0.nc"
).to_numpy()
patm = calc_patm(elv=elev)

# Data loader class for CRU data
# TODO - think about whether this needs to change to daily? The SPLASH code has a
#        similar processor class that fills CRU to daily, if needed.


class ProcessData:
    """CRU data loader.

    Helper class to:
    * load the forcing variables for a decade
    * provide the get_data method to extract the monthly data for a given year.
    """

    def __init__(self, decade_files):
        self.monthly_data = dict()

        # Loop over the three variable files
        for var, file in decade_files.items():
            # Read the monthly data from the gz file.
            with gzip.open(file) as fp:
                var_data = xarray.load_dataset(fp.read())[var]

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

    def get_data(self, year):
        requested_data = dict()

        # Loop over the variables
        for var, var_data in self.monthly_data.items():
            # Now extract the requested year,
            requested_data[var] = self.monthly_data[var][self.dates.dt.year == year]

        return requested_data


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

        cru_annual_data = cru_decadal_data.get_data(year)

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

        # Calculate the monthly mean
        swdown_monthly_mean = swdown_xarr.groupby("time.month").mean()

        # Get PPFD - slower step for WFDE5. Both sources provide SWDown in W/m2,
        # converted to PPFD inµmol/m2/s using 2.04 µmol W-1.
        ppfd = swdown_monthly_mean[swdown_var].to_numpy() * 2.04

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
        # TODO - these are daily values so average by month (is average sane?)
        water_stress_penalty = xarray.load_dataset(
            root / f"derived/aridity/data/soilmstress_mengoli_{year}.nc"
        )
        monthly_mean_water_stress = water_stress_penalty.groupby(
            water_stress_penalty["time"].dt.month
        ).mean()

        # Export data
        # - Need to use nanosecond precision because of xarray/pandas, which leads to
        #   spuriously accurate midnight on first of month values. Might need to revisit
        #   this.
        # - Export values as single precision float. No need for double precision, save
        #   half the file size.
        # - Compress the data to save more file size.
        time_coords = np.arange(
            np.datetime64(f"{year}-01"),
            np.datetime64(f"{year + 1}-01"),
            np.timedelta64(1, "M"),
        ).astype("datetime64[ns]")

        export_data = xarray.Dataset(
            data_vars=dict(
                pot_gpp_c3_default_kphio=(
                    ["month", "lat", "lon"],
                    pmodel_c3_default_kphio.gpp.astype(np.float32),
                ),
                pot_gpp_c4_default_kphio=(
                    ["month", "lat", "lon"],
                    pmodel_c4_default_kphio.gpp.astype(np.float32),
                ),
                pot_gpp_c3_max_kphio=(
                    ["month", "lat", "lon"],
                    pmodel_c3_max_kphio.gpp.astype(np.float32),
                ),
                pot_gpp_c4_max_kphio=(
                    ["month", "lat", "lon"],
                    pmodel_c4_max_kphio.gpp.astype(np.float32),
                ),
                mean_monthly_water_stress=(
                    ["month", "lat", "lon"],
                    monthly_mean_water_stress["soilmstress_mengoli"]
                    .to_numpy()
                    .astype(np.float32),
                ),
            ),
            coords={
                "month": time_coords,
                "lat": cru_annual_data["tmp"]["lat"],
                "lon": cru_annual_data["tmp"]["lon"],
            },
        )

        export_data.to_netcdf(
            path=root / f"derived/potential_gpp/data/potential_gpp_{year}.nc",
            encoding={
                "pot_gpp_c3_default_kphio": {"zlib": True, "complevel": 6},
                "pot_gpp_c4_default_kphio": {"zlib": True, "complevel": 6},
                "pot_gpp_c3_max_kphio": {"zlib": True, "complevel": 6},
                "pot_gpp_c4_max_kphio": {"zlib": True, "complevel": 6},
                "mean_monthly_water_stress": {"zlib": True, "complevel": 6},
            },
        )
