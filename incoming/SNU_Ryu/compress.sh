#!/bin/bash
  
# Compress the source matrix files into a targz

# Use the throughput class - single node, single cpu

#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/incoming/SNU_Ryu/compress.out


tar -zcf /rds/general/project/lemontree/live/incoming/SNU_Ryu/SNU_Ryu_original_files.tgz /rds/general/project/lemontree/live/incoming/SNU_Ryu/source_format/

