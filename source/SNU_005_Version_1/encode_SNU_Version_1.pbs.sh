#!/bin/bash

# This script encodes compiled monthly data files using integer data to improve
# file size and compression by discarding spurious precision.

# Use the throughput class - single node, single cpu, using GPFS for better file handling

#PBS -lselect=1:ncpus=8:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -J 1-21
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/conversion_^array_index^.out

# Env vars needed:
#
# * Use VAR to set the variable 
# * Use OUTDIR_SUFFIX to set the suffix on the output dir,
#        e.g. OUTDIR_SUFFIX=in_here -> FPAR_in_here
# * Use YEARONE to set the earliest year
# Example:
# qsub -v VAR=FPAR,OUTDIR_SUFFIX=test,YEARONE=2000 encode_SNU_Version_1.pbs.sh 

module load anaconda3/personal

source activate python3.10

python --version

echo -e "In PBS.SH and running:\n VAR: $VAR\n  OUTDIR_SUFFIX: $OUTDIR_SUFFIX\n  ARR_IND:  $PBS_ARRAY_INDEX\n  YEARONE: ${YEARONE:-Not set}"

python /rds/general/project/lemontree/live/source/SNU_005_Version_1/encode_SNU_Version_1.py

conda deactivate
