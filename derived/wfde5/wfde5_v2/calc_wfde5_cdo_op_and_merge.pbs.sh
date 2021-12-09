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

# Get and check the cdo operator is set
while getopts :o: flag
do
    case "${flag}" in
        o) operator=${OPTARG};;
        \?) echo "Usage: cmd -o cdo_operator var1 var ...";
            exit 1;
     esac
    esac
done

if [ -z "$operator" ] ;
then
    echo 'No cdo operator set'
    exit 1;
fi

# Jump forward of option indexes to get to variables
shift $(expr $OPTIND - 1)

# Each job handles a different year
year=$(expr 1978 + $PBS_ARRAY_INDEX)

# Paths and make sure the daily_means outputs location exists
src_path=/rds/general/project/lemontree/live/source/wfde5/wfde5_v2
der_path=/rds/general/project/lemontree/live/derived/wfde5/wfde5_v2/


# Loop over the provided variables 
for var in "$@";
do 
    echo $var;
    
    # Move to the variable directory and make if needed
    outdir=${der_path}/${operator}/
    mkdir -p $outdir
    cd $outdir

    # Loop over the months in the year folder
    for each_file in ${src_path}/${var}/${year}/*; 
    do 
        echo $each_file;
        # Find the daymeans and save to a temporary file,
        # including year to avoid jobs deleting each others outputs
        temp_file=${operator}_${year}_$(basename $each_file)
        cdo -f nc4c -z zip_6 -${operator} $each_file $temp_file 
    done

    # Merge the files and then remove the temporary ones.
    cdo mergetime -f nc4c -z zip_6 ${operator}_${year}* ${var}_WFDE5v2_CRU_${operator}_${year}.nc
    rm ${operator}_${year}*
done

