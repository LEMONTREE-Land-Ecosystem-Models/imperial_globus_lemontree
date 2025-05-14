#! /bin/bash

#PBS -l walltime=24:00:00
#PBS -l select=1:ncpus=1:mem=40gb
#PBS -J 1-40
#PBS -j oe


module load tools/dev
module load CDO/2.0.5-gompi-2021b

fapar_path=/rds/general/project/lemontree/live/source/SNU_005_Version_1/FPAR_daily_by_month
out_dir=/rds/general/project/lemontree/live/derived/SNU_Ryu/FPAR3_05d

# Grid files for the inputs and downsample - this preserves lat and long wrapping,
# where r720x360 wraps longitude into 0-360 with 0°E at leftmost edge
grid_0_05=/rds/general/project/lemontree/live/derived/SNU_Ryu/grid_0_05.txt
grid_0_5=/rds/general/project/lemontree/live/derived/SNU_Ryu/grid_0_5.txt

# Files cover 1982 - 2021
year=$((1981+$PBS_ARRAY_INDEX))

for file in ${fapar_path}/FPAR_${year}*;
do 
    echo $file
    outfile=`basename $file`
    cdo setgrid,$grid_0_05 $file temp_input.setgrid.nc
    cdo remapcon,$grid_0_5 temp_input.setgrid.nc ${out_dir}/${outfile}
done

