#!/bin/bash

# Run the data extraction

# NOTES:
#
# * Use the throughput class - single node, single cpu, using GPFS for better file
#   handling

#PBS -lselect=1:ncpus=1:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/vpd_and_gpp_site_extractor.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

date

python /rds/general/project/lemontree/live/projects/vpd_and_gpp/site_extractor.py

date

conda deactivate
