import os

import numpy as np
import rasterio
from PIL import Image
from rasterio.io import MemoryFile
from rasterio.merge import merge
from rasterio.transform import from_bounds

# === CONFIG ===
TILE_DIR = r'C:\WJS\SCRIPTS\Python\Image Scraper\Output_tiles'
# ZOOM = 22  # must match your downloaded tile zoom
ZOOM_Level = [14, 15, 16, 17, 18, 19, 20, 21, 22]  # 20 is very detailed
file_Prefix = 'Torrent_Monuments'
# OUTPUT_DIRECTORY = rf"C:\Orange Imagery\Georefernced Imagery"
OUTPUT_DIRECTORY = rf"C:\WJS\SCRIPTS\Python\Image Scraper\Output_mosaic"

TILE_SIZE = 256
PROGRESS_INTERVAL = 100
# ==============

INITIAL_RES = 156543.03392804097  # meters/pixel at zoom 0
ORIGIN_SHIFT = 20037508.342789244  # half Earth width in Web Mercator


def tile_bounds(x, y, z):
    """Return Web Mercator (EPSG:3857) bounds for given tile index."""
    res = INITIAL_RES / (2 ** z)
    xmin = -ORIGIN_SHIFT + x * TILE_SIZE * res
    ymax = ORIGIN_SHIFT - y * TILE_SIZE * res
    xmax = xmin + TILE_SIZE * res
    ymin = ymax - TILE_SIZE * res
    return [xmin, ymin, xmax, ymax]


for ZOOM in ZOOM_Level:
    file_name = f'{file_Prefix}{ZOOM}'
    output_path = rf"{OUTPUT_DIRECTORY}\{file_name}.tif"

    print(f"Starting Zoom Level {ZOOM}")

    try:
        tiles = [
            f for f in os.listdir(TILE_DIR)
            if f.startswith(f"{ZOOM}_") and f.endswith(".png")
        ]
    except FileNotFoundError:
        print(f"Tile directory not found: {TILE_DIR}\n")
        continue

    total_tiles = len(tiles)
    if not tiles:
        print(f"No tiles found in {TILE_DIR} for zoom {ZOOM}\n")
        continue

    print(f"Found {total_tiles} tiles for zoom {ZOOM}")
    datasets = []
    memfiles = []

    try:
        # Process each tile as RGBA so transparent pixels are preserved.
        for i, fname in enumerate(tiles, start=1):
            try:
                _, x, y = fname[:-4].split("_")
                x, y = int(x), int(y)

                with Image.open(os.path.join(TILE_DIR, fname)) as image:
                    img = np.array(image.convert("RGBA"))

                if img.shape[0] != TILE_SIZE or img.shape[1] != TILE_SIZE:
                    print(f"WARNING Skipping {fname}: unexpected size {img.shape}")
                    continue

                bounds = tile_bounds(x, y, ZOOM)
                transform = from_bounds(*bounds, TILE_SIZE, TILE_SIZE)

                meta = {
                    "driver": "GTiff",
                    "height": TILE_SIZE,
                    "width": TILE_SIZE,
                    "count": img.shape[2],
                    "dtype": "uint8",
                    "crs": "EPSG:3857",
                    "transform": transform,
                }

                memfile = MemoryFile()
                memfiles.append(memfile)
                with memfile.open(**meta) as dst:
                    for band_index in range(img.shape[2]):
                        dst.write(img[:, :, band_index], band_index + 1)
                datasets.append(memfile.open())
            except (OSError, ValueError) as e:
                print(f"WARNING Error processing {fname}: {e}")

            if i % PROGRESS_INTERVAL == 0 or i == total_tiles:
                print(f"{i}/{total_tiles} images processed")

        if not datasets:
            print(f"No valid tiles found for zoom {ZOOM}; skipping merge\n")
            continue

        print("Merging tiles into one georeferenced raster (this may take a while)...")
        mosaic, out_transform = merge(datasets)
        meta = datasets[0].meta.copy()
        meta.update({
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
        })

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with rasterio.open(output_path, "w", **meta) as dest:
            dest.write(mosaic)

        print(f"Saved georeferenced mosaic: {output_path}")
        print("CRS: EPSG:3857 (Web Mercator)\n")
    except Exception as e:
        print(f"ERROR Zoom Level {ZOOM} failed: {e}\n")
    finally:
        for dataset in datasets:
            dataset.close()
        for memfile in memfiles:
            memfile.close()

print("Complete")
