#!/bin/bash

# This script cleans the raw SNU 2024 netcdf datasets.

#PBS -lselect=1:ncpus=1:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/standardise_and_add_coords.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

date

python /rds/general/project/lemontree/live/source/SNU_2024/standardise_and_add_coords.py

date

conda deactivate
