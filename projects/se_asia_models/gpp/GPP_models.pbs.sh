
#!/bin/bash

# Run the SE Asia GPP models

# NOTES:
#
# * Use the throughput class - single node, single cpu, using GPFS for better file
#   handling

# The lines below are the PBS directives. They specify the resources required for the
# job. 

#PBS -lselect=1:ncpus=1:mem=128gb
#PBS -lwalltime=24:00:00
#PBS -j oe
#PBS -o /rds/general/project/lemontree/live/projects/se_asia_models/gpp/GPP_models.out

# Activate the conda environment
eval "$(~/miniforge3/bin/conda shell.bash hook)"
conda activate pyrealm_py312

# Echo the python version and start time
python --version
echo -e "In PBS.SH and running"
date

# Run the GPP script
python /rds/general/project/lemontree/live/projects/se_asia_models/gpp/GPP_models.py

# Echo the end time and deactivate the conda environment
date
conda deactivate

