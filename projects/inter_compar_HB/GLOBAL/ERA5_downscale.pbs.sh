#!/bin/bash

# This script downscales the original ERA5 single level 0.25° resolution data to the
# required 0.5° resolution data. It runs as an array job to parallelise conversion of
# different variables.

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -J 0-5
#PBS -o /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5_downscale_^array_index^.out

module load CDO

# Select a variable to convert based on the array index
VARIABLES=("u10" "v10" "d2m" "t2m" "sp" "tp" "ssrd" "strd" "tmin" "tmax")
THIS_VAR=${VARIABLES[$PBS_ARRAY_INDEX]}

# Setup the source and destination directories
SRC_DIR="/rds/general/project/lemontree/ephemeral/ERA5_ARCO/${THIS_VAR}"
DEST_DIR="/rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5"

# Make a variable specific output if one doesn't exist
mkdir -p $DEST_DIR/$THIS_VAR

# Iterate over the source directory contents, converting to mildly compressed NetCDF at
# 0.5° resolution
for file in $SRC_DIR/* ; 
    do echo $file; 
    cdo -z zip_6 gridboxmean,2,2 $file $DEST_DIR/$THIS_VAR/$(basename $file)
done
