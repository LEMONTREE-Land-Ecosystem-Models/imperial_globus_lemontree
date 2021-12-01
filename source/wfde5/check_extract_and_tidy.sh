#!/bin/bash

# Checks the right number of files has been extracted and - if so - deletes
# the downloaded zip files, which are duplicated data. First, extracts Elev

cd /rds/general/project/lemontree/live/source/wfde5/wfde5_v2/Elev
unzip WFDE5_v2.0_Elev.zip

cd ../

# How many NC files
n_extract=$(find . -name *.nc | wc -l)
n_expected=$(expr 12 \* 41 \* 8 + 1) # 12 months, 41 years, 8 vars + Elev


if test $n_extract -eq $n_expected; 
then
    echo "SUCCESS - deleting downloaded zips"
    find . -name *.zip -type f -exec rm -f {} \;
else
    echo "FAILURE"
fi
