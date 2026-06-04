import concurrent.futures
import math
import os
import threading

import requests

# === CONFIG ===
# BASE_URL = ("https://svc.pictometry.com/Image/3DB1455E-E287-7980-9663-C1DE620700E6/wmts/PICT-TXXARA22-qBMsAzPNJo/default/GoogleMapsCompatible") ### Aransas CAD
# BASE_URL = ("https://svc.pictometry.com/Image/EBDE00D5-9DF8-9BBE-566B-C7579A2F8D8B/wmts/PICT-TXCALH23-bIlrHR59N6/default/GoogleMapsCompatible") ### Calhoun CAD
BASE_URL = ("https://svc.pictometry.com/Image/C3962F3E-305D-D237-723D-44A90A266044/wmts/PICT-TXORAN25-nkr1rpq7vo/default/GoogleMapsCompatible") ### Orange CAD
# BASE_URL = ("https://svc.pictometry.com/Image/97177060-8D3C-4A14-B0C9-A87AB0164E99/wmts/PICT-TXLLAN25-p9VbuuN4xU/default/GoogleMapsCompatible") ### LLano CAD
# BASE_URL = ("https://svc.pictometry.com/Image/29A1DB6C-57B5-1E96-B90C-DB62DCDFFAE9/wmts/PICT-TXBAST23-l3HVaRcAGb/default/GoogleMapsCompatible") ### Bastrop CAD

# ZOOM = 22  # 20 is very detailed
ZOOM_Level = [22]  # 20 is very detailed

# TOP_LEFT = (27.91798, -97.10082)       # (lat, lon)
# BOTTOM_RIGHT = (27.849, -97.04895)     # (lat, lon)
# TOP_LEFT = (27.89926, -97.06845)       # (lat, lon) ### Raft
# BOTTOM_RIGHT = (27.89849, -97.06761)     # (lat, lon)
TOP_LEFT = (30.057306, -93.929194)       # (lat, lon) ### Blind
BOTTOM_RIGHT = (30.053861, -93.920861)     # (lat, lon)
OUT_DIR = r'C:\WJS\SCRIPTS\Python\Image Scraper\Output_tiles'
MAX_WORKERS = 20
PROGRESS_INTERVAL = 50  # print every x images
# ==============


def deg2num(lat, lon, zoom):
    """Convert lat/lon to tile numbers (GoogleMapsCompatible scheme)."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x_tile = int((lon + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile


# Compute tile index bounds
for ZOOM in ZOOM_Level:
    print(f"Starting Zoom Level {ZOOM}")
    x_min, y_max = deg2num(BOTTOM_RIGHT[0], TOP_LEFT[1], ZOOM)  # lower left
    x_max, y_min = deg2num(TOP_LEFT[0], BOTTOM_RIGHT[1], ZOOM)  # upper right

    print(f"Tile range: X={x_min}-{x_max}, Y={y_min}-{y_max}")

    os.makedirs(OUT_DIR, exist_ok=True)

    # Shared counters and lock for thread-safe updates
    counter = 0
    failures = 0
    lock = threading.Lock()

    def download_tile(x, y):
        global counter, failures

        url = f"{BASE_URL}/{ZOOM}/{x}/{y}.png"
        outfile = os.path.join(OUT_DIR, f"{ZOOM}_{x}_{y}.png")

        try:
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            with open(outfile, "wb") as f:
                f.write(response.content)
            result = f"OK {x},{y}"
        except (requests.RequestException, OSError) as e:
            with lock:
                failures += 1
            result = f"ERROR {x},{y} ({e})"
        finally:
            with lock:
                counter += 1
                if counter % PROGRESS_INTERVAL == 0 or counter == total_tiles:
                    print(f"{counter}/{total_tiles} images completed")

        return result

    # Build list of all tile coords
    tiles = [(x, y) for x in range(x_min, x_max + 1) for y in range(y_min, y_max + 1)]
    total_tiles = len(tiles)
    print(f"Total tiles: {total_tiles}")

    # Download with threaded progress tracking
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for result in ex.map(lambda xy: download_tile(*xy), tiles):
            if result.startswith("ERROR"):
                print(result)

    print(f"Zoom Level {ZOOM} Complete ({failures} failures)\n")
print("All downloads complete!")
