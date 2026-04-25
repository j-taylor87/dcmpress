# dicom_processing.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026

from io import BytesIO
from pathlib import Path
import zipfile

from pydicom import dcmread
from pydicom.dataset import Dataset
from pydicom.errors import InvalidDicomError

from logging_config import LOGGER
from models import ProcessingResult


def get_unique_zip_filename(uploaded_filename: str, used_zip_filenames: set[str]) -> str:
    """Return a unique filename for storage inside the output ZIP archive.

    Parameters
    ----------
    uploaded_filename : str
        Original uploaded filename.
    used_zip_filenames : set[str]
        ZIP filenames already used during the current processing run.

    Returns
    -------
    str
        Unique filename for the ZIP archive.
    """
    original_filename = Path(uploaded_filename).name or "dicom_file.dcm"
    filename_path = Path(original_filename)

    filename_stem = filename_path.stem or "dicom_file"
    filename_suffix = filename_path.suffix or ".dcm"

    zip_filename = original_filename
    duplicate_counter = 2

    while zip_filename in used_zip_filenames:
        zip_filename = f"{filename_stem}_{duplicate_counter}{filename_suffix}"
        duplicate_counter += 1

    used_zip_filenames.add(zip_filename)
    return zip_filename


def get_transfer_syntax_uid(dataset: Dataset):
    """Return the dataset transfer syntax UID.

    Parameters
    ----------
    dataset : Dataset
        pydicom dataset.

    Returns
    -------
    pydicom.uid.UID
        Dataset transfer syntax UID.

    Raises
    ------
    ValueError
        If file meta information or Transfer Syntax UID is missing.
    """
    file_meta = getattr(dataset, "file_meta", None)
    transfer_syntax_uid = getattr(file_meta, "TransferSyntaxUID", None)

    if transfer_syntax_uid is None:
        raise ValueError("Missing Transfer Syntax UID in DICOM file meta information.")

    return transfer_syntax_uid


def decompress_dataset_if_required(
    dataset: Dataset,
    preserve_instance_uid: bool,
    decoding_plugin: str,
) -> bool:
    """Decompress a DICOM dataset in place if its transfer syntax is compressed.

    Parameters
    ----------
    dataset : Dataset
        pydicom dataset to inspect and decompress.
    preserve_instance_uid : bool
        If True, prevents pydicom from generating a new SOP Instance UID during
        decompression.
    decoding_plugin : str
        pydicom decoding plugin name. Use an empty string to allow automatic
        plugin selection.

    Returns
    -------
    bool
        True if decompression was performed. False if the dataset was already
        uncompressed.

    Raises
    ------
    ValueError
        If compressed pixel data is expected but missing.
    NotImplementedError
        If no available decoder supports the transfer syntax.
    RuntimeError
        If the requested decoder plugin is unavailable or cannot decode the data.
    """
    transfer_syntax_uid = get_transfer_syntax_uid(dataset)

    if not transfer_syntax_uid.is_compressed:
        return False

    if "PixelData" not in dataset:
        raise ValueError("Compressed transfer syntax found, but no Pixel Data element is present.")

    generate_instance_uid_setting = False if preserve_instance_uid else None

    try:
        dataset.decompress(
            decoding_plugin=decoding_plugin,
            generate_instance_uid=generate_instance_uid_setting,
        )

    except RuntimeError:
        fallback_decoding_plugin = "gdcm"

        if decoding_plugin == fallback_decoding_plugin:
            raise

        LOGGER.warning(
            "Decompression failed using decoding plugin '%s'. Retrying with '%s'.",
            decoding_plugin or "auto",
            fallback_decoding_plugin,
            exc_info=True,
        )

        dataset.decompress(
            decoding_plugin=fallback_decoding_plugin,
            generate_instance_uid=generate_instance_uid_setting,
        )

    return True


def write_dataset_to_bytes(dataset: Dataset) -> bytes:
    """Write a DICOM dataset to an in-memory byte string.

    Parameters
    ----------
    dataset : Dataset
        pydicom dataset to write.

    Returns
    -------
    bytes
        Encoded DICOM bytes.
    """
    dicom_buffer = BytesIO()
    dataset.save_as(dicom_buffer, enforce_file_format=True)
    dicom_buffer.seek(0)

    return dicom_buffer.getvalue()


