#!/bin/bash

# This script runs the download of the ERA5 data on a compute node, not the login

# Use the throughput class - single node, single cpu
#PBS -lselect=1:ncpus=1:mem=96gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/ERA5_download.out

eval "$(~/miniforge3/bin/conda shell.bash hook)"

# Activate a conda environment python314_xarray, which needs:
# xarray[io] 
# zarr
# httpio
# fsspec
# ipython
# obstore

conda activate python314_xarray

python /rds/general/project/lemontree/live/projects/inter_compar_HB/GLOBAL/CDS_ARCO_download.py

conda deactivate # Out of python314_xarray
conda deactivate # Out of base
