# This bash script contains the shell commands needed to run the CRU TS 4.07 download
# python script on the Imperial HPC system.

module load anaconda3/personal

# Activate a python environment - needs standard library only and Python 3.9+
source activate python3.10

# Load CEDA credentials from user home directory - these must be stored as a 
# single line with space:
# username password
creds=$(<$HOME/CEDA_FTP_CREDENTIALS.txt)

project_dir=/rds/general/project/lemontree/live/

# Make the output directory
outdir=$project_dir/source/cru_ts/cru_ts_4.07b
mkdir -p $outdir

# Run the FTP script
python $project_dir/tools/ceda_ftp_tool.py badc/cru/data/cru_ts/cru_ts_4.07 $outdir $creds -e station_counts -e 1901.2022 -e dat.gz

conda deactivate
