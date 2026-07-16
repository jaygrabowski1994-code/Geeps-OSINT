"""
Image Metadata (EXIF) Investigation module.

Extracts embedded metadata from a local image file -- the kind of data
that routinely leaks in photos shared online: camera make/model,
timestamps, software, and (crucially for OSINT) embedded GPS
coordinates.

Two backends, in order of preference:
  1. exiftool (if installed) -- the gold standard; reads far more tags
     and formats than any pure-Python library. Invoked as a subprocess
     with -json for clean parsing.
  2. Pillow (if the 'Pillow' package is available) -- a lightweight
     fallback that covers standard JPEG/TIFF EXIF, including GPS.

If neither is available, the module explains how to get one. It only
ever reads a local file the user explicitly points at -- it does not
download anything.
"""

from __future__ import annotations

import json
import os
import subprocess

from core.logger import get_logger
from core.plugins import PluginMeta
from core.tools import is_installed, path
from core.ui import banner, clear, err, info, ok, pause, prompt, section, warn

log = get_logger("exif")

MODULE_META = PluginMeta(
    key="7",
    name="Image Metadata (EXIF)",
    description="Extract EXIF/metadata (incl. GPS) from a local image via exiftool or Pillow",
    order=70,
)

# Tags we surface prominently because they matter most for OSINT.
_KEY_TAGS = [
    ("Make", "Camera make"),
    ("Model", "Camera model"),
    ("DateTimeOriginal", "Date taken"),
    ("CreateDate", "Created"),
    ("Software", "Software"),
    ("Artist", "Artist/author"),
    ("Copyright", "Copyright"),
    ("ImageSize", "Image size"),
    ("GPSLatitude", "GPS latitude"),
    ("GPSLongitude", "GPS longitude"),
    ("GPSPosition", "GPS position"),
]


def _extract_exiftool(filepath: str) -> dict | None:
    exe = path("exiftool")
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "-json", "-n", filepath],
            capture_output=True, text=True, timeout=20,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("exiftool failed on %s: %s", filepath, exc)
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        data = json.loads(result.stdout)
        return data[0] if isinstance(data, list) and data else None
    except (ValueError, IndexError):
        return None


def _extract_pillow(filepath: str) -> dict | None:
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS
    except ImportError:
        return None

    try:
        with Image.open(filepath) as img:
            raw = img._getexif() if hasattr(img, "_getexif") else None
            size = f"{img.width}x{img.height}"
    except Exception as exc:
        log.warning("Pillow failed to open %s: %s", filepath, exc)
        return None

    out: dict = {"ImageSize": size}
    if not raw:
        return out

    for tag_id, value in raw.items():
        tag = TAGS.get(tag_id, str(tag_id))
        if tag == "GPSInfo" and isinstance(value, dict):
            gps = {GPSTAGS.get(k, str(k)): v for k, v in value.items()}
            lat = _pillow_gps_coord(gps, "GPSLatitude", "GPSLatitudeRef")
            lon = _pillow_gps_coord(gps, "GPSLongitude", "GPSLongitudeRef")
            if lat is not None:
                out["GPSLatitude"] = lat
            if lon is not None:
                out["GPSLongitude"] = lon
        else:
            out[tag] = value
    return out


def _pillow_gps_coord(gps: dict, coord_key: str, ref_key: str):
    """Convert Pillow's degrees/minutes/seconds GPS tuple to signed decimal degrees."""
    coord = gps.get(coord_key)
    ref = gps.get(ref_key)
    if not coord:
        return None
    try:
        degrees, minutes, seconds = (float(x) for x in coord)
        decimal = degrees + minutes / 60 + seconds / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 6)
    except (TypeError, ValueError):
        return None


def _display(metadata: dict, backend: str) -> None:
    ok(f"Metadata extracted via {backend}.")

    section("Key tags")
    shown_any = False
    for tag, label in _KEY_TAGS:
        if tag in metadata and metadata[tag] not in (None, ""):
            info(f"{label}: {metadata[tag]}")
            # ImageSize is always derivable from the pixels -- it doesn't
            # count as "real" embedded metadata for the stripped-image hint.
            if tag != "ImageSize":
                shown_any = True
    if not shown_any:
        info("No camera/date/GPS tags present (image may have been stripped of metadata).")

    # GPS is the highest-value OSINT signal -- if present, build a maps link.
    lat = metadata.get("GPSLatitude")
    lon = metadata.get("GPSLongitude")
    if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
        section("Location")
        warn(f"Embedded GPS coordinates found: {lat}, {lon}")
        info(f"Map: https://www.google.com/maps?q={lat},{lon}")

    section(f"All tags ({len(metadata)})")
    for key in sorted(metadata):
        value = metadata[key]
        text = str(value)
        if len(text) > 300:
            text = text[:300] + " ...(truncated)"
        info(f"{key}: {text}")


def run() -> None:
    clear()
    banner("IMAGE METADATA (EXIF)")
    print("Extracts embedded metadata (camera, timestamps, GPS) from a\n"
          "local image file. Reads only the file you point at.\n")

    if not is_installed("exiftool"):
        try:
            import PIL  # noqa: F401
            info("exiftool not found; using the Pillow fallback (covers standard EXIF).")
        except ImportError:
            err("Neither exiftool nor Pillow is available.")
            info("Install exiftool (recommended): Termux 'pkg install exiftool', "
                 "Ubuntu 'sudo apt install libimage-exiftool-perl'.")
            info("Or install Pillow: pip install Pillow")
            pause()
            return

    filepath = prompt("Enter path to an image file")
    if not filepath:
        warn("No path entered. Returning to menu.")
        pause()
        return

    filepath = os.path.expanduser(filepath)
    if not os.path.isfile(filepath):
        err(f"No file found at: {filepath}")
        pause()
        return

    log.info("EXIF investigation started for a local file")

    metadata = None
    backend = ""
    try:
        metadata = _extract_exiftool(filepath)
        if metadata is not None:
            backend = "exiftool"
    except Exception:
        log.exception("Unexpected error running exiftool")

    if metadata is None:
        try:
            metadata = _extract_pillow(filepath)
            if metadata is not None:
                backend = "Pillow"
        except Exception:
            log.exception("Unexpected error running Pillow")

    if metadata is None:
        err("Could not extract metadata from this file with the available backends.")
        info("The file may be an unsupported format, or corrupt.")
        pause()
        return

    _display(metadata, backend)
    log.info("EXIF investigation complete (backend=%s, %d tags)", backend, len(metadata))
    pause()
