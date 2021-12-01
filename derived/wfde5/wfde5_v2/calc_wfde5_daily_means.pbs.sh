#!/bin/bash

# This script uses CDO to calculate daily means of the WFDE 5 variables as 
# a job array looping over years.

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -J 1-41
#PBS -o /rds/general/project/lemontree/live/derived/wfde5/wfde5_v2/daily_means/download_wfde5_v2.out

module load cdo

# Skip Elev, which is constant
variables=(LWdown PSurf Qair Rainf Snowf SWdown Tair Wind)

# Each job handles a different year
year=$(expr 1978 + $PBS_ARRAY_INDEX)

# Paths and make sure the daily_means outputs location exists
src_path=/rds/general/project/lemontree/live/source/wfde5/wfde5_v2
der_path=/rds/general/project/lemontree/live/derived/wfde5/wfde5_v2/daily_means/
mkdir -p $der_path

# Loop over the variables.
for var in "${variables[@]}"; 
do 
    echo $v;
    cd $der_path
    
    # Move to the variable directory and make if needed
    mkdir -p $var
    cd $var
    
    # Loop over the months in the year folder
    for each_file in ${src_path}/${var}/${year}/*; 
    do 
        echo $each_file;
        # Find the daymeans and save to a temporary file,
        # including year to avoid jobs deleting each others outputs
        temp_file=daymean_${year}_$(basename $each_file)
        cdo -f nc4c -z zip_6 -daymean $each_file $temp_file 
    done
    
    # Merge the files and then remove the temporary ones.
    cdo mergetime daymean_${year}* ${var}_WFDE5v2_CRU_daily_means_${year}.nc
    rm daymean_${year}*
done
