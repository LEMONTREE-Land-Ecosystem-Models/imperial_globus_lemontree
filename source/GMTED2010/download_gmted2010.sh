#! /bin/bash

# Download script for GMTED2010 datasets.

# This script downloads the GMTED2010 datasets from the USGS website and converts to
# GeoTIff. The GMTED2010 datasets provide global elevation data at a range of spatial
# resolutions (7.5, 15 and 30 arc seconds) and the links below provide bulk download of
# global grids. There are also various aggregation methods used to get cell values for
# elevation: this script currently downloads the mean and breakline emphasis datasets at
# 30 arc seconds. The breakline emphasis dataset preserves local minima and maxima so as
# not to round off the edges of mountains and valleys. The mean is probably a better
# choice for analysis.

# Requires gdal_translate to convert ArcInfo to GeoTIFF format.
module load GDAL

# Download a product description PDF
curl -O https://pubs.usgs.gov/ds/2012/3017/pdf/ds3017.pdf


# Download the Breakline Emphasis dataset at 30 arc seconds
mkdir be30
cd be30
curl -O https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/topo/downloads/GMTED/Grid_ZipFiles/be30_grd.zip
unzip be30_grd.zip

# Convert the ArcInfo grid to GeoTIFF
gdal_translate be30_grd/hdr.adf be30.tiff

# Remove the ArcInfo grid
rm -r be30_grd
rm -r info

cd ../

# Download the Mean dataset at 30 arc seconds
mkdir mn30
cd mn30
curl -O https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/topo/downloads/GMTED/Grid_ZipFiles/mn30_grd.zip
unzip mn30_grd.zip

# Convert the ArcInfo grid to GeoTIFF
gdal_translate mn30_grd/hdr.adf mn30.tiff

# Remove the ArcInfo grid
rm -r mn30_grd
rm -r info

cd ../