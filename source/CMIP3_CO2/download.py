"""Downloads and reformats the NASA CMIP3 CO2 forcings"""

import io
import pandas
import requests

# Download the data
data = requests.get("https://data.giss.nasa.gov/modelforce/ghgases/Fig1A.ext.txt")
data_text = io.StringIO(data.text)

# Parse the data from the table:
# Ice-    1850  285.2         1900  295.7         1950  311.3         2000  369.64

data_parsed = pandas.read_fwf(
    data_text, skiprows=5, nrows=50, widths=[8, 4, 8] * 4, header=None
)

year = pandas.concat([data_parsed[1], data_parsed[4], data_parsed[7], data_parsed[10]])
co2 = pandas.concat([data_parsed[2], data_parsed[5], data_parsed[8], data_parsed[11]])

data = pandas.DataFrame({"year": year, "co2": co2})
data = data.dropna().reset_index().drop(columns="index")
data["year"] = data["year"].astype(int)

data.to_csv("CMIP3_CO2_1850_2011.csv", index=None)
