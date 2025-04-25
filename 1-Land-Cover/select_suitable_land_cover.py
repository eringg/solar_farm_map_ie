import geopandas as gpd
import matplotlib.pyplot as plt
import textwrap

# Replace with your actual file path
shapefile_path = "1-Land-Cover//CLC18_IE//CLC18_IE.shp"
land_cover = gpd.read_file(shapefile_path)

land_cover.plot(
    figsize=(10, 10),
    column='Class_Desc',
    legend=True,
    legend_kwds={'loc': 'upper left', 'bbox_to_anchor': (1.05, 1)}  # moves legend outside
)

plt.title("Land Cover Types")
plt.tight_layout()  # adjusts layout to avoid clipping
plt.show()

# Take a peek at the data
print(land_cover.head())
print(land_cover.crs)  # Check the coordinate reference system


land_cover['Class_Desc'].value_counts()

# Updated list of suitable land types (excludes mineral extraction sites)
suitable_types = [
    "Non-irrigated arable land",
    "Land principally occupied by agriculture, with significant areas of natural vegetation",
    "Natural grasslands",
    "Pastures",
    "Sparsely vegetated areas",
    "Bare rocks",
    "Dump sites"
]

# Filter the GeoDataFrame
suitable_land = land_cover[land_cover['Class_Desc'].isin(suitable_types)]



# Define your wrap width (adjust as needed)
wrap_width = 25

# Manually wrap the class descriptions
suitable_land = suitable_land.copy()
suitable_land['Wrapped_Class_Desc'] = suitable_land['Class_Desc'].apply(
    lambda x: '\n'.join(textwrap.wrap(x, wrap_width))
)

# Plot using the wrapped column
fig, ax = plt.subplots(figsize=(10, 10))

suitable_land.plot(
    ax=ax,
    column='Wrapped_Class_Desc',
    legend=True,
    legend_kwds={
        'loc': 'upper left',
        'bbox_to_anchor': (1.05, 1),
        'frameon': False
    }
)

ax.set_title("Suitable Land Types for Solar Farms")
ax.set_axis_off()
plt.tight_layout()
plt.show()


# Reproject suitable land to EPSG:2157 (Irish Transverse Mercator)
suitable_land_2157 = suitable_land.to_crs(epsg=2157)

# Save the reprojected data as a new shapefile
suitable_land_2157.to_file("1-Land-Cover//Shp_File/suitable_land.shp")