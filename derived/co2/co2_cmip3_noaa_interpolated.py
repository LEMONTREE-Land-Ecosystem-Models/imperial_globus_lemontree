import numpy as np
import pandas
from pathlib import Path
from scipy.interpolate import interp1d

root = Path("/rds/general/project/lemontree/live/")

# Load global CO2 data and interpolate to monthly values to join CMIP3 to NOAA
# observations
co2_cmip3 = pandas.read_csv(root / "source/CMIP3_CO2/CMIP3_CO2_1850_2011.csv")
co2_noaa = pandas.read_csv(root / "source/NOAA_CO2/co2_mm_gl.csv", comment="#")

co2_noaa = co2_noaa[["year", "month", "average"]]
co2_noaa = co2_noaa.rename(columns={"average": "average_co2_ppm"})


# 1) Monthly data

# Get mid year date for annual value and set up an interpolator function
co2_cmip3["date"] = co2_cmip3["year"].astype("str") + "-07-01"
date_as_numpy = co2_cmip3["date"].to_numpy().astype("datetime64[D]")

interp_func = interp1d(
    x=date_as_numpy.astype(int), y=co2_cmip3["co2"], bounds_error=False
)

# Get time sequence from 1850 to start of NOAA data at monthly intervals with daily
# precision and convert to pandas to get the handy date component attributes
months = np.arange(
    np.datetime64("1850-01"), np.datetime64("1979-01"), np.timedelta64(1, "M")
).astype("datetime64[D]")
pd_months = pandas.to_datetime(months)

# Assemble the interpolated dataframe - need to cast to int here because that is what
# the interpolator is using along the interpolation axis.
co2_cmip3_monthly = pandas.DataFrame(
    {
        "year": pd_months.year,
        "month": pd_months.month,
        "average_co2_ppm": interp_func(months.astype(int)),
    }
)

# Create a single time series
co2_monthly = pandas.concat([co2_cmip3_monthly, co2_noaa])

# Remov spurious accuracy and save
co2_monthly["average_co2_ppm"] = co2_monthly["average_co2_ppm"].round(3)
co2_monthly.to_csv(
    root / "derived/co2/co2_cmip3_noaa_interpolated_monthly.csv",
    index=False,
    na_rep="NA",
)

# 2) Daily data

# Reinterpolate CMIP3 to daily values
# Get time sequence from 1850 to start of NOAA data at daily intervals
cmip3_days = np.arange(
    np.datetime64("1850-01"), np.datetime64("1979-01"), np.timedelta64(1, "D")
).astype("datetime64[D]")

pd_days = pandas.to_datetime(cmip3_days)

# Assemble the interpolated CMIP3 dataframe
co2_cmip3_daily = pandas.DataFrame(
    {
        "year": pd_days.year,
        "month": pd_days.month,
        "days": pd_days.day,
        "average_co2_ppm": interp_func(cmip3_days.astype(int)),
    }
)

# Now interpolate the NOAA monthly data to daily
co2_noaa["day"] = 15
co2_noaa["date"] = pandas.to_datetime(co2_noaa[["year", "month", "day"]])
date_as_numpy = co2_noaa["date"].to_numpy().astype("datetime64[D]")

# Joining with the last daily value from CMIP3 to avoid a gap in the first two weeks of
# January 1980
interp_x = np.concat([cmip3_days[[-1]], date_as_numpy])
interp_y = np.concat(
    [co2_cmip3_daily["average_co2_ppm"].iloc[[-1]], co2_noaa["average_co2_ppm"]]
)

interp_func_noaa = interp1d(x=interp_x.astype(int), y=interp_y, bounds_error=False)

days = np.arange(
    np.datetime64("1979-01"), np.datetime64("2024-05"), np.timedelta64(1, "D")
).astype("datetime64[D]")
pd_days = pandas.to_datetime(days)


# Assemble the interpolated NOAA dataframe
co2_noaa_daily = pandas.DataFrame(
    {
        "year": pd_days.year,
        "month": pd_days.month,
        "days": pd_days.day,
        "average_co2_ppm": interp_func_noaa(days.astype(int)),
    }
)

# Create a single time series
co2_daily = pandas.concat([co2_cmip3_daily, co2_noaa_daily])

# Remov spurious accuracy and save
co2_daily["average_co2_ppm"] = co2_daily["average_co2_ppm"].round(3)
co2_daily.to_csv(
    root / "derived/co2/co2_cmip3_noaa_interpolated_daily.csv",
    index=False,
    na_rep="NA",
)
