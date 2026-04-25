# ui_components.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026

import base64
from pathlib import Path
import numpy as np
import streamlit as st
from pydicom.dataset import Dataset
from pydicom.pixels import apply_modality_lut, apply_voi_lut

from config import (
    APP_ICON_PATH,
    APP_NAME,
    DECODING_PLUGIN_DISPLAY_NAMES,
    DECODING_PLUGIN_OPTIONS,
)
from logging_config import LOGGER
from models import SidebarControls, ProcessingResult


def get_base64_image(image_path: Path) -> str | None:
    """Read an image from disk and return a base64-encoded string.

    Parameters
    ----------
    image_path : Path
        Path to the image file.

    Returns
    -------
    str | None
        Base64-encoded image string, or None if the image cannot be read.
    """
    try:
        with image_path.open("rb") as image_file:
            return base64.b64encode(image_file.read()).decode()

    except FileNotFoundError:
        LOGGER.warning("App icon file not found: %s", image_path)
        return None

    except OSError:
        LOGGER.exception("Could not read app icon file: %s", image_path)
        return None


def display_app_header() -> None:
    """Display the app title and optional logo."""
    image_base64 = get_base64_image(APP_ICON_PATH)

    if image_base64:
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; gap: 10px;">
                <img src="data:image/png;base64,{image_base64}" width="50" height="50" style="margin: 0;">
                <h1 style="margin: 0; font-size: 3rem;">{APP_NAME}</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title(APP_NAME)

    st.markdown(
        "<h3 style='font-size:1.2rem;'>Decompress compressed DICOM files</h3>",
        unsafe_allow_html=True,
    )


def display_sidebar_controls() -> SidebarControls:
    """Display upload and processing controls.

    Returns
    -------
    SidebarControls
        User-selected processing options and uploaded files.
    """
    uploaded_files = st.file_uploader(
        "Upload one or more compressed DICOM files",
        type=None,
        accept_multiple_files=True,
        help="No extension filter is applied because DICOM files may not use a .dcm extension.",
    )

    force_read = st.checkbox(
        "Force read non-standard DICOM files",
        value=False,
        help="Use only when a known DICOM file is missing the usual file preamble or DICM prefix.",
    )

    preserve_instance_uid = st.checkbox(
        "Preserve SOP Instance UID",
        value=False,
        help=(
            "Preserving the original SOP Instance UID may cause conflicts if the decompressed "
            "files are imported into PACS or another DICOM archive."
        ),
    )

    show_patient_identifiers = st.checkbox(
        "Show patient identifiers",
        value=False,
        help="Displays Patient Name and Patient ID in the app. These values are not written to the log.",
    )

    decoding_plugin = st.selectbox(
        "Decoding plugin",
        options=DECODING_PLUGIN_OPTIONS,
        format_func=get_decoding_plugin_display_name,
        index=0,
        help=(
            "'Auto' lets pydicom try available compatible decoders."
            "Select a specific plugin if you want to force one decoder."
        ),
    )

    return SidebarControls(
        uploaded_files=uploaded_files or [],
        force_read=force_read,
        preserve_instance_uid=preserve_instance_uid,
        show_patient_identifiers=show_patient_identifiers,
        decoding_plugin=decoding_plugin,
    )


def get_decoding_plugin_display_name(plugin_name: str | None) -> str:
    """Return a user-facing display name for a pydicom decoding plugin option.

    Parameters
    ----------
    plugin_name : str | None
        pydicom decoding plugin name, or None for automatic plugin selection.

    Returns
    -------
    str
        User-facing display name.
    """
    return DECODING_PLUGIN_DISPLAY_NAMES.get(plugin_name, str(plugin_name))


def display_dicom_summary(
    processing_result: ProcessingResult,
    uploaded_filename: str,
    show_patient_identifiers: bool,
) -> None:
    """Display basic DICOM metadata for a processed file.

    Parameters
    ----------
    processing_result : ProcessingResult
        Result object containing the processed DICOM dataset and transfer syntax metadata.
    uploaded_filename : str
        Uploaded filename shown in the Streamlit UI.
    show_patient_identifiers : bool
        Whether to display directly identifying patient fields.
    """
    dataset = processing_result.dataset

    if dataset is None:
        st.warning("No DICOM metadata available.")
        return

    st.write(f"**File:** {uploaded_filename}")
    st.write(f"**ZIP filename:** {processing_result.zip_filename}")

    st.write(
        f"**Original Transfer Syntax:** "
        f"{processing_result.original_transfer_syntax_name} "
        f"`{processing_result.original_transfer_syntax_uid}`"
    )

    st.write(
        f"**Output Transfer Syntax:** "
        f"{processing_result.output_transfer_syntax_name} "
        f"`{processing_result.output_transfer_syntax_uid}`"
    )

    st.write(f"**Modality:** {getattr(dataset, 'Modality', 'N/A')}")
    st.write(f"**SOP Class:** {getattr(dataset, 'SOPClassUID', 'N/A')}")

    if show_patient_identifiers:
        st.write(f"**Patient Name:** {getattr(dataset, 'PatientName', 'N/A')}")
        st.write(f"**Patient ID:** {getattr(dataset, 'PatientID', 'N/A')}")


def get_first_preview_frame(pixel_array: np.ndarray, dataset: Dataset) -> np.ndarray:
    """Return the first displayable frame from a DICOM pixel array.

    Parameters
    ----------
    pixel_array : np.ndarray
        DICOM pixel array.
    dataset : Dataset
        pydicom dataset containing image metadata.

    Returns
    -------
    np.ndarray
        Single-frame pixel array.
    """
    number_of_frames = int(getattr(dataset, "NumberOfFrames", 1) or 1)

    if number_of_frames > 1 and pixel_array.ndim >= 3:
        return pixel_array[0]

    return pixel_array


def is_colour_image(dataset: Dataset, pixel_array: np.ndarray) -> bool:
    """Return True if the dataset should be treated as a colour image.

    Parameters
    ----------
    dataset : Dataset
        pydicom dataset containing image metadata.
    pixel_array : np.ndarray
        Pixel array to assess.

    Returns
    -------
    bool
        True if the image appears to be colour.
    """
    samples_per_pixel = int(getattr(dataset, "SamplesPerPixel", 1) or 1)
    photometric_interpretation = str(getattr(dataset, "PhotometricInterpretation", "")).upper()

    return samples_per_pixel > 1 or photometric_interpretation in {
        "RGB",
        "YBR_FULL",
        "YBR_FULL_422",
        "YBR_PARTIAL_420",
        "YBR_PARTIAL_422",
        "YBR_ICT",
        "YBR_RCT",
        "PALETTE COLOR",
    } or (pixel_array.ndim == 3 and pixel_array.shape[-1] in (3, 4))


def normalise_array_for_display(pixel_array: np.ndarray) -> np.ndarray:
    """Normalise an image array to uint8 display range.

    Parameters
    ----------
    pixel_array : np.ndarray
        Image array to normalise.

    Returns
    -------
    np.ndarray
        uint8 image array scaled to 0-255.
    """
    display_array = np.asarray(pixel_array, dtype=np.float64)

    finite_values = display_array[np.isfinite(display_array)]

    if finite_values.size == 0:
        return np.zeros(display_array.shape, dtype=np.uint8)

    lower_limit, upper_limit = np.percentile(finite_values, [1, 99])

    if upper_limit <= lower_limit:
        lower_limit = float(np.min(finite_values))
        upper_limit = float(np.max(finite_values))

    if upper_limit <= lower_limit:
        return np.zeros(display_array.shape, dtype=np.uint8)

    display_array = np.clip(display_array, lower_limit, upper_limit)
    display_array = (display_array - lower_limit) / (upper_limit - lower_limit)
    display_array = display_array * 255

    return display_array.astype(np.uint8)


def get_windowed_preview_array(dataset: Dataset) -> np.ndarray:
    """Return a display-ready preview array from a DICOM dataset.

    Applies modality LUT/rescale and VOI LUT/windowing for monochrome images.
    Colour images are normalised without DICOM greyscale windowing.

    Parameters
    ----------
    dataset : Dataset
        pydicom dataset containing image pixel data.

    Returns
    -------
    np.ndarray
        Display-ready image array.
    """
    pixel_array = dataset.pixel_array
    pixel_array = get_first_preview_frame(pixel_array, dataset)

    if is_colour_image(dataset, pixel_array):
        return normalise_array_for_display(pixel_array)

    display_array = apply_modality_lut(pixel_array, dataset)
    display_array = apply_voi_lut(display_array, dataset)

    display_array = normalise_array_for_display(display_array)

    photometric_interpretation = str(getattr(dataset, "PhotometricInterpretation", "")).upper()

    if photometric_interpretation == "MONOCHROME1":
        display_array = 255 - display_array

    return display_array


def display_dicom_preview(dataset: Dataset) -> None:
    """Display a small image preview from a DICOM dataset.

    For multi-frame datasets, only the first frame is displayed. Monochrome
    images are displayed using DICOM modality LUT/rescale and VOI LUT/windowing
    where available.

    Parameters
    ----------
    dataset : Dataset
        pydicom dataset containing image pixel data.
    """
    if "PixelData" not in dataset:
        st.warning("No image data available.")
        return

    try:
        preview_array = get_windowed_preview_array(dataset)

        st.image(
            preview_array,
            caption="Preview",
            clamp=True,
            width="stretch",
        )

    except Exception as preview_error:
        LOGGER.warning("Preview generation failed.", exc_info=True)
        st.warning(f"Preview unavailable: {preview_error}")