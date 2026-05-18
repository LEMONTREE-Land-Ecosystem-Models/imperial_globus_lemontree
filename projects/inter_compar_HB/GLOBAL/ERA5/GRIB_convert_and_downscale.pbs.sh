#!/bin/bash

# This script converts ERA5 variables downloaded as GRIB into NetCDF format and then
# resamples the original ERA5 single level 0.25° resolution data to the required 0.5°
# resolution data. It runs as an array job to parallelise conversion of different
# variables.

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -J 0-1
#PBS -o /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5/GRIB_convert_and_downscale_^array_index^.out

module load CDO

# Activate a conda environment python314_xarray, which needs:
# earthkit.data
eval "$(~/miniforge3/bin/conda shell.bash hook)"
conda activate python314_xarray

# Select a variable to convert based on the array index - the PBS settings above iterate
# over the two variables downloaded as GRID using the CDSAPI

# Long and short names for this job id
VARIABLES=(
    "maximum_2m_temperature_since_previous_post_processing:mx2t"
    "minimum_2m_temperature_since_previous_post_processing:mn2t"
)
THIS_VAR=${VARIABLES[$PBS_ARRAY_INDEX]}
LONG_NAME="$(cut -d':' -f1 <<< $THIS_VAR)"
SHORT_NAME="$(cut -d':' -f2 <<< $THIS_VAR)"

# Setup the source and destination directories
SRC_DIR="/rds/general/project/lemontree/ephemeral/ERA5_swarm_array/${LONG_NAME}"
DEST_DIR="/rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5"

# Make a variable specific output if one doesn't exist
mkdir -p $DEST_DIR/$SHORT_NAME

# Iterate over the source directory contents, converting to mildly compressed NetCDF at
# 0.5° resolution. We are using remapbil to generate bilinear estimates of the cell
# centres of a regular 0.5° lat/lon grid.



for file in $SRC_DIR/* ; 
    do echo $file;

    # Get output filename with short form name
    SRC_FILENAME=$(basename $file)
    DST_FILENAME=${SRC_FILENAME/$LONG_NAME/$SHORT_NAME}
    DST_FILENAME=${DST_FILENAME/.grib/.nc}

    # Get paths to converted file and to converted and downscaled
    CONVERTED=$SRC_DIR/$DST_FILENAME
    DOWNSCALED=$DEST_DIR/$SHORT_NAME/$DST_FILENAME 

    # Convert the file to NetCDF using earthkit.data
    python /rds/general/projects/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5/GRIB_convert.py $file $CONVERTED

    cdo -z zip_6  \
        remapbil,/rds/general/projects/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5/ERA5_grid_half_degree.txt \
        $CONVERTED $DOWNSCALED 
done


conda deactivate # Out of python314_xarray
conda deactivate # Out of base
