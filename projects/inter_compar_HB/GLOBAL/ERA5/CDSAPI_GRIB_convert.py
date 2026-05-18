"""Simple conversion tool using ECMWF earthkit.data to convert CDS GRIB to NetCDF."""

import sys
import os
from pathlib import Path

import earthkit.data as ekd


def convert_GRIB_to_NetCDF(source: Path, dest: Path):

    # Load the data from a GRIB file
    grib_data = ekd.from_source("file", source)

    # Convert it using valid_time dimensions and dropping the optional earthkit metadata
    xarray_data = grib_data.to_xarray(time_dims="valid_time", add_earthkit_attrs=False)

    # Rename valid_time to restore CF compliance
    xarray_data_time = xarray_data.rename({"valid_time": "time"})

    # Reduce byte depth to save space
    xarray_data_time = xarray_data_time.astype("float32")

    # Save to file
    xarray_data_time.to_netcdf(dest)


# Get job array index to get a variable for the array job
job_index = int(os.environ.get("PBS_ARRAY_INDEX"))
variables = ("mx2t", "mn2t")
this_var = variables[job_index]

# Setup the source directory
src_dir = f"/rds/general/project/lemontree/ephemeral/ERA5_CDSAPI/{this_var}"

# Loop over files, writing NetCDF back into the same directory.
for file in Path(src_dir).glob("*.grib"):
    convert_GRIB_to_NetCDF(file, file.with_suffix(".nc"))
