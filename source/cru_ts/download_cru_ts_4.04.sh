# This bash script contains the shell commands needed to run the CRU TS 4.04 download
# python script on the Imperial HPC system.

module load anaconda3/personal

# Activate a conda environment, which needs packages crypotography and ContrailOnlineCAClient:
# conda install cryptography
# conda install  ContrailOnlineCAClient>=0.5.1

source activate base

python download_cru_ts_4.04.py

conda deactivate