# app.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Author: James Taylor
# Created: May 2025
# Last updated: 25 Apr 2026
#
# Streamlit entry point for the dcmpress DICOM decompressor app.

from io import BytesIO
import zipfile
import streamlit as st

from config import APP_NAME, OUTPUT_ZIP_FILENAME
from dicom_processing import process_uploaded_file
from logging_config import LOGGER
from ui_components import (
    display_app_header,
    display_dicom_preview,
    display_dicom_summary,
    display_sidebar_controls,
)


st.set_page_config(page_title=APP_NAME, layout="wide")

display_app_header()

left_col, right_col = st.columns([0.25, 0.75])

with left_col:
    sidebar_controls = display_sidebar_controls()
    download_placeholder = st.empty()

zip_buffer = BytesIO()
used_zip_filenames: set[str] = set()
successful_file_count = 0

with right_col:
    if sidebar_controls.uploaded_files:
        LOGGER.info(
            "Starting batch processing for %s uploaded file(s).",
            len(sidebar_controls.uploaded_files),
        )

        progress_bar = st.progress(0)

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_index, uploaded_file in enumerate(sidebar_controls.uploaded_files, start=1):
                st.divider()

                file_info_col, preview_col = st.columns([0.7, 0.3])

                with st.spinner(f"Processing {uploaded_file.name}"):
                    processing_result = process_uploaded_file(
                        uploaded_file=uploaded_file,
                        zip_file=zip_file,
                        used_zip_filenames=used_zip_filenames,
                        force_read=sidebar_controls.force_read,
                        preserve_instance_uid=sidebar_controls.preserve_instance_uid,
                        decoding_plugin=sidebar_controls.decoding_plugin,
                        file_index=file_index,
                    )

                with file_info_col:
                    if processing_result.success and processing_result.dataset is not None:
                        st.success(processing_result.user_message)

                        display_dicom_summary(
                            processing_result=processing_result,
                            uploaded_filename=uploaded_file.name,
                            show_patient_identifiers=sidebar_controls.show_patient_identifiers,
                        )

                        successful_file_count += 1

                    else:
                        st.write(f"**File:** {uploaded_file.name}")
                        st.error(processing_result.user_message)

                with preview_col:
                    if processing_result.dataset is not None:
                        display_dicom_preview(processing_result.dataset)

                progress_bar.progress(file_index / len(sidebar_controls.uploaded_files))

        LOGGER.info(
            "Batch processing complete. %s of %s file(s) added to ZIP.",
            successful_file_count,
            len(sidebar_controls.uploaded_files),
        )

        st.caption(
            f"{successful_file_count} of {len(sidebar_controls.uploaded_files)} file(s) added to the output ZIP."
        )

zip_buffer.seek(0)

if sidebar_controls.uploaded_files:
    with download_placeholder:
        st.download_button(
            label="Download decompressed files (.zip)",
            data=zip_buffer.getvalue(),
            file_name=OUTPUT_ZIP_FILENAME,
            mime="application/zip",
            disabled=successful_file_count == 0,
            width="stretch",
        )