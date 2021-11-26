#!/bin/bash

# This script runs the download of the WFDE5 data on a compute node, not the login

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/source/wfde5/download_wfde5_v2.out

module load anaconda3/personal

# Activate a conda environment, which needs cdsapi:
# pip install cdsapi

source activate base

python download_wfde5_v2.py

conda deactivate