import xarray as xr
import numpy as np
import pandas as pd
from pathlib import Path

# pathway
input_file = r"Z:\ephemeral\crujra.v2.5.5d.dlwrf.1980.365d.noc.nc\crujra.v2.5.5d.dlwrf.1980.365d.noc.nc"
output_file   = r"Z:\ephemeral\crujra.v2.5.5d.dlwrf.1980.365d.noc.nc\crujra.v2.5.5d.dlwrf.1980.365d.hr.noc.nc"
flat_file = r"Z:\ephemeral\crujra.v2.5.5d.dlwrf.1980.365d.noc.nc\crujra.v2.5.5d.dlwrf.1980.365d.hr_2d.noc.nc"

vars_to_interpolate = ["dlwrf"]  
interp_method = "linear"

print("Opening dataset CRU-JRA v2.5")
ds = xr.open_dataset(input_file, use_cftime=True)  
print("Resampling dlwrf to hourly timestep using linear interpolation")

ds_hourly = ds.resample(time="1H").interpolate("linear")
ds_hourly = ds_hourly[["dlwrf"]]
# ensure float32
ds_hourly["dlwrf"] = ds_hourly["dlwrf"].astype(np.float32)

# set up variable to save
ds_hourly.attrs.update(ds.attrs)
ds_hourly["dlwrf"].attrs.update(ds["dlwrf"].attrs)
ds_hourly.attrs["history"] = (
    ds.attrs.get("history", "") +
    " | Interpolated from 6-hourly to hourly using xarray.resample(...).interpolate('linear')."
)

encoding = {
    "dlwrf": {
        "dtype": "float32",
        "zlib": True,
        "complevel": 4  # compress level could range from 0-9
    }
}

print(f"Writing output to {output_file}")
Path(output_file).parent.mkdir(parents=True, exist_ok=True)
ds_hourly.to_netcdf(output_file, mode="w", format="NETCDF4", encoding=encoding)
print("Done.")

## set up land mask and removing sea
da = ds_hourly["dlwrf"]
# load into memory as xarray do not work well with dask...
da = da.load()          
ds_hourly = ds_hourly.load() # load coords

da_data = da.values     
is_missing = np.isnan(da_data)             
non_missing_any = (~is_missing).any(axis=0) 

landmask_bool = xr.DataArray(
    non_missing_any,
    dims=("lat", "lon"),
    coords={"lat": ds_hourly["lat"], "lon": ds_hourly["lon"]},
    name="landmask"
)

print("Total grid cells:", landmask_bool.size)
print("Land cells:", int(landmask_bool.sum()))
print("Sea cells:", int((~landmask_bool).sum()))

# Keep only land cells
da_land = da.where(landmask_bool)  
# flatten to 2d
da_stacked = da_land.stack(location=("lat", "lon")) 
# drop sea cells
da_flat = da_stacked.dropna(dim="location", how="all") 

print("Number of land locations kept:", da_flat.sizes["location"])

# key map and save compound data
da_flat = da_flat.reset_index("location")  # unlease lat-lon from multi index

lat_vals = da_flat["lat"].values   
lon_vals = da_flat["lon"].values

# full grid
lat_grid = ds_hourly["lat"].values  # (lat,)
lon_grid = ds_hourly["lon"].values  # (lon,)

# Integer indices on full grid
lat_index = np.searchsorted(lat_grid, lat_vals).astype(np.int32)
lon_index = np.searchsorted(lon_grid, lon_vals).astype(np.int32)

# set up flatten data and save
da_flat = da_flat.astype("float32")
ds_flat = xr.Dataset(
    data_vars={
        "dlwrf":     da_flat,                            
        "lat_index": (("location",), lat_index),
        "lon_index": (("location",), lon_index),
        "lat_full":  (("lat_full",), lat_grid.astype(np.float32)),
        "lon_full":  (("lon_full",), lon_grid.astype(np.float32)),
    },
    coords={
        "time":     da_flat["time"],     
        "location": da_flat["location"], 
        "lat_loc":  (("location",), lat_vals.astype(np.float32)),
        "lon_loc":  (("location",), lon_vals.astype(np.float32)),
    },
    attrs=ds_hourly.attrs
)

ds_flat["dlwrf"].attrs.update(ds_hourly["dlwrf"].attrs)
ds_flat["lat_full"].attrs["description"] = "Full latitude grid of original data"
ds_flat["lon_full"].attrs["description"] = "Full longitude grid of original data"
ds_flat["lat_index"].attrs["description"] = "Index into lat_full for each location"
ds_flat["lon_index"].attrs["description"] = "Index into lon_full for each location"
ds_flat["lat_loc"].attrs["description"]  = "Latitude of each land location"
ds_flat["lon_loc"].attrs["description"]  = "Longitude of each land location"

ds_flat.attrs["history"] = (
    ds_hourly.attrs.get("history", "") +
    " | Interpolated to hourly in-memory, derived land mask (non-NaN over time), "
    "removed sea cells, flattened to dlwrf(time, location) with index map and full grid."
)

encoding_flat = {
    "dlwrf": {
        "dtype": "float32",
        "zlib": True,
        "complevel": 4,
        "shuffle": True,
    },
    "lat_index": {"dtype": "int32",   "zlib": True, "complevel": 1, "shuffle": True},
    "lon_index": {"dtype": "int32",   "zlib": True, "complevel": 1, "shuffle": True},
    "lat_full":  {"dtype": "float32", "zlib": True, "complevel": 1, "shuffle": True},
    "lon_full":  {"dtype": "float32", "zlib": True, "complevel": 1, "shuffle": True},
    "lat_loc":   {"dtype": "float32", "zlib": True, "complevel": 1, "shuffle": True},
    "lon_loc":   {"dtype": "float32", "zlib": True, "complevel": 1, "shuffle": True},
}

Path(flat_file).parent.mkdir(parents=True, exist_ok=True)
ds_flat.to_netcdf(flat_file, format="NETCDF4", encoding=encoding_flat)

print("Wrote flattened hourly file:", flat_file)

# reconstruct 3d data
dlwrf_flat = ds_flat["dlwrf"]            # (time, location)
lat_index  = ds_flat["lat_index"].values
lon_index  = ds_flat["lon_index"].values
time       = ds_flat["time"]

lat_grid = ds_flat["lat_full"].values    
lon_grid = ds_flat["lon_full"].values    

n_time = dlwrf_flat.sizes["time"]
n_lat  = lat_grid.size
n_lon  = lon_grid.size

# fill 3d array
dlwrf_3d = np.full((n_time, n_lat, n_lon), np.nan, dtype=np.float32)

# Fill land points
for loc in range(dlwrf_flat.sizes["location"]):
    i_lat = lat_index[loc]
    i_lon = lon_index[loc]
    dlwrf_3d[:, i_lat, i_lon] = dlwrf_flat[:, loc].values

ds_recon = xr.Dataset(
    data_vars={"dlwrf": (("time", "lat_full", "lon_full"), dlwrf_3d)},
    coords={
        "time":     time,
        "lat_full": (("lat_full",), lat_grid),
        "lon_full": (("lon_full",), lon_grid),
    },
    attrs=ds_flat.attrs
)

ds_recon = ds_recon.rename({"lat_full": "lat", "lon_full": "lon"})
print(ds_recon)