import numpy as np
import pandas
from pathlib import Path
from scipy.interpolate import interp1d

root = Path("/rds/general/project/lemontree/live/")

# Load global CO2 data and interpolate to monthly values to join CMIP3 to NOAA
# observations
co2_cmip3 = pandas.read_csv(root / "source/CMIP3_CO2/CMIP3_CO2_1850_2011.csv")
co2_noaa = pandas.read_csv(root / "source/NOAA_CO2/co2_mm_gl.csv", skiprows=55)

# Get mid year date for annual value and set up an interpolator function
co2_cmip3["date"] = co2_cmip3["year"].astype("str") + "-07-01"
date_as_numpy = co2_cmip3["date"].to_numpy().astype("datetime64[D]")

interp_func = interp1d(
    x=date_as_numpy.astype(int), y=co2_cmip3["co2"], bounds_error=False
)

# Get time sequence from 1850 to start of NOAA data at monthly intervals with daily
# precision
months = np.arange(
    np.datetime64("1850-01"), np.datetime64("1979-01"), np.timedelta64(1, "M")
).astype("datetime64[D]")

# Assemble the interpolated dataframe
co2_cmip3_monthly = pandas.DataFrame(
    {
        "year": np.repeat(np.arange(1850, 1979), 12),
        "month": np.tile(np.arange(1, 13), 1979 - 1850),
        "average": interp_func(months.astype(int)),
    }
)

# Create a single time series
co2 = pandas.concat([co2_cmip3_monthly, co2_noaa[["year", "month", "average"]]])

# Formatting and naming
co2.rename(columns={"average": "average_co2_ppm"}, inplace=True)
co2["average_co2_ppm"] = co2["average_co2_ppm"].round(3)
co2.to_csv(
    root / "derived/co2/co2_cmip3_noaa_interpolated.csv", index=False, na_rep="NA"
)
