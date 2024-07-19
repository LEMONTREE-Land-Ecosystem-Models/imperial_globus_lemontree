import numpy as np
import pandas as pd
from pathlib import Path
from scipy.interpolate import interp1d

root = Path("/rds/general/project/lemontree/live/")

# Load global CO2 data and interpolate to monthly values to join CMIP3 to NOAA
# observations
co2_cmip3 = pd.read_csv(root / "source/CMIP3_CO2/CMIP3_CO2_1850_2011.csv")
co2_noaa = pd.read_csv(root / "source/NOAA_CO2/co2_mm_gl.csv", comment="#")

# Reduce NOAA to required fields
co2_noaa = co2_noaa[["year", "month", "average"]]
co2_noaa = co2_noaa.rename(columns={"average": "co2"})

# Assign mid year dates to annual CMIP3 and mid month dates to monthly NOAA
co2_cmip3["month"] = 7
co2_cmip3["day"] = 1
co2_noaa["day"] = 15

# Combine to get a single time series and format as date
co2_data = pd.concat([co2_cmip3, co2_noaa])
co2_data["date"] = pd.to_datetime(co2_data[["year", "month", "day"]])

# Generate the interpolation function - need to use integer values for dates
interp_dates = co2_data["date"].to_numpy().astype("datetime64[D]")
interp_func = interp1d(
    x=interp_dates.astype(int), y=co2_data["co2"], bounds_error=False
)

# 1) Interpolate monthly data

# Get a mid month time sequence across the data with daily precision and convert to
# pandas to get the handy date component attributes

monthly = np.arange(
    np.datetime64("1850-01"), np.datetime64("2024-05"), np.timedelta64(1, "M")
) + np.timedelta64(14, "D")

pd_months = pd.to_datetime(monthly)

# Assemble the interpolated dataframe - need to cast to int here because that is what
# the interpolator is using along the interpolation axis.
co2_monthly = pd.DataFrame(
    {
        "year": pd_months.year,
        "month": pd_months.month,
        "average_co2_ppm": interp_func(monthly.astype(int)),
    }
)

# Remov spurious accuracy and save
co2_monthly["average_co2_ppm"] = co2_monthly["average_co2_ppm"].round(3)
co2_monthly.to_csv(
    root / "derived/co2/co2_cmip3_noaa_interpolated_monthly.csv",
    index=False,
    na_rep="NA",
)

# 2) Daily data

# Get a daily time sequence across the data with daily precision and convert to
# pandas to get the handy date component attributes
daily = np.arange(
    np.datetime64("1850-01-01"), np.datetime64("2024-05-01"), np.timedelta64(1, "D")
).astype("datetime64[D]")

pd_days = pd.to_datetime(daily)

# Assemble the interpolated CMIP3 dataframe
co2_daily = pd.DataFrame(
    {
        "year": pd_days.year,
        "month": pd_days.month,
        "days": pd_days.day,
        "average_co2_ppm": interp_func(daily.astype(int)),
    }
)

# Remove spurious accuracy and save
co2_daily["average_co2_ppm"] = co2_daily["average_co2_ppm"].round(3)
co2_daily.to_csv(
    root / "derived/co2/co2_cmip3_noaa_interpolated_daily.csv",
    index=False,
    na_rep="NA",
)
