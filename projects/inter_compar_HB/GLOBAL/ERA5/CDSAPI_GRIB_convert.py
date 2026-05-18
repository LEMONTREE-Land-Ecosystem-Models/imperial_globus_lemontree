"""Simple conversion tool using ECMWF earthkit.data to convert CDS GRIB to NetCDF."""

import sys

import earthkit.data as ekd


def convert_GRIB_to_NetCDF(source: str, dest: str):

    # Load the data from a GRIB file
    grib_data = ekd.from_source("file", source)

    # Convert it using valid_time dimensions and dropping the optional earthkit metadata
    xarray_data = grib_data.to_xarray(time_dims="valid_time", add_earthkit_attrs=False)

    # Reduce byte depth to save space
    xarray_data = xarray_data.astype("float32")

    # Save to file
    xarray_data.to_netcdf(dest)


if __name__ == "__main__":
    # Use the command line args to run the conversion from src to dest.
    convert_GRIB_to_NetCDF(sys.argv[1], sys.argv[1])
