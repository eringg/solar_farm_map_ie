import geopandas as gpd
import rasterio
from rasterio.plot import show
from rasterio.mask import mask
import matplotlib.pyplot as plt
import os
from matplotlib.colors import LinearSegmentedColormap

# Load clipped suitability polygons
input_path = "3-keep_suitable_land_near_transmission/Shp_File/clipped_suitability.shp"
polygon_gdf = gpd.read_file(input_path)
print(f"Polygon CRS: {polygon_gdf.crs}")  # Should be EPSG:2157

# List of raster files to process
raster_files = [
    '1-Sunlight-Hours/rasters_by_month/solar_cf_month_1.tif',
    '1-Sunlight-Hours/rasters_by_month/solar_cf_month_4.tif',
    '1-Sunlight-Hours/rasters_by_month/solar_cf_month_7.tif',
    '1-Sunlight-Hours/rasters_by_month/solar_cf_month_10.tif',
]

month_names = {
    1: "January",
    4: "April",
    7: "July",
    10: "October"
}

reds = ['#a50026', '#f46d43', '#fdae61', '#fee08b', '#ffffbf']
cmap_red_orange_yellow = LinearSegmentedColormap.from_list('red_orange_yellow', reds)

output_dir = "4-sunshine_levels_on_suitable_land/masked_rasters"
os.makedirs(output_dir, exist_ok=True)

# Step 1: Clip and save all rasters
for raster_path in raster_files:
    print(f"📦 Processing raster: {raster_path}")
    
    basename = os.path.basename(raster_path)
    month_num = int(basename.split('_')[3].split('.')[0])
    month_name = month_names.get(month_num, f"Month {month_num}")
    
    with rasterio.open(raster_path) as src:
        if polygon_gdf.crs != src.crs:
            polygon_proj = polygon_gdf.to_crs(src.crs)
        else:
            polygon_proj = polygon_gdf
        
        geoms = [feature["geometry"] for feature in polygon_proj.__geo_interface__["features"]]
        out_image, out_transform = mask(src, geoms, crop=True)
        
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        
        out_raster_path = os.path.join(output_dir, f"clipped_{basename}")
        with rasterio.open(out_raster_path, "w", **out_meta) as dest:
            dest.write(out_image)
        print(f"✅ Saved clipped raster to {out_raster_path}")

# Step 2: Re-import and plot the clipped rasters
clipped_raster_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.tif')]

for clipped_raster_path in clipped_raster_files:
    basename = os.path.basename(clipped_raster_path)
    month_num = int(basename.split('_')[4].split('.')[0])
    month_name = month_names.get(month_num, f"Month {month_num}")
    
    with rasterio.open(clipped_raster_path) as clipped_src:
        fig, ax = plt.subplots(figsize=(10, 10))
        show(clipped_src.read(1), transform=clipped_src.transform, ax=ax, cmap=cmap_red_orange_yellow,
             title=f'Clipped Solar Capacity Factor – {month_name}')
        ax.set_xlabel("Easting (m)")
        ax.set_ylabel("Northing (m)")
        ax.grid(True)
        plt.tight_layout()
        plt.show()

