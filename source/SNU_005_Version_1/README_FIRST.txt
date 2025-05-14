# Processing notes on Version 1

These data files have been reprocessed from the original provided files. The
original files were provided as:

* Individual daily NetCDF files (~ 75K files total). The number of files made
  data handling slow.
* Data encoded as float32 (four bytes), which is common but provides a high degree
  of precision that is not warranted.
* Each dataset had a defined value to indicate missing data, but this had not 
  been set in the file metadata.

These files have been reformatted as follows:

* The files for each variable have been compiled into annual 3 dimensional 
  NetCDF files (time, lat, long).
* The time data is recorded in the NetCDF time dimension as correct dates.
* The files have encoded into unsigned integer data (uint16, or uint for MCMD4)
  to save disk space and make the files quicker to work with.
* The offsets and scaling factors for those encoding are recorded in the NetCDF
  file attributes and many programs will automatically decode to floating point
  data when loading.
* Missing values have been standardised to integer values 65535 (or 255 for 
  MCMD4) and this is recorded in the NetCDF attributes.

## Data alteration

Scanning the daily ranges of the original input files showed some extreme values
outside of the expected ranges of the variables. The data in the original input
files have been edited as follows: 

* Some files for variables bounded below at zero contained values very slightly
  below zero. These values were clamped: values less than zero were set to zero.

* Some files contained unexpectedly high values (e.g. FAPAR > 1). These values
  have been set to NA.

The clamping and upper limit values are recorded in the NetCDF attributes.

