import geopandas as gpd
import matplotlib.pyplot as plt

# Load your shapefiles
buffered_transmission = gpd.read_file('1a-transmission_lines_buffered/Shp_File/buffered_3km_epsg2157.shp')
suitability_land = gpd.read_file('2-combine_land_cover_dem/Shp_File/solar_ready_land.shp')

# Ensure both GeoDataFrames use the same CRS
suitability_land = suitability_land.to_crs(buffered_transmission.crs)

# Clip suitability land using buffered transmission polygons (intersection)
clipped_suitability = gpd.overlay(suitability_land, buffered_transmission, how='intersection')

# Save clipped result
output_path =  '3-keep_suitable_land_near_transmission/Shp_File/clipped_suitability.shp'

clipped_suitability.to_file(output_path)

print("Clipping complete and saved to:", output_path)

# Re-import the clipped shapefile
clipped = gpd.read_file(output_path)

# Plot the clipped suitability polygons
fig, ax = plt.subplots(figsize=(10, 10))
clipped.plot(ax=ax, color='green', edgecolor='black', alpha=0.6)
ax.set_title('Clipped Suitability Land')
plt.show()