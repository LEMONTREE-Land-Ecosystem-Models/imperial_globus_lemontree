#!/bin/bash

# This script runs the SPLASH model across the CRU TS 4.07 dataset

# Uses the throughput class - single node, single cpu, using GPFS for better file
# handling,

#PBS -lselect=1:ncpus=1:mem=100gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/run_splash.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

date

python /rds/general/project/lemontree/live/derived/splash_cru_ts4.07/run_splash_v2.py

date

conda deactivate
