#!/bin/bash

# This script runs the potential GPP calculations. It does not run years in parallel
# because each year only takes a few minutes so this is more HPC friendly.

# NOTES:
#
# * Use the throughput class - single node, single cpu, using GPFS for better file
#   handling

#PBS -lselect=1:ncpus=1:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/potential_gpp.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

date

python /rds/general/project/lemontree/live/derived/potential_gpp/potential_gpp_daily.py

date

conda deactivate
