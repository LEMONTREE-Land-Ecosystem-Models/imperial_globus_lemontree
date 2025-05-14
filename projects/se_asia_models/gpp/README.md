# SE Asia models

This project directory is being used to develop high resolution models of GPP and fire
risk for South East Asia.

## GPP Models

We are using `pyrealm` to estimate GPP from the following forcing variables:

* Temperature: CHELSA tas data - note that this is provided as Kelvins/10!
* VPD: CHELSA tas data  - provided as Pascals.
* Atmospheric pressure: Some data sets have time series data for pressure, but I don’t
  think CHELSA does. Are we ok to use constant pressure within grid cells simply derived
  from altitude from one of the elevation datasets?
* CO2 concentration. We don’t have spatial data for CO2 - can we just use the NOAA Mauna
  Loa global values?
* fAPAR: from SNU
* PPFD: CHELSA RSDS data - note that CHELSA RSDS is MJ m2 day and we need PPFD in µmol
  m2 s1, so it isn’t just RSDS * 2.04, but should be easy enough to convert.

For the spatial and temporal resolution we have:

* We are using the CHELSA monthly datasets at 1/120° resolution (30 arc seconds, 0.0083°,
  ~1km at the equator).
* The FPAR data from SNU is 1/20° resolution (0.05°, ~5km at the equator) and is daily
  (although there are multiple versions and I think the newest ones might be monthly).

### Files

* `gpp/HPC_setup.sh`: This file contains bash code to set up an new Python environment
  on the Imperial HPC containing the required packages.
* `gpp/GPP_models.py`: A draft script to run the model, currently using placeholder
  values for some variables, but using `rasterio` to load the region of interest for the
  CHELSA data.
* `gpp/GPP_models.pbs.sh`: A draft bash script to submit the job to the HPC queueing
  system. This will get more complex if we want to run chunks of the analysis in
  parallel.
