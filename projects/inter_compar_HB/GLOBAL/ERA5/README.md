# ERA 5 data processing

This directory contains the code to generate the ERA5 inputs for the intercomparison
project, along with the processed outputs of the code. There are ten variables
required and we need to use two separate workflows to get all the data:

## Download

The original source data are at 0.25° resolution and we need 0.5° resolution for the
project, so all of the files are downloaded to storage on the `ephemeral` directory
before being downsampled to locations inside the LEMOMTREE project directory.

### CDS ARCO

Eight of the variables are available as part of a new (as of 2026) API that gives direct
access to cloud optimised ZARR datasets that contain the most commonly used ERA5
variables.  Download from these resources is fast and uses xarray to directly save files
to NetCDF.

* u10: 10m_u_component_of_wind
* v10: 10m_v_component_of_wind
* d2m: 2m_dewpoint_temperature
* t2m: 2m_temperature
* sp: surface_pressure
* tp: total_precipitation
* ssrd: surface_solar_radiation_downwards
* strd: surface_thermal_radiation_downwards

### CDSAPI

The remaining two variables have not been included in the ARCO dataset and have to be
downloaded using the standard CDSAPI interface. This is throttled - the `CDSAPI_testing`
directory shows how response time varies during a day when requesting many files - and
so is a slower process.

To improve the throughput, files are downloaded as GRIB, which reduces the request load
on the CDS servers, and we distribute the download effort across multiple users. This is
not using sockpuppet accounts - just using existing valid accounts to share the
downloading process.

The downloaded files then need to be converted from GRIB to NetCDF, which uses the new
`earthkit.data` package from ECMWF.

## Downsampling

The downloaded NetCDF files are then resampled to 0.5° using bilinear remapping in CDO
(`cdo remapbil`) and the outputs are written to variable directories in this ERA5
directory. 