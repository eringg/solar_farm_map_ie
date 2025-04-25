import geopandas as gpd
from rasterstats import zonal_stats
import matplotlib.pyplot as plt
import rasterio
import pandas as pd
import rasterio.plot
import numpy as np

# Load your filtered suitable land polygons
suitable_land = gpd.read_file("1-Land-Cover/Shp_File/suitable_land.shp")
print("Vector CRS:", suitable_land.crs)

# Path to your binary raster
terrain_mask_path = "1-DEM/binary_filtered_dem.tif"
# Load raster file
with rasterio.open("1-DEM/binary_filtered_dem.tif") as src:
    data = src.read(1)
    print("Unique raster values:", np.unique(data))
    print("Raster CRS:", src.crs)

# Compute mean (i.e., % of polygon area with value = 1)
terrain_stats = zonal_stats(
    suitable_land,
    terrain_mask_path,
    stats=["mean"],
    nodata=None,  # ← Do not ignore 0s!
    geojson_out=False
)

#Analyse the summary statistics
print(terrain_stats[:3])  # See first 3 entries

# Check for None values
terrain_df = pd.DataFrame(terrain_stats)
print(terrain_df.describe())

# Check for polygons that meet the criteria, i.e., mean >= 0.90
high_score_count = sum(1 for stat in terrain_stats if stat["mean"] is not None and stat["mean"] >= 0.95)
print(f"Polygons with ≥95% suitable terrain: {high_score_count}")

# Check for polygons with mean that is neither 0 or 1
non_extreme_count = sum(1 for stat in terrain_stats if stat["mean"] is not None and 0 < stat["mean"] < 1)
print(f"Polygons with mean neither 0 nor 1: {non_extreme_count}")

#
missing_or_zero = [i for i, stat in enumerate(terrain_stats) if stat["mean"] is None or stat["mean"] == 0]
print(f"Polygons with no suitable terrain or missing data: {len(missing_or_zero)}")


# Add terrain_score to the GeoDataFrame
suitable_land["terrain_score"] = [s["mean"] if s["mean"] is not None else 0 for s in terrain_stats]

# Filter polygons with ≥95% suitable terrain
solar_ready = suitable_land[suitable_land["terrain_score"] >= 0.95]

# Save result
solar_ready.to_file("2-combine_land_cover_dem/Shp_File/solar_ready_land.shp")

# Optional: Plot the result
solar_ready.plot(column="terrain_score", legend=True, figsize=(10, 10))
plt.title("Solar-Ready Land (≥95% Suitable Terrain)")
plt.show()
