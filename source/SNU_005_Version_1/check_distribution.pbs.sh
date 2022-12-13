#!/bin/bash

# This script repakages the incoming data from individual day files in landonly
# vectors to netcdf files containing a year of data in an unpacked grid

# Use the throughput class - single node, single cpu

#PBS -lselect=1:ncpus=1:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o limit_checker.out

# Env vars needed:
#
# * Use VAR to set the variable 
# * Use DIR to set the root directory

# Example:
# qsub -v VAR=FPAR,DIR=/path/to/dir check_limits_SNU_Ryu_monthly.pbs.sh 

module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running:\n VAR: $VAR\n"

python /rds/general/project/lemontree/live/source/SNU_005_Version_1/check_distribution.py

conda deactivate
