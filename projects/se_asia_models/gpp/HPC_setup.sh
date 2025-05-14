#! /bin/bash

# This script sets up a new python environment for running the GPP models on the HPC.

# We will use conda to create a new environment with the required packages. If a user
# has not installed conda, they can do so by running the following command:
module load miniforge/3
miniforge-setup

# Once conda is installed, we can activate the conda commands and then create a new
# environment with the required packages.
eval "$(~/miniforge3/bin/conda shell.bash hook)"
conda create -n pyrealm_py312 python=3.12

# We need the following packages:
# The rasterio package is available in conda-forge, so we can install it using conda. 
# The pyrealm package is available on PyPI, so we can install it using pip.
conda install rasterio
pip install pyrealm==2.0.0-rc3
