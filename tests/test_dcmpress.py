# test_dcmpress.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Tests for filename, transfer-syntax, decompression, UI helper, and logging logic.

import io
import logging
import zipfile

import pytest
from pydicom import dcmread
from pydicom.data import get_testdata_file
from pydicom.dataset import Dataset
from pydicom.uid import ExplicitVRLittleEndian

import logging_config
from dicom_processing import (
    decompress_dataset_if_required,
    get_transfer_syntax_uid,
    get_unique_zip_filename,
    process_uploaded_file,
)
from ui_components import get_decoding_plugin_display_name, is_colour_image
import numpy as np


def load_testdata_dataset(filename):
    """Read a pydicom test data file, skipping the test if it is unavailable."""
    path = get_testdata_file(filename)
    if path is None:
        pytest.skip(f"pydicom test data file unavailable: {filename}")
    return dcmread(path)


class FakeUploadedFile(io.BytesIO):
    """Minimal stand-in for a Streamlit UploadedFile (BytesIO with a name)."""

    def __init__(self, data, name):
        super().__init__(data)
        self.name = name


def make_uploaded_file(filename, upload_name=None):
    """Build a FakeUploadedFile from the raw bytes of a pydicom test data file."""
    path = get_testdata_file(filename)
    if path is None:
        pytest.skip(f"pydicom test data file unavailable: {filename}")
    with open(path, "rb") as source_file:
        data = source_file.read()
    return FakeUploadedFile(data, upload_name or filename)


# --- get_unique_zip_filename ------------------------------------------------


def test_get_unique_zip_filename_first_use_is_unchanged():
    used = set()
    assert get_unique_zip_filename("image.dcm", used) == "image.dcm"
    assert "image.dcm" in used


def test_get_unique_zip_filename_deduplicates():
    used = set()
    first = get_unique_zip_filename("image.dcm", used)
    second = get_unique_zip_filename("image.dcm", used)
    third = get_unique_zip_filename("image.dcm", used)
    assert first == "image.dcm"
    assert second == "image_2.dcm"
    assert third == "image_3.dcm"


def test_get_unique_zip_filename_handles_path_and_missing_name():
    used = set()
    assert get_unique_zip_filename("/some/dir/scan.DCM", used) == "scan.DCM"
    # A path with no usable name falls back to a default filename.
    assert get_unique_zip_filename("", used) == "dicom_file.dcm"


# --- get_transfer_syntax_uid ------------------------------------------------


def test_get_transfer_syntax_uid_returns_uid():
    dataset = load_testdata_dataset("CT_small.dcm")
    uid = get_transfer_syntax_uid(dataset)
    assert str(uid) == "1.2.840.10008.1.2.1"


def test_get_transfer_syntax_uid_missing_meta_raises():
    dataset = Dataset()  # no file_meta
    with pytest.raises(ValueError):
        get_transfer_syntax_uid(dataset)


# --- decompress_dataset_if_required -----------------------------------------


def test_decompress_uncompressed_dataset_returns_false():
    dataset = load_testdata_dataset("CT_small.dcm")
    performed = decompress_dataset_if_required(
        dataset=dataset,
        preserve_instance_uid=False,
        decoding_plugin=None,
    )
    assert performed is False
    assert get_transfer_syntax_uid(dataset).is_compressed is False


def test_decompress_compressed_dataset_changes_transfer_syntax():
    dataset = load_testdata_dataset("MR_small_jpeg_ls_lossless.dcm")
    assert get_transfer_syntax_uid(dataset).is_compressed is True

    performed = decompress_dataset_if_required(
        dataset=dataset,
        preserve_instance_uid=False,
        decoding_plugin=None,
    )

    assert performed is True
    output_uid = get_transfer_syntax_uid(dataset)
    assert output_uid.is_compressed is False
    assert output_uid == ExplicitVRLittleEndian


def test_decompress_preserves_instance_uid_when_requested():
    dataset = load_testdata_dataset("MR_small_jpeg_ls_lossless.dcm")
    original_instance_uid = dataset.SOPInstanceUID

    decompress_dataset_if_required(
        dataset=dataset,
        preserve_instance_uid=True,
        decoding_plugin=None,
    )

    assert dataset.SOPInstanceUID == original_instance_uid


def test_decompress_with_explicit_gdcm_plugin():
    pytest.importorskip("gdcm")
    dataset = load_testdata_dataset("JPEG2000.dcm")
    assert get_transfer_syntax_uid(dataset).is_compressed is True

    performed = decompress_dataset_if_required(
        dataset=dataset,
        preserve_instance_uid=False,
        decoding_plugin="gdcm",
    )

    assert performed is True
    assert get_transfer_syntax_uid(dataset).is_compressed is False


