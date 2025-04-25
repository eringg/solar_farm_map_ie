import rasterio
import numpy as np
import matplotlib.pyplot as plt
from rasterio.enums import Resampling

# Load DEM
dem_path = "1-DEM//dem_irl_itm-1.tif"

with rasterio.open(dem_path) as src:
    print("CRS:", src.crs)  # Expected: EPSG:2157
    dem = src.read(1)
    transform = src.transform
    profile = src.profile

# Calculate gradients in x and y directions
x, y = np.gradient(dem, transform.a, transform.e)

# Slope in degrees
slope = np.degrees(np.arctan(np.sqrt(x**2 + y**2)))

# Aspect in degrees: 0=N, 90=E, 180=S, 270=W
aspect = np.degrees(np.arctan2(-x, y))
aspect = np.mod(aspect + 360, 360)  # Normalize between 0-360

# Optional: Visualize the original DEM
plt.figure(figsize=(10, 6))
masked_dem = np.where(dem <= 0, np.nan, dem)  # Mask sea-level or below if needed
plt.imshow(masked_dem, cmap="terrain")
plt.colorbar(label="Elevation (m)")
plt.title("Original DEM")
plt.show()

# Create masks
south_facing = (aspect >= 135) & (aspect <= 225)
flat_land = slope < 5
non_sea_level = dem > 0

# Combine masks
desired_mask = (flat_land | south_facing) & non_sea_level

# Create binary output: 1 = yes, 0 = no
binary_filtered = np.where(desired_mask, 1, 0).astype(np.uint8)


# Visualize the binary mask
plt.figure(figsize=(10, 6))
plt.imshow(binary_filtered, cmap="gray")
plt.colorbar(label="1 = Yes, 0 = No")
plt.title("South-facing Slopes or Flat Land (Binary)")
plt.show()

# Define output path
output_path = "1-DEM//binary_filtered_dem.tif"

# Update profile for binary output
profile.update(
    dtype=rasterio.uint8,
    nodata=None,
)

# Write the binary raster
with rasterio.open(output_path, 'w', **profile) as dst:
    print("CRS:", src.crs)  # Expected: EPSG:2157
    dst.write(binary_filtered, 1)

print(f"Binary Filtered DEM saved to {output_path}")





####Checks to ensure the binary raster is saved out correctly
# Reimport the saved binary raster
reimport_path = "1-DEM//binary_filtered_dem.tif"

with rasterio.open(reimport_path) as reimp_src:
    reimp_data = reimp_src.read(1)
    reimp_transform = reimp_src.transform
    reimp_crs = reimp_src.crs

# Print CRS and unique values for sanity check
print("Reimported Raster CRS:", reimp_crs)


# Get unique values and counts
# Get unique values and counts
unique_vals, counts = np.unique(reimp_data, return_counts=True)
for val, count in zip(unique_vals, counts):
    if val == 1:
        label = "Suitable (1)"
    elif val == 0:
        label = "Unsuitable (0)"
    else:
        label = "Unknown"
    print(f"Value {val} - {label}: {count:,} pixels")


# Visualize reimported binary raster
plt.figure(figsize=(10, 6))
plt.imshow(reimp_data, cmap="gray_r", vmin=0, vmax=1)
plt.colorbar(label="1 = Suitable, 0 = Unsuitable")
plt.title("Reimported Binary Filtered DEM (Black = Suitable)")
plt.show()

