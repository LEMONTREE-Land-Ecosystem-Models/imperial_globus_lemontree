#!/bin/bash

# This script repakages the incoming data from individual day files in landonly
# vectors to netcdf files containing a year of data in an unpacked grid

# Use the throughput class - single node, single cpu

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -J 1-21
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/conversion_^array_index^.out

# Env vars needed:
#
# * Use VAR to set the variable 
# * Use YEARONE to set the starting year
# Example:
# qsub -v VAR=FPAR,YEARONE=1982 check_limits_SNU_Ryu.pbs.sh 

module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running:\n VAR: $VAR\n  OUTDIR_SUFFIX: $OUTDIR_SUFFIX\n  ARR_IND:  $PBS_ARRAY_INDEX\n  PACK: ${PACK:-Not set}"

python /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/check_limits_SNU_Ryu.py

conda deactivate