def test_decompress_missing_pixel_data_raises():
    dataset = load_testdata_dataset("MR_small_jpeg_ls_lossless.dcm")
    del dataset.PixelData
    with pytest.raises(ValueError):
        decompress_dataset_if_required(
            dataset=dataset,
            preserve_instance_uid=False,
            decoding_plugin=None,
        )


# --- process_uploaded_file (end-to-end into ZIP) ----------------------------


def test_process_uploaded_file_decompresses_into_zip():
    uploaded = make_uploaded_file("MR_small_jpeg_ls_lossless.dcm")
    zip_buffer = io.BytesIO()
    used = set()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        result = process_uploaded_file(
            uploaded_file=uploaded,
            zip_file=zip_file,
            used_zip_filenames=used,
            force_read=False,
            preserve_instance_uid=False,
            decoding_plugin=None,
            file_index=1,
        )

    assert result.success is True
    assert result.dataset is not None
    assert result.zip_filename in used
    assert "Decompression successful" in result.user_message
    assert result.output_transfer_syntax_uid == "1.2.840.10008.1.2.1"

    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer) as zip_file:
        assert result.zip_filename in zip_file.namelist()


def test_process_uploaded_file_copies_uncompressed_unchanged():
    uploaded = make_uploaded_file("CT_small.dcm")
    zip_buffer = io.BytesIO()
    used = set()

    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        result = process_uploaded_file(
            uploaded_file=uploaded,
            zip_file=zip_file,
            used_zip_filenames=used,
            force_read=False,
            preserve_instance_uid=False,
            decoding_plugin=None,
            file_index=1,
        )

    assert result.success is True
    assert "already uncompressed" in result.user_message
    assert result.original_transfer_syntax_uid == result.output_transfer_syntax_uid


# --- ui_components pure helpers ---------------------------------------------


def test_get_decoding_plugin_display_name_known_and_unknown():
    assert get_decoding_plugin_display_name(None) == "Auto"
    assert get_decoding_plugin_display_name("gdcm") == "GDCM"
    # Unknown plugin name falls back to its string form.
    assert get_decoding_plugin_display_name("unknown") == "unknown"


def test_is_colour_image_detects_rgb():
    dataset = Dataset()
    dataset.SamplesPerPixel = 3
    dataset.PhotometricInterpretation = "RGB"
    rgb_array = np.zeros((4, 4, 3), dtype=np.uint8)
    assert is_colour_image(dataset, rgb_array) is True


def test_is_colour_image_detects_monochrome():
    dataset = Dataset()
    dataset.SamplesPerPixel = 1
    dataset.PhotometricInterpretation = "MONOCHROME2"
    mono_array = np.zeros((4, 4), dtype=np.uint8)
    assert is_colour_image(dataset, mono_array) is False


# --- logging_config ---------------------------------------------------------


def test_configure_logger_is_idempotent():
    logger = logging_config.configure_logger()
    handler_count = len(logger.handlers)
    logging_config.configure_logger()
    assert len(logging.getLogger(logging_config.LOGGER_NAME).handlers) == handler_count


def test_configure_logger_has_console_and_file_handlers():
    logger = logging_config.configure_logger()
    handler_types = {type(handler).__name__ for handler in logger.handlers}
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_processing_emits_no_patient_identifiers(caplog):
    """Regression: emitted log records must not contain patient identifiers."""
    dataset = load_testdata_dataset("MR_small_jpeg_ls_lossless.dcm")
    patient_name = str(getattr(dataset, "PatientName", ""))
    patient_id = str(getattr(dataset, "PatientID", ""))
    # Guard against a meaningless test if the fixture has empty identifiers.
    if not patient_name and not patient_id:
        pytest.skip("Test fixture has no patient identifiers to check against.")

    uploaded = make_uploaded_file("MR_small_jpeg_ls_lossless.dcm")
    zip_buffer = io.BytesIO()

    # The dcmpress logger does not propagate to root, so attach caplog's
    # handler directly to it to capture emitted records.
    app_logger = logging.getLogger(logging_config.LOGGER_NAME)
    app_logger.addHandler(caplog.handler)
    try:
        with caplog.at_level(logging.DEBUG, logger=logging_config.LOGGER_NAME):
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                process_uploaded_file(
                    uploaded_file=uploaded,
                    zip_file=zip_file,
                    used_zip_filenames=set(),
                    force_read=False,
                    preserve_instance_uid=False,
                    decoding_plugin=None,
                    file_index=1,
                )
    finally:
        app_logger.removeHandler(caplog.handler)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert log_text  # processing should have produced log output
    if patient_name:
        assert patient_name not in log_text
    if patient_id:
        assert patient_id not in log_text
