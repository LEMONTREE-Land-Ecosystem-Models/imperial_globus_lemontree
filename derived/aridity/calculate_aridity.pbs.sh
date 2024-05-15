#!/bin/bash

# This script calculates the Mengoli aridity index from the SPLASH model outputs for 
# the CRU TS 4.07 dataset

# Uses the throughput class - single node, single cpu, using GPFS for better file
# handling,

#PBS -lselect=1:ncpus=1:mem=100gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/calculate_aridity.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

date

python /rds/general/project/lemontree/live/derived/aridity/calculate_aridity.py

date

conda deactivate
