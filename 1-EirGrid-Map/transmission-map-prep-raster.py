# --- Step 1: Import Required Libraries ---
import rasterio
from rasterio.plot import reshape_as_image, reshape_as_raster
from rasterio.transform import xy
from shapely.geometry import LineString
import cv2
import numpy as np
import matplotlib.pyplot as plt
import pytesseract
from pytesseract import Output
import pandas as pd
import geopandas as gpd

# --- Step 2: Helper Functions ---
def plot_image(image, title, figsize=(10, 8)):
    plt.figure(figsize=figsize)
    plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    plt.title(title)
    plt.axis("off")
    plt.show()

def plot_geometries(gdf, title="Geometries"):
    gdf.plot(figsize=(10, 8), edgecolor='black')
    plt.title(title)
    plt.axis("equal")
    plt.show()

def create_exclusion_mask(image, manual_excludes):
    exclude_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for (x1, y1), (x2, y2) in manual_excludes:
        cv2.rectangle(exclude_mask, (x1, y1), (x2, y2), 255, -1)
    return exclude_mask

def apply_exclusion_mask(image, exclude_mask):
    image_with_exclusions = image.copy()
    image_with_exclusions[exclude_mask == 255] = (255, 255, 255)
    return image_with_exclusions

def extract_color_regions(image, hsv_image, color_ranges):
    combined_result = np.full_like(image, 255)
    for color, ranges in color_ranges.items():
        mask_total = None
        for lower, upper in ranges:
            mask = cv2.inRange(hsv_image, lower, upper)
            mask_total = mask if mask_total is None else cv2.bitwise_or(mask_total, mask)
        result = np.where(mask_total[:, :, np.newaxis] == 255, image, combined_result)
        combined_result = result
    return combined_result

def remove_text(image, df_filtered):
    text_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    for i in df_filtered.index:
        x, y, w, h = df_filtered.loc[i, 'left'], df_filtered.loc[i, 'top'], df_filtered.loc[i, 'width'], df_filtered.loc[i, 'height']
        cv2.rectangle(text_mask, (x, y), (x + w, y + h), 255, -1)
    image_without_text = image.copy()
    image_without_text[text_mask == 255] = (255, 255, 255)
    return image_without_text

# --- Step 3: Load Raster Image ---
raster_path = "1-EirGrid-Map/EirGridMap-raster/EirGridMap.tif"
with rasterio.open(raster_path) as src:
    raster_meta = src.meta.copy()
    crs = src.crs
    transform = src.transform
    bounds = src.bounds
    img_array = src.read()
    img = reshape_as_image(img_array)

plot_image(img, "Original Image")

# --- Step 4: Manual Exclusions ---
manual_excludes = [
    ((3, 1),        (2813, 926)),   #Map Title
    ((110, 1040),   (1260, 3050)),  #Legend
    ((5190, 4),     (5800, 640)),   #Compass
    ((3230, 5600),  (5830, 8250)),  #Dublin Zoom
    ((3, 6540),     (3290, 8250)),  #Cork & Belfast Zoom
    ((3,1),         (100, 8250)),   #Left Border
    ((5710, 10),    (5840, 8250)),  #Right Border
    ((3, 1),        (5840, 120)),   #Top Border
    ((4389, 3131),  (5294, 3639)),  #Dublin Box
    ((2692, 5325),  (3102, 5790)),  #Cork Box
    ((4645, 1068),  (5251, 1719)),  #Belfast Box   
]

# Apply Manual Exclusions
exclude_mask = create_exclusion_mask(img, manual_excludes)
img_with_exclusions = apply_exclusion_mask(img, exclude_mask)

# --- Plot: Image with Manual Exclusions Applied ---
plot_image(img_with_exclusions, "Map with Manual Exclusions")

# Convert Image to HSV
hsv = cv2.cvtColor(img_with_exclusions, cv2.COLOR_BGR2HSV)

# Define Color Ranges for Extraction
color_ranges = {
    "selected_colors": [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),    # red (lower)
        (np.array([160, 100, 100]), np.array([180, 255, 255])), # red (upper)
        (np.array([10, 100, 100]), np.array([25, 255, 255])),   # orange
        (np.array([100, 150, 50]), np.array([140, 255, 255])),  # blue
        (np.array([40, 50, 50]), np.array([90, 255, 255])),     # green-yellow
        (np.array([0, 0, 0]), np.array([180, 255, 50]))          # black/gray
    ]
}

# Extract Color Regions
detected_img = extract_color_regions(img_with_exclusions, hsv, color_ranges)

# --- Plot: Detected Color Regions ---
plot_image(detected_img, "Detected Colors")

# Create a copy of the detected image
non_white_to_black = detected_img.copy()

# Define the RGB threshold for "white" (tweak if needed)
threshold = 240

# Create a new image where non-white pixels become black
bw_mask = np.where(np.all(non_white_to_black >= threshold, axis=-1, keepdims=True),
                   [255, 255, 255],
                   [0, 0, 0]).astype(np.uint8)

# --- Plot: Image with Non-White Pixels Converted to Black ---
plot_image(bw_mask, "Black/White Mask")

