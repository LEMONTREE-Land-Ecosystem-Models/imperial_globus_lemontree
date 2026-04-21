#!/bin/bash

# This script runs the download of the ERA5 data on a compute node, not the login

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5_download.out

eval "$(~/miniforge3/bin/conda shell.bash hook)"

# Activate a conda environment, which needs cdsapi:
# pip install cdsapi

python /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5_download_cdsswarm.py

conda deactivate
