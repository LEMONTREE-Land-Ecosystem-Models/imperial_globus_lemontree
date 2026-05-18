#!/bin/bash

# This script downscales the original ERA5 single level 0.25° resolution data to the
# required 0.5° resolution data. It runs as an array job to parallelise conversion of
# different variables. This job handles the eight variables downloaded through the ARCO
# API - the remaining two variables need to be downloaded as GRIB using CDSAPI and then
# converted to NetCDF before resampling.

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -J 0-9
#PBS -o /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5/ERA5_downscale_^array_index^.out

module load CDO

# Select a variable to convert based on the array index

VARIABLES=("u10" "v10" "d2m" "t2m" "sp" "tp" "ssrd" "strd" "mx2t" "mn2t")
THIS_VAR=${VARIABLES[$PBS_ARRAY_INDEX]}

# Switch between the two possible source directories
if [[ "$THIS_VAR" == "mx2t" || "$THIS_VAR" == "mn2t" ]]; then
    VAR_DIR="ERA5_CDSAPI"
else
    VAR_DIR="ERA5_ARCO"
fi

# Setup the source and destination directories
SRC_DIR="/rds/general/project/lemontree/ephemeral/${VAR_DIR}/${THIS_VAR}"
DEST_DIR="/rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5"

# Make a variable specific output if one doesn't exist
mkdir -p $DEST_DIR/$THIS_VAR

# Iterate over the source directory contents, converting to mildly compressed NetCDF at
# 0.5° resolution. We are using remapbil to generate bilinear estimates of the cell
# centres of a regular 0.5° lat/lon grid.

for file in $SRC_DIR/*.nc ; 
    do echo $file; 
    cdo -z zip_6  \
        remapbil,/rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5/half_degree.grd \
        $file \
        $DEST_DIR/$THIS_VAR/$(basename $file)
done
