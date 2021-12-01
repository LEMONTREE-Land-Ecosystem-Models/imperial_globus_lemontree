#!/bin/bash

# This script extracts the zipped downloads of the WFDE5 data on a compute node, 
# not the login. The contents are heavily compressed NetCDF4 files, so keeping
# them inside archives does not save file space

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -J 1-41
#PBS -o /rds/general/project/lemontree/live/source/wfde5/download_wfde5_v2.out

# Skip Elev, which is constant
variables=(LWdown PSurf Qair Rainf Snowf SWdown Tair Wind)

# Each job handles a different year
year=$(expr 1978 + $PBS_ARRAY_INDEX)

# Loop over the variables.
for var in "${variables[@]}"; 
do 
	echo $v; 
	cd /rds/general/project/lemontree/live/source/wfde5/wfde5_v2/$var
	mkdir -p $year
	target_file=WFDE5_v2.0_${var}_${year}.zip 
	unzip $target_file -d $year
	# rm $target_file
done