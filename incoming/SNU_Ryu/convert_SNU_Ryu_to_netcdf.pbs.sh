#!/bin/bash

# This script repakages the incoming data from individual day files in landonly
# vectors to netcdf files containing a year of data in an unpacked grid

# Use the throughput class - single node, single cpu

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -J 1-20
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/incoming/SNU_Ryu/conversion.out

# Submit using qsub -v SCRIPT_VAR=FPAR or qsub -v SCRIPT_VAR=LAI

module load anaconda3/personal

source activate base

python /rds/general/project/lemontree/live/incoming/SNU_Ryu/convert_SNU_Ryu_to_netcdf.py

conda deactivate
