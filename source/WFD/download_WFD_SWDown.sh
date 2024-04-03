# This bash script contains the shell commands needed to run the CRU TS 4.07 download
# python script on the Imperial HPC system.

module load anaconda3/personal

# Activate a python environment - needs standard library only and Python 3.9+
source activate python3.10

# Load CEH credentials from user home directory - these must be stored as a 
# single line with space:
# username password
creds=$(<$HOME/CEH_CREDENTIALS.txt)

project_dir=/rds/general/project/lemontree/live/

# Make the output directory
outdir=$project_dir/source/WFD/SWDown
mkdir -p $outdir

# Run the download script
python $project_dir/tools/ceh_download_tool.py https://catalogue.ceh.ac.uk/datastore/eidchub/31dd5dd3-85b7-45f3-96a3-6e6023b0ad61/extracted/ $outdir $creds

conda deactivate
