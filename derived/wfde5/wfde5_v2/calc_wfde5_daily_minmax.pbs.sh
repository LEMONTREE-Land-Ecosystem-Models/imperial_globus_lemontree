#!/bin/bash

# This script uses CDO to calculate daily means of the WFDE 5 variables as 
# a job array looping over years.

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -J 1-41
#PBS -o /rds/general/project/lemontree/live/derived/wfde5/wfde5_v2/daily_min_max.out

module load cdo

# Each job handles a different year
year=$(expr 1978 + $PBS_ARRAY_INDEX)

# Paths and make sure the daily_means outputs location exists
src_path=/rds/general/project/lemontree/live/source/wfde5/wfde5_v2
der_path=/rds/general/project/lemontree/live/derived/wfde5/wfde5_v2/

# Loop over the variables - currently only Tair, but keeping loop in case others needed.
for var in Tair;
do 
    echo $var;
    
    for metric in min max;
    do
    
        # Move to the variable directory and make if needed
        outdir=${der_path}/daily_${metric}/${var}
        mkdir -p $outdir
        cd $outdir
    
        # Loop over the months in the year folder
        for each_file in ${src_path}/${var}/${year}/*; 
        do 
            echo $each_file;
            # Find the daymeans and save to a temporary file,
            # including year to avoid jobs deleting each others outputs
            temp_file=day${metric}_${year}_$(basename $each_file)
            cdo -f nc4c -z zip_6 -day${metric} $each_file $temp_file 
        done
    
        # Merge the files and then remove the temporary ones.
        cdo -f nc4c -z zip_6 mergetime day${metric}_${year}* ${var}_WFDE5v2_CRU_daily_${metric}_${year}.nc
        rm day${metric}_${year}*
    done
done

