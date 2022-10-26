#!/bin/bash

# This script renames the MCD43C4 data files - internally the original source files used
# a variable name with a space in it "MCD43C4 qc" and then is not the same as the
# variable name used in the compiled outputs "MCD43C4_2001_01.nc". This is basically a
# single use script to fix that.

# Use the throughput class - single node, single cpu, using GPFS for better file handling

#PBS -lselect=1:ncpus=8:mem=96gb:gpfs=true
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/ephemeral/qc_renamer.out


module load cdo

cd /rds/general/project/lemontree/ephemeral/SNU_data_sharing_Sep_2022/MCD43C4_raw

for each_file in *.nc;
do
    # rename the variable in the file and output to renamed file
    cdo chname,MCD43C4\ qc,MCD43C4_qc $each_file ${each_file//MCD43C4/MCD43C4_qc}

done;

