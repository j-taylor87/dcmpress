# config.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026

from pathlib import Path

APP_NAME = "dcmpress"
APP_ICON_PATH = Path("assets/slinky_coloured.png")

OUTPUT_ZIP_FILENAME = "decompressed_dicom_files.zip"

DECODING_PLUGIN_OPTIONS = [
    None,
    "pylibjpeg",
    "gdcm",
    "pyjpegls",
    "pillow",
    "pydicom",
]

DECODING_PLUGIN_DISPLAY_NAMES = {
    None: "Auto",
    "pylibjpeg": "pylibjpeg",
    "gdcm": "GDCM",
    "pyjpegls": "JPEG-LS",
    "pillow": "Pillow",
    "pydicom": "pydicom native",
}