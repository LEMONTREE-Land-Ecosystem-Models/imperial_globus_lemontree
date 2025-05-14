README
1. Product name: Gap-filled BRDF-corrected NIRv (calculated from MCD43C4), SNU Version 1, produced in August 2022;
2. Time period: 2000.1 to 2021.12; temporal resolution: daily and monthly; spatial resolution: 0.05deg; NIRv=NDVI*NIR; size: 3600*7200; filled value for ocean pixels: -1;
3. Gaussian filter was applied to fill the gaps in daily NIRv using a rolling time window (21 day); if there were still gaps, then monthly average was further used to fill the gaps;
4. The original qc for MCD43C4 was also include in the NetCDF files.

Contact: Dr. Xing Li: xing.li.rs@gmail.com
Dr. Youngryel Ryu: ryuyr77@gmail.com 
