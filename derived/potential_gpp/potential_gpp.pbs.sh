#!/bin/bash

# This script runs the potential GPP calculations by year.

# NOTES:
#
# * If this analysis is reworked to include soil moisture, including splash, then it
#   will need to run as a single job to iterate over the soil moisture years in turn.
#
# * Running a single year may be too short for a sensible job spec, in which case the
#   array index could be used to loop over decades for the 1901 - 2018 data
#
# * Use the throughput class - single node, single cpu, using GPFS for better file
#   handling

#PBS -lselect=1:ncpus=8:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -J 1901-2018
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/potential_gpp_^array_index^.out


module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running"

date

python /rds/general/project/lemontree/live/derived/potential_gpp/potential_gpp.py

date

conda deactivate
