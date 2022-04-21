#!/bin/bash
  
# Compress the source matrix files from the storage tgz

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/compress.out

tar -zcf /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/SNU_Ryu_original_files.tgz -C /rds/general/project/lemontree/live/source/SNU_Ryu_FPAR_LAI/ source_format