# --- Step 7: Text Removal ---
rgb = cv2.cvtColor(bw_mask, cv2.COLOR_BGR2RGB)
custom_config = r'--psm 6'  # Assume a single uniform block of text
data = pytesseract.image_to_data(rgb, output_type=Output.DICT, config=custom_config)
df = pd.DataFrame(data)
df['text'] = df['text'].str.strip()
df_filtered = df[(df['text'] != '') & (df['conf'] > 1) & (df['text'].str.len() > 2)] # Filter out empty text and low confidence

# Remove Text from Image
first_text_removal = remove_text(bw_mask, df_filtered)

# --- Plot: Final Image (Text Removed) ---
plot_image(first_text_removal, "First Round of Text Removed")



# Extract Text Data from Image (for removal)
rgb2 = cv2.cvtColor(first_text_removal, cv2.COLOR_BGR2RGB)
custom_config = r'--psm 6'  # Assume a single uniform block of text
data2 = pytesseract.image_to_data(rgb2, output_type=Output.DICT, config=custom_config)
df2 = pd.DataFrame(data2)
df2['text'] = df2['text'].str.strip()
df_filtered2 = df2[(df2['text'] != '') & (df2['conf'] > 1) & (df2['text'].str.len() > 2)]

# Remove Text from Image
text_removed_2 = remove_text(first_text_removal, df_filtered2)

# --- Plot: Final Image (Text Removed) ---
plot_image(text_removed_2, "Text Removed")


# --- Step 7b Manual Exclusions ---
manual_text_excludes = [
    ((2075, 4678),  (2224, 4732)),   #Dromada
    ((1740, 4606),  (1860, 4648)),   #Drombeg
    ((1837, 4703),  (1909, 4730)),   #Trien
    ((1896, 4848),  (2079, 4876)),   #Cloghboola
    ((2692, 4340),  (2767, 4371)),   #Ahane
    ((3070, 3537),  (3195, 3578)),   #Cloniffe
    ((2476, 3176),  (2550, 3202)),   #Cloon
    ((4651, 4519),  (4950, 4590)),   #Ballywater
    ((4094, 3877),  (4163, 3922)),   #Athy
    ((4012, 4852),  (4148, 4884)),   #Loughtown
    ((3945, 4393),  (4069, 4423)),   #Kilkenny
    ((4269, 4176),  (4360, 4208)),   #Kellis
    ((4241, 2438),  (4378, 2469)),   #Drumcamil
    ((4392, 2849),  (4477, 2871)),   #Gorman
    ((4604, 2804),  (4736, 2840)),   #Drybridge
    ((4789, 3055),  (4948, 3122)),   #East-West
    ((3339, 2799),  (3454, 2828)),   #Richmond
    ((3207, 1452),  (3365, 1489)),   #Mulreavy
    ((3797, 1054),  (3930, 1134)),   #Slieve Kirk
    ((4465, 1744),  (4624, 1774)),   #Waringstown
    ((2228, 5749),  (2355, 5775)),   #Dummanway
    ((5212,  831),  (5583, 1038)),   #Interconnector 500MW
    ((1851, 2183),  (2056, 2238)),   #Scahnakilly
    ((3526, 5189),  (3669, 5228)),   #Dungarvan
    ((4333, 5249),  (4552, 5587)),   #Greenlink Interconnector
]

# Apply Manual Exclusions
text_exclude_mask = create_exclusion_mask(text_removed_2, manual_text_excludes)
text_removed_3 = apply_exclusion_mask(text_removed_2, text_exclude_mask)


# --- Plot: Image with Manual Exclusions Applied ---
plot_image(text_removed_3, "Final Text Exclusions")



# --- Step 8: Contour Detection ---
gray = cv2.cvtColor(text_removed_3, cv2.COLOR_BGR2GRAY)
_, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

# DEBUG: Plot the binary image after thresholding
plot_image(cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR), "Binary Image for Contour Detection")


contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

print(f"Found {len(contours)} contours")


# Create a blank white canvas same size as input
polyline_image = np.full_like(text_removed_3 , 255)

# Draw polylines (contours)
cv2.drawContours(polyline_image, contours, -1, (0, 0, 255), 2)  # color=black, thickness=1

plot_image(polyline_image, "Detected Polylines")


def pixel_to_coords(transform, row, col):
    x, y = rasterio.transform.xy(transform, row, col)
    return (x, y)

geometry_list = []
for contour in contours:
    coords = contour.squeeze()
    if coords.ndim != 2 or coords.shape[0] < 2:
        continue
    try:
        spatial_coords = [pixel_to_coords(transform, int(pt[1]), int(pt[0])) for pt in coords]
        line = LineString(spatial_coords)
        if line.is_valid:
            geometry_list.append(line)
    except Exception as e:
        print(f"Error creating line: {e}")


output_shapefile = "1-EirGrid-Map/Shp_File/transmission_map_lines.shp"

# Create GeoDataFrame

if geometry_list:
    gdf = gpd.GeoDataFrame(geometry=geometry_list, crs=crs)
    gdf.to_file(output_shapefile)
    print(f"Shapefile with polylines saved to: {output_shapefile}")
    plot_geometries(gdf, title="Extracted Line Geometries")
else:
    print("No valid polylines were generated.")


