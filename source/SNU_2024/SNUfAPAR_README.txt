This is the README file for SNU fAPAR data shared by Sungchan Jeong (sungchanm0224@gmail.com) and is part of Breathing Earth System Simulator (BESS) dataset.

Files include:
(1) snu_fpar_v1-2: raw data contains two variables: 2d array of fAPAR (480[time]*8774037[land grid]) and 2d array of landmask (3600*7200). fAPAR is available from 1982-2021 on monthly timestep with 0.05 degree spatial resolution.
(2) monthly_005d: folder containing 3d raster files which are converted from raw data according to landmask, sliced to annual data. Temporal and spatial resolution are consistent with raw data.
(3) process_SNUfAPAR: script used to convert 2d raw data to 3d annual files.