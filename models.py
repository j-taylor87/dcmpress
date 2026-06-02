# models.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026

"""Dataclasses for dcmpress sidebar controls and per-file processing results."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydicom.dataset import Dataset

if TYPE_CHECKING:
    from streamlit.runtime.uploaded_file_manager import UploadedFile

@dataclass
class ProcessingResult:
    """Container for the result of processing one uploaded DICOM file."""

    success: bool
    dataset: Dataset | None
    zip_filename: str | None
    user_message: str
    original_transfer_syntax_name: str | None = None
    original_transfer_syntax_uid: str | None = None
    output_transfer_syntax_name: str | None = None
    output_transfer_syntax_uid: str | None = None

@dataclass
class SidebarControls:
    """Container for user-selected Streamlit sidebar controls."""

    uploaded_files: "list[UploadedFile]"
    force_read: bool
    preserve_instance_uid: bool
    show_patient_identifiers: bool
    decoding_plugin: str | None