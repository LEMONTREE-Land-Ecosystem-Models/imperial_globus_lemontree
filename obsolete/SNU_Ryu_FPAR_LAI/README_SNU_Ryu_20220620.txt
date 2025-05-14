1. MODIS LAI:  2000-2017, daily
MODIS fPAR: 2000-2019, daily

a) Both data were interpolated to daily step from their original 8-day step.
First, simple linear interpolation was used to smooth the 8-day time series LAI.
Then, the monthly average was used to fill the data gap, 
Finally, Gaussian interpolation was used to generate daily data.

b) We saved the 0.05 degree data as one-dimension data to reduce its size. The land cover map can
help to convert them to two-dimension global map (3660 pixel * 7200 pixel). 

c) No scaling factor.

d) These data were further converted to NetCDF format (one NC file one year)
in folders: /live/source/SNU_Ryu_FPAR_LAI/LAI_netcdf/ and /live/source/SNU_Ryu_FPAR_LAI/FPAR_netcdf/

e) Below is the matlab script for generating gridded 0.05 degree map with geographic lat/lon projection

raw = importdata('XXXX\FPAR_Daily^.2000.032.mat');
msk005d = importdata('XXXX\Landmask.005d.mat');
DATA = nan(size(msk005d),'single');
% convert one-dimension to two-dimension by use of landcover map
DATA(msk005d) = raw;

%output  0.05 degree data
strname=['XXXX\output.tif'];
R = georasterref('RasterSize',size(DATA),'LatitudeLimits',[-90 90],'LongitudeLimits',[-180 180]);
geotiffwrite(strname,flipud(DATA),R);


2. MODIS LAI:  2018-2019, daily

Same processing method as MODIS LAI from 2000-2017 but directly saved in NetCDF.
Please use scaling factor 0.0001 to obtain the true LAI values.


If you have any questions, please contact us.

Dr. Youngryel Ryu     ryuyr77@gmail.com
Dr. Xing Li           xing.li.rs@gmail.com
