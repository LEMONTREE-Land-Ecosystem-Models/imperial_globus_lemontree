#!/bin/bash

# This script repakages the incoming data from individual day files in landonly
# vectors to netcdf files containing a year of data in an unpacked grid

# Use the throughput class - single node, single cpu

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -J 1-20
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/conversion_^job_id^_^array_index^.out

# Submit using qsub -v SCRIPT_VAR=FPAR or qsub -v SCRIPT_VAR=LAI and 
# * Use SCRIPT_OUTDIR_SUFFIX to set the suffix on the output dir,
#   e.g. SCRIPT_OUTDIR_SUFFIX=in_here -> FPAR_in_here
# * Use SCRIPT_PACK=1 to pack outputs into uint16

module load anaconda3/personal

source activate base

echo "In PBS.SH and running:\n VAR: $SCRIPT_VAR\n OUT_DIR_SUFFIX: $SCRIPT_OUTDIR_SUFFIX$\n ARR_IND: $PBS_ARRAY_INDEX\n ${SCRIPT_PACK:-Not set}"

python /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/convert_SNU_Ryu_to_netcdf.py

conda deactivate
