"""Extract example site data.

This script extracts time series for specific sites from the various potential GPP
workflow datasets and outputs a single (relatively) small dataset for use in making
validation and demonstration plots
"""

from pathlib import Path

import xarray


root = Path("/rds/general/project/lemontree/live")

# Define three sites for showing time series
sites = xarray.Dataset(
    data_vars=dict(
        lon=(["site_id"], [-122.419, -119.538, -116.933]),
        lat=(["site_id"], [37.775, 37.865, 36.532]),
    ),
    coords=dict(site_id=(["San Francisco", "Yosemite", "Death Valley"])),
)

# Load the SPLASH files into an MF dataset
splash_files = list((root / "derived/splash_cru_ts4.07/data").glob("*.nc"))
splash_mf_dataset = xarray.open_mfdataset(splash_files)

# Read in the SPLASH data for the sites - the compute() method causes the data
# to be actually loaded from the MF dataset, which is opened lazily.
splash_at_sites = splash_mf_dataset.sel(sites, method="nearest").compute()

# Load the soil moisture stress data into an MF dataset
soilmstress_files = list((root / "derived/aridity/data").glob("soilmstress_mengoli_*.nc"))
soilmstress_mf_dataset = xarray.open_mfdataset(soilmstress_files)

# Read in the SPLASH data for the sites - the compute() method causes the data
# to be actually loaded from the MF dataset, which is opened lazily.
soilmstress_at_sites = soilmstress_mf_dataset.sel(sites, method="nearest").compute()

# Load the annual aridity index
aridity_dataset = xarray.open_dataset(root / "derived/aridity/data/annual_aridity_indices.nc")
aridity_at_sites = aridity_dataset.sel(sites, method="nearest").compute()

# Load the GPP data into an MF dataset
gpp_files = list((root / "derived/potential_gpp/data").glob("*.nc"))
gpp_mf_dataset = xarray.open_mfdataset(gpp_files)

# Read in the SPLASH data for the sites - the compute() method causes the data
# to be actually loaded from the MF dataset, which is opened lazily.
gpp_at_sites = gpp_mf_dataset.sel(sites, method="nearest").compute()

# Combine the site data into a single Dataset for export
site_data = xarray.merge(
    [splash_at_sites, soilmstress_at_sites, aridity_at_sites, gpp_at_sites]
)
site_data.to_netcdf(root / "derived/potential_gpp/example_site_data.nc")
