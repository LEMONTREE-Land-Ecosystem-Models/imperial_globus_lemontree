#!/bin/bash

# This script repakages the incoming data from individual day files in landonly
# vectors to netcdf files containing a year of data in an unpacked grid

# Use the throughput class - single node, single cpu

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -J 1-21
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/conversion_^array_index^.out

# Env vars needed:
#
# * Use VAR=FPAR or VAR=LAI to set the variable 
# * Use OUTDIR_SUFFIX to set the suffix on the output dir,
#        e.g. OUTDIR_SUFFIX=in_here -> FPAR_in_here
# * Optionally use PACK=1 to pack outputs into uint16
#
# Example:
# qsub -v VAR=FPAR,OUTDIR_SUFFIX=test,PACK=1 convert_SNU_Ryu_to_netcdf.pbs.sh 

module load anaconda3/personal

source activate base

echo -e "In PBS.SH and running:\n VAR: $VAR\n  OUTDIR_SUFFIX: $OUTDIR_SUFFIX\n  ARR_IND:  $PBS_ARRAY_INDEX\n  PACK: ${PACK:-Not set}"

python /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/convert_SNU_Ryu_to_netcdf.py

conda deactivate
