
import geopandas as gpd
import matplotlib.pyplot as plt

# Load the original polyline shapefile
shapefile_path = '1-EirGrid-Map/Shp_File/transmission_map_lines.shp'
gdf = gpd.read_file(shapefile_path)

# Ensure it's in EPSG:2157 (meters)
if gdf.crs.to_epsg() != 2157:
    gdf = gdf.to_crs(epsg=2157)

# Create a 3km (3000 meter) buffer
buffered_geom = gdf.geometry.buffer(3000)

# Create a new GeoDataFrame with the buffered polygons
buffered_gdf = gpd.GeoDataFrame(gdf.copy(), geometry=buffered_geom)
buffered_gdf.set_crs(epsg=2157, inplace=True)

# Save the buffered layer
output_path = '1a-transmission_lines_buffered/Shp_File/buffered_3km_epsg2157.shp'
buffered_gdf.to_file(output_path)

print(f"Buffered shapefile saved to: {output_path}")

# Re-import and check
reimported_gdf = gpd.read_file(output_path)
print(f"Reimported CRS: {reimported_gdf.crs}")
print(f"Number of features: {len(reimported_gdf)}")

# Plot to verify
fig, ax = plt.subplots(figsize=(10, 10))
reimported_gdf.plot(ax=ax, color='lightgreen', edgecolor='black')
plt.title('Reimported Buffered Polygons (3km Buffer, EPSG:2157)')
plt.show()