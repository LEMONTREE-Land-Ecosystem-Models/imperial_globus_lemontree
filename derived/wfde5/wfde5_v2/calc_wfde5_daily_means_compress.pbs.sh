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

# Skip Elev, which is constant, and wind which is a bit meaningless
variables=(LWdown PSurf Qair Rainf Snowf SWdown Tair)

# Each job handles a different year
year=$(expr 1978 + $PBS_ARRAY_INDEX)

# Paths and make sure the daily_means outputs location exists
der_path=/rds/general/project/lemontree/live/derived/wfde5/wfde5_v2/daily_means/

# Loop over the variables.
for var in "${variables[@]}"; 
do 
    echo $var;
    cd $der_path
    
    # Move to the variable directory and make if needed
    cd $var
    
    # Merge the files and then remove the temporary ones.
    target=${var}_WFDE5v2_CRU_daily_means_${year}.nc
    mv $target ${target}.bak
    cdo -z zip_6 selall ${target}.bak $target
done
