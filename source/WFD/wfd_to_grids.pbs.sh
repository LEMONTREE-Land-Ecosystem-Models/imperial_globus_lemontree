#!/bin/bash

# This script repackages the WFD from monthly files ofland cells only into annual grids

# Use the throughput class - single node, single cpu, using GPFS for better file handling

#PBS -lselect=1:ncpus=8:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -J 1901-2001
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/wfd_gridded_^array_index^.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

python /rds/general/project/lemontree/live/source/WFD/wfd_to_grids.py

conda deactivate
