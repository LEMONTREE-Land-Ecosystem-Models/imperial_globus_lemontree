import gzip
import os
from pathlib import Path

import xarray
import numpy as np
import pandas

from pyrealm.hygro import convert_vp_to_vpd
from pyrealm.pmodel import calc_patm
from pyrealm.pmodel import PModelEnvironment, PModel

year = int(os.getenv("PBS_ARRAY_INDEX"))

root = Path("/rds/general/project/lemontree/live")

# CRU TS data: Mean monthly temperature (°C) and Mean monthly vapour pressure (hPa)
# Dimensions:  (lon: 720, lat: 360, time: 120)

# Find the correct decadal file
cru_ts_decades = np.arange(1901, 2021).reshape(12, 10)
cru_ts_decade_strings = [f"{rw[0]}.{rw[9]}" for rw in cru_ts_decades]
decade_index, _ = np.where(cru_ts_decades == year)
cruts_dates = cru_ts_decade_strings[decade_index[0]]

with gzip.open(
    root / f"source/cru_ts/cru_ts_4.07/data/tmn/cru_ts4.07.{cruts_dates}.tmn.dat.nc.gz"
) as fp:
    tmn_xarr = xarray.load_dataset(fp.read())["tmn"]

with gzip.open(
    root / f"source/cru_ts/cru_ts_4.07/data/vap/cru_ts4.07.{cruts_dates}.vap.dat.nc.gz"
) as fp:
    vap_xarr = xarray.load_dataset(fp.read())["vap"]


# Extract year and convert to numpy
tmn = tmn_xarr.where(tmn_xarr["time.year"] == year, drop=True).to_numpy()
vap = vap_xarr.where(vap_xarr["time.year"] == year, drop=True).to_numpy()

# Convert hPa VP to VPD
vpd = convert_vp_to_vpd(vp=vap * 10, ta=tmn)

# Load interpolated merge of CMIP3 CO2 forcings and NOAA Mauna Loa observations.
# See derived/co2/co2_cmip3_noaa_interpolated.py for details.
co2 = pandas.read_csv(root / "derived/co2/co2_cmip3_noaa_interpolated.csv")

# Extract appropriate year and broadcast to spatial grid
co2_year = co2.loc[co2.year == year]
co2_grid = np.broadcast_to(
    co2_year["average_co2_ppm"].to_numpy()[:, None, None], vpd.shape
)

# Get atmospheric pressure from elevation and broadcast to shape
elev = xarray.load_dataarray(
    root / "source/wfde5/wfde5_v2/Elev/ASurf_WFDE5_CRU_v2.0.nc"
).to_numpy()
patm = calc_patm(elv=elev)
patm = np.broadcast_to(patm[None, ...], vpd.shape)

# Load PPFD data from WFD (1900 - 1978, 3 hourly) or WFDE5 v2 (1979 - 2018, half hourly)
# Note that the load step for WFD is time consuming, because it loads the data, but the
# open_mfdataset for WFDE5 is lazy and so the time consuming step comes when the data is
# accesssed to be converted to PPFD below
if year < 1979:
    swdown_xarr = xarray.load_dataset(
        root / f"source/WFD/SWDown_gridded/WFD_SWDOWN_{year}.nc"
    )
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

# Get PPFD - slower step for WFDE5
ppfd = swdown_monthly_mean[swdown_var].to_numpy() * 2.04

# Clean input variables for bad values
tmn = np.where(tmn < -25.0, np.nan, tmn)
vpd = np.clip(vpd, 0, np.inf)

# Fit the P Models
env = PModelEnvironment(tc=tmn, patm=patm, vpd=vpd, co2=co2_grid)

pmodel_c3 = PModel(env=env)
pmodel_c4 = PModel(env=env, method_optchi="c4")

pmodel_c3.estimate_productivity(fapar=1, ppfd=ppfd)
pmodel_c4.estimate_productivity(fapar=1, ppfd=ppfd)

# Export data - need to use nanosecond precision because of xarray/pandas, which leads
# to spuriously accurate midnight on first of month values
time_coords = np.arange(
    np.datetime64(f"{year}-01"), np.datetime64(f"{year + 1}-01"), np.timedelta64(1, "M")
).astype("datetime64[ns]")

export_data = xarray.Dataset(
    data_vars=dict(
        potential_gpp_c3=(["time", "lat", "lon"], pmodel_c3.gpp),
        potential_gpp_c4=(["time", "lat", "lon"], pmodel_c4.gpp),
    ),
    coords={
        "time": time_coords,
        "lat": tmn_xarr["lat"],
        "lon": tmn_xarr["lon"],
    },
)

export_data.to_netcdf(root / f"derived/potential_gpp/data/potential_gpp_{year}.nc")
