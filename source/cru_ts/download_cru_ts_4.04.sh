# This bash script contains the shell commands needed to run the CRU TS 4.04 download
# python script on the Imperial HPC system.

module load anaconda3/personal

# Activate a conda environment, which needs simplejson and ContrailOnlineCAClient:
# pip install ContrailOnlineCAClient

source activate base

python download_cru_ts_4.04.py

conda deactivate