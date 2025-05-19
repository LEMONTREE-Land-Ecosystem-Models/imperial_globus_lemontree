#!/bin/bash

# This script extracts annual geo grids from the cleaned SNU data

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/extract_annual_grids.out


# Activate the conda environment
eval "$(~/miniforge3/bin/conda shell.bash hook)"
conda activate pyrealm_py312

# Echo the python version and start time
python --version
echo -e "In PBS.SH and running"
date

python /rds/general/project/lemontree/live/source/SNU_2024/extract_annual_grids.py

date
conda deactivate
