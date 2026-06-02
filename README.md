# dcmpress

A Streamlit web app that **decompresses** DICOM files for image analysis purposes.

Many DICOM objects are stored using a compressed transfer syntax (JPEG, JPEG 2000,
JPEG-LS, RLE, etc.). Some downstream tools cannot read compressed pixel data. dcmpress
reads each uploaded file, decompresses the pixel data to an uncompressed (Explicit VR
Little Endian) transfer syntax where required, re-saves it, and bundles the results into
a single ZIP archive for download.

## What it does

- Reads one or more uploaded DICOM files (with optional force read for objects missing
  the standard preamble / `DICM` prefix).
- Detects the transfer syntax and decompresses the dataset in place when it is compressed.
  Files that are already uncompressed are added to the ZIP unchanged.
- Optionally preserves the original SOP Instance UID (off by default, since reusing UIDs
  can cause conflicts in PACS).
- Shows a per-file summary (original/output transfer syntax, modality, SOP class) and a
  small image preview.
- Writes every decompressed/copied file into a single downloadable ZIP archive.

## Supported decoder plugins

Decompression is performed by pydicom using one of the following decoding plugins. "Auto"
lets pydicom try the available compatible decoders; a specific plugin can be selected to
force one decoder:

- **GDCM** (`gdcm`, via `python-gdcm`) — also used as the automatic fallback decoder.
- **pylibjpeg** (`pylibjpeg` with `pylibjpeg-libjpeg`, `pylibjpeg-openjpeg`,
  `pylibjpeg-rle`) — JPEG, JPEG 2000 (OpenJPEG), and RLE.
- **JPEG-LS** (`pyjpegls`).
- **Pillow** (`pillow`).
- **pydicom** native.

## Running locally

Requires Python 3.13.

```bash
python -m venv .venv
. .venv/Scripts/activate        # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```

The app is then available at http://localhost:8501.

## Running with Docker

```bash
docker compose up --build
```

This builds the image and starts the app. The container exposes Streamlit on port 8501;
`docker-compose.yml` publishes it on host port 8502 (http://localhost:8502).

To run the image directly without compose:

```bash
docker build -t dcmpress .
docker run --rm -p 8501:8501 dcmpress
```

## Usage

Upload any DICOM files you would like to decompress, confirm the file(s) have been
decompressed successfully, then download the resulting ZIP archive.

## Logging

Logs are written to the console and to `logs/dcmpress.log` (rotating). The log level can be
set with the `LOG_LEVEL` environment variable (default `INFO`). Patient identifiers (e.g.
Patient Name, Patient ID) are never written to the log.
