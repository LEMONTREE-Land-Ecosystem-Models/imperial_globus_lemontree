# SE Asia models

This project directory is being used to develop high resolution models of GPP and fire
risk for South East Asia.

The `HPC_setup.sh` file contains `bash` code to set up an new Python environment on the
Imperial HPC containing the required packages for running the modelling.

## GPP Models

The `gpp` directory contains predications of GPP using `pyrealm` and the following
forcing variables:

* Temperature: CHELSA `tas` converted from Kelvins/10
* VPD: CHELSA `vpd` data provided as Pascals.
* PPFD: CHELSA `rsds` data converted from MJ m2 day to PPFD in µmol m2 s1.
* Atmospheric pressure, converted from GMTED2010 elevation using `calc_patm`.
* CO2 concentration using the global NOAA dataset
* fAPAR: from SNU fAPAR.

For the spatial and temporal resolution we have:

* We are using the CHELSA monthly datasets at 1/120° resolution (30 arc seconds, 0.0083°,
  ~1km at the equator). GMTED is also 1/120°.
* The FPAR data from SNU is monthly and at 1/20° resolution (0.05°, ~5km at the
  equator), and is upscaled simply by tiling the values from a single value to 6x6
  cells.
* The CO2 is monthly global data with the same value used for all cells.

### Code Files

* `gpp/GPP_models.py`: The python script to: load the data; do all of the data wrangling
  to get data into the right formats, units and shapes; and then run the models.
* `gpp/GPP_models.pbs.sh`: A bash script to submit the Python code to the HPC queueing
  system. The file takes around 10 hours to run.

### Outputs

The Python file writes out annual NetCDF files to (e.g.) `gpp/data/se_asia_gpp_1982.nc`
along with simple summary statistics for the models as
`data/se_asia_gpp_1982_summary.txt`.

Each NetCDF file contains monthly data for a single year for all cells within the region
of interest. There are two data variables:

* `potential_gpp` uses fAPAR=1 and phi0=1/8; and
* `brc_model_gpp` uses the actual fAPAR data and phi0=0.081785 to match the settings
  used for the `BRC` model for use with the Stocker soil moisture penalty.

Dataset structure:

```text
<xarray.Dataset> Size: 3GB
Dimensions:        (time: 12, y: 4800, x: 5880)
Coordinates:
  * x              (x) float64 47kB 92.0 92.01 92.02 92.03 ... 141.0 141.0 141.0
  * y              (y) float64 38kB 29.0 28.99 28.98 ... -10.98 -10.99 -11.0
    spatial_ref    int64 8B ...
  * time           (time) datetime64[ns] 96B 1982-01-01 ... 1982-12-01
Data variables:
    potential_gpp  (time, y, x) float32 1GB ...
    brc_model_gpp  (time, y, x) float32 1GB ...
```

## Soil moisture penalty

The `soil_moisture_penalty` directory contains estimates of soil moisture calculated
using the `pyrealm.splash` model using the following inputs:

* Temperature: CHELSA `tas` data converted from Kelvins/10
* Precipitation: CHELSA `pr` data converted from kg m-2 month-1 to mm day-1.
* Sun fraction: CHELSA `clt` percentage data converted as (1 - (clt/100)).
* Elevation: GMTED 2010 mean elevation data.

All datasets are at 30 arc-second resolution _except_ for some unknown reason the
downloaded monthly CHELSA cloud data is 90 arc-second resolution (~3 km). The cloud data
is therefore simply tiled to 3x3 cell blocks.

All three CHELSA variables are monthly and SPLASH requires daily inputs. Temperature and
sun fraction are already monthly mean values and so were simply duplicated to give daily
values; precipitation is a monthly total and is divided evenly across the days of the
month.

### Code files

Because the data is converted to daily values, the memory requirements for the SPLASH
analysis are much larger than for the GPP calculations. The code to calculate soil
moisture therefore runs subsets of 2° latitudinal bands.

* The file `soil_moisture_penalty/soil_moisture_banded.py` is Python code to load the
  required data for a given 2° latitudinal band, calculate daily soil moisture and then
  write out annual files containing monthly mean soil moisture and total annual PET and
  AET.
* The file `soil_moisture_penalty/soil_moisture_banded.pbs.sh` is then a PBS job
  submission script that creates an array job running each of the 20 x 2° bands. Each 2°
  array job requires ~88GB RAM. The runtime is variable but the longest was about 7
  hours. Each job creates writes an output file (e.g.) `soil_moisture_1982_band_0.nc`.

* The files `soil_moisture_penalty/compile_banded_data.py` and
  `soil_moisture_penalty/compile_banded_data.pbs.sh` provides a simple PBS job to
  compile the 20 x 2° band outputs into single annual files for the whole region. The
  results are saved as `soil_moisture_1982.nc` with the following structure:

  ```text
  <xarray.Dataset> Size: 2GB
  Dimensions:           (time: 12, y: 4800, x: 5880)
  Coordinates:
    * x                 (x) float64 47kB 92.0 92.01 92.02 ... 141.0 141.0 141.0
    * y                 (y) float64 38kB 29.0 28.99 28.98 ... -10.98 -10.99 -11.0
      spatial_ref       int64 8B ...
    * time              (time) datetime64[ns] 96B 1985-01-01 ... 1985-12-01
  Data variables:
      monthly_wn        (time, y, x) float32 1GB 15.7 15.83 15.99 ... 51.42 51.39
      total_annual_aet  (y, x) float32 113MB ...
      total_annual_pet  (y, x) float32 113MB ...
  ```
  
  After this job has been run, the banded files (`soil_moisture_1982_band_0.nc` etc) can
  be deleted. The job took 2.5 hours and used 823856kb (~1GB) of RAM.

* The files `soil_moisture_penalty/calculate_stocker_penalty.py` and
  `soil_moisture_penalty/calculate_stocker_penalty.pbs.sh` provides a PBS job to
  calculate the aridity index as AET / PET across all years and then calculate monthly
  values for the Stocker soil moisture penalty using `monthly_wn / 150` as the estimate
  of soil moisture content. The results are saved as files `stocker_penalty_1982.nc`
  with the following structure:

  ```text
  Out[83]: 
  <xarray.Dataset> Size: 1GB
  Dimensions:          (time: 12, y: 4800, x: 5880)
  Coordinates:
    * x                (x) float64 47kB 92.0 92.01 92.02 ... 141.0 141.0 141.0
    * y                (y) float64 38kB 29.0 28.99 28.98 ... -10.98 -10.99 -11.0
      spatial_ref      int64 8B ...
    * time             (time) datetime64[ns] 96B 1985-01-01 ... 1985-12-01
  Data variables:
      stocker_penalty  (time, y, x) float32 1GB 0.6217 0.6258 ... 0.8956 0.8953
  ```
  
  The job takes around 15 minutes to run and uses 10130808Kb (~10GB RAM).
