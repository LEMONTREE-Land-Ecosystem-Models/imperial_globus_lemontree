#!/bin/bash

# This script downloads CHELSA monthly variables

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/chelsa_download.out


# Activate the conda environment - can just use base as the script only uses standard
# library commands
eval "$(~/miniforge3/bin/conda shell.bash hook)"

# Echo the python version and start time
python --version
echo -e "In PBS.SH and running"
date

python /rds/general/project/lemontree/live/source/CHELSA/chelsa_download_monthly.py

date
conda deactivate