def process_uploaded_file(
    uploaded_file,
    zip_file: zipfile.ZipFile,
    used_zip_filenames: set[str],
    force_read: bool,
    preserve_instance_uid: bool,
    decoding_plugin: str,
    file_index: int,
) -> ProcessingResult:
    """Read, optionally decompress, and add one uploaded DICOM file to the ZIP.

    Parameters
    ----------
    uploaded_file
        Streamlit uploaded file object.
    zip_file : zipfile.ZipFile
        Open ZIP archive to which the processed DICOM file will be added.
    used_zip_filenames : set[str]
        ZIP filenames already used during this run.
    force_read : bool
        Whether to pass force=True to pydicom.dcmread().
    preserve_instance_uid : bool
        Whether to preserve the original SOP Instance UID where possible.
    decoding_plugin : str
        pydicom decoding plugin name.
    file_index : int
        One-based index of the file in the current upload batch, used for logging.

    Returns
    -------
    ProcessingResult
        Result object containing success state, processed dataset, ZIP filename,
        and user-facing status message.
    """
    uploaded_file.seek(0)

    try:
        LOGGER.info("Processing file %s: %s", file_index, uploaded_file.name)

        dataset = dcmread(uploaded_file, force=force_read)

        original_transfer_syntax_uid = get_transfer_syntax_uid(dataset)
        original_transfer_syntax_name = original_transfer_syntax_uid.name
        original_transfer_syntax_uid_value = str(original_transfer_syntax_uid)

        LOGGER.info(
            "File %s original transfer syntax: %s",
            file_index,
            original_transfer_syntax_uid,
        )

        decompression_performed = decompress_dataset_if_required(
            dataset=dataset,
            preserve_instance_uid=preserve_instance_uid,
            decoding_plugin=decoding_plugin,
        )

        output_transfer_syntax_uid = get_transfer_syntax_uid(dataset)
        output_transfer_syntax_name = output_transfer_syntax_uid.name
        output_transfer_syntax_uid_value = str(output_transfer_syntax_uid)

        LOGGER.info(
            "File %s output transfer syntax: %s",
            file_index,
            output_transfer_syntax_uid,
        )

        dicom_bytes = write_dataset_to_bytes(dataset)

        zip_filename = get_unique_zip_filename(
            uploaded_filename=uploaded_file.name,
            used_zip_filenames=used_zip_filenames,
        )

        zip_file.writestr(zip_filename, dicom_bytes)

        if decompression_performed:
            user_message = "Decompression successful."
        else:
            user_message = "File is already uncompressed. It was added to the ZIP unchanged."

        LOGGER.info("File %s added to ZIP as: %s", file_index, zip_filename)

        return ProcessingResult(
            success=True,
            dataset=dataset,
            zip_filename=zip_filename,
            user_message=user_message,
            original_transfer_syntax_name=original_transfer_syntax_name,
            original_transfer_syntax_uid=original_transfer_syntax_uid_value,
            output_transfer_syntax_name=output_transfer_syntax_name,
            output_transfer_syntax_uid=output_transfer_syntax_uid_value,
        )

    except InvalidDicomError:
        LOGGER.warning("Invalid DICOM file at index %s.", file_index, exc_info=True)

        return ProcessingResult(
            success=False,
            dataset=None,
            zip_filename=None,
            user_message=(
                "Invalid DICOM file. If this is a known DICOM object without a standard "
                "preamble, try enabling force read."
            ),
        )

    except NotImplementedError:
        LOGGER.warning("Unsupported compressed transfer syntax for file index %s.", file_index, exc_info=True)

        return ProcessingResult(
            success=False,
            dataset=None,
            zip_filename=None,
            user_message=(
                "Unsupported compressed transfer syntax or no suitable decoder is available. "
                "Check that the required pylibjpeg plugins are installed."
            ),
        )

    except RuntimeError:
        LOGGER.warning("Decoder runtime failure for file index %s.", file_index, exc_info=True)

        return ProcessingResult(
            success=False,
            dataset=None,
            zip_filename=None,
            user_message=(
                "The selected decoder could not decode this file. Try the automatic decoder option "
                "or check the installed pylibjpeg plugins."
            ),
        )

    except ValueError as value_error:
        LOGGER.warning("DICOM validation/write error for file index %s.", file_index, exc_info=True)

        return ProcessingResult(
            success=False,
            dataset=None,
            zip_filename=None,
            user_message=str(value_error),
        )

    except Exception:
        LOGGER.exception("Unexpected processing error for file index %s.", file_index)

        return ProcessingResult(
            success=False,
            dataset=None,
            zip_filename=None,
            user_message="Unexpected error while processing this file. See the app logs for details.",
        )