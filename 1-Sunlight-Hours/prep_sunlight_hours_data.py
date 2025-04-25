import cdsapi
import os
import zipfile
import xarray as xr
from glob import glob
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# Download dataset
dataset = "sis-energy-pecd"
request = {
    "pecd_version": "pecd4_1",
    "temporal_period": ["historical"],
    "origin": ["era5_reanalysis"],
    "variable": ["solar_generation_capacity_factor"],
    "spatial_resolution": ["0_25_degree"],
    "year": ["2020", "2021"],
    "month": ["01", "04", "07", "10"],
    "area": [55.5, -10.5, 51, -5.5]
}

client = cdsapi.Client()
client.retrieve(dataset, request, '1-Sunlight-Hours//ireland_solar.zip')

# Unzip the file
with zipfile.ZipFile("1-Sunlight-Hours//ireland_solar.zip", 'r') as zip_ref:
    zip_ref.extractall("1-Sunlight-Hours//ireland_solar")

folder = "1-Sunlight-Hours//ireland_solar"

# Find all .nc files in the folder with full paths
nc_files = sorted(glob(os.path.join(folder, "*.nc")))

print(f"Found {len(nc_files)} NetCDF files.")

# Loop through each .nc file
datasets = []
for f in nc_files:
    ds = xr.open_dataset(f)
    
    # Extract variables assuming 'spv_cf' is solar capacity factor
    df = ds[['spv_cf', 'latitude', 'longitude', 'time']].to_dataframe().reset_index()
    datasets.append(df)

# Concatenate all DataFrames together
final_df = pd.concat(datasets, ignore_index=True)

# Ensure 'time' is datetime
final_df['time'] = pd.to_datetime(final_df['time'])

# Extract Year and Month
final_df['year'] = final_df['time'].dt.year
final_df['month'] = final_df['time'].dt.month

# Round coordinates for consistency
final_df['latitude'] = final_df['latitude'].round(4)
final_df['longitude'] = final_df['longitude'].round(4)

# Group by Month, Lat, Lon and compute mean solar capacity factor
monthly_avg_df = final_df.groupby(['month', 'latitude', 'longitude'], as_index=False)['spv_cf'].mean()

print(monthly_avg_df.head())
print(monthly_avg_df.shape)

# Load countries from Natural Earth
world = gpd.read_file("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_admin_0_countries.geojson")
ireland = world[world['ADMIN'] == 'Ireland']

# Plotting heatmaps per month (optional visualization)
for month in monthly_avg_df['month'].unique():
    month_data = monthly_avg_df[monthly_avg_df['month'] == month]

    lats = sorted(month_data['latitude'].unique())
    lons = sorted(month_data['longitude'].unique())

    grid = month_data.pivot(index='latitude', columns='longitude', values='spv_cf').sort_index(ascending=False)
    X, Y = np.meshgrid(grid.columns, grid.index)

    fig, ax = plt.subplots(figsize=(10, 8))
    pcm = ax.pcolormesh(X, Y, grid.values, cmap='viridis', shading='auto')
    ireland.boundary.plot(ax=ax, edgecolor='black', linewidth=1)
    plt.colorbar(pcm, ax=ax, label='Solar Capacity Factor')
    ax.set_title(f'Solar Capacity Factor – Month {month}')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_xlim([-10.5, -5.5])
    ax.set_ylim([51, 55.5])
    plt.tight_layout()
    plt.show()

# Define target CRS
target_crs = "EPSG:2157"

# Prepare output folder
output_folder = "1-Sunlight-Hours/rasters_by_month"
os.makedirs(output_folder, exist_ok=True)

# Set desired output pixel size in meters (adjust for finer/coarser resolution)
desired_resolution = 1000  # 1000 meters = 1 km pixels; try smaller like 500 or 250 for finer pixels


for month in monthly_avg_df['month'].unique():
    month_data = monthly_avg_df[monthly_avg_df['month'] == month]

    grid = month_data.pivot(index='latitude', columns='longitude', values='spv_cf').sort_index(ascending=False)
    data_array = grid.values.astype('float32')

    lat_resolution = abs(grid.index[1] - grid.index[0])
    lon_resolution = abs(grid.columns[1] - grid.columns[0])

    west = grid.columns.min()
    east = grid.columns.max() + lon_resolution
    south = grid.index.min()
    north = grid.index.max() + lat_resolution

    src_transform = rasterio.transform.from_origin(
        west=west,
        north=north,
        xsize=lon_resolution,
        ysize=lat_resolution
    )

    # Source CRS check
    if (grid.index.min() >= -90 and grid.index.max() <= 90) and (grid.columns.min() >= -180 and grid.columns.max() <= 180):
        src_crs = 'EPSG:4326'
    else:
        raise ValueError("Source coordinates out of latitude/longitude bounds; unknown CRS.")

    src_height, src_width = data_array.shape

    dst_transform, dst_width, dst_height = calculate_default_transform(
        src_crs, target_crs,
        src_width, src_height,
        west, south, east, north,
        resolution=desired_resolution
    )

    reprojected = np.empty((dst_height, dst_width), dtype='float32')

    reproject(
        source=data_array,
        destination=reprojected,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=target_crs,
        resampling=Resampling.bilinear
    )

    filename = os.path.join(output_folder, f"solar_cf_month_{month}.tif")
    with rasterio.open(
        filename,
        'w',
        driver='GTiff',
        height=dst_height,
        width=dst_width,
        count=1,
        dtype='float32',
        crs=target_crs,
        transform=dst_transform,
        nodata=np.nan
    ) as dst:
        dst.write(reprojected, 1)
        dst.set_band_description(1, f"Solar Capacity Factor - Month {month}")

    print(f"✅ Saved reprojected raster: {filename}")


