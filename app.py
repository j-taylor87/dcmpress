# app.py
# dcmpress — DICOM decompressor
# -----------------------------------------------
# Drag & drop one or more DICOM files to view basic info
# and decompress them to Explicit VR Little Endian.

import streamlit as st
from pydicom import dcmread
from pydicom.pixels.utils import decompress
from io import BytesIO
import zipfile
import base64

def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

st.set_page_config(page_title="dcmpress", layout="wide")

# app title and icon
image_base64 = get_base64_image("slinky.png")
st.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 10px;">
        <img src="data:image/png;base64,{image_base64}" width="50" height="50" style="margin: 0;">
        <h1 style="margin: 0; font-size: 3rem;">dcmpress</h1>
    </div>
    """,
    unsafe_allow_html=True
)
# st.title("dcmpress")
st.markdown("<h3 style='font-size:1.2rem;'>Decompress compressed DICOM files</h3>", unsafe_allow_html=True)

col1, col2 = st.columns([0.2, 0.8])

with col1:
    uploaded_files = st.file_uploader(
        "Upload one or more compressed DICOM files", type=None, accept_multiple_files=True
    )

# create in-memory ZIP buffer
zip_buffer = BytesIO()

with col2:
    if uploaded_files:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for uploaded_file in uploaded_files:
                ds = None
                with st.container():
                    st.divider()
                    col2a, col2b = st.columns([0.9, 0.1])
                    with col2a:
                        try:
                            ds = dcmread(uploaded_file, force=True)
                            st.write(f"**File:** {uploaded_file.name}")
                            st.write(f"**Patient Name:** {getattr(ds, 'PatientName', 'N/A')}")
                            st.write(f"**Original Transfer Syntax:** {ds.file_meta.TransferSyntaxUID.name}")
                            ds_decompressed = decompress(
                                ds, decoding_plugin="pylibjpeg", generate_instance_uid=False
                            )
                            st.success("✅ Decompression successful")
                            st.write(f"**New Transfer Syntax:** {ds.file_meta.TransferSyntaxUID.name}")

                            # save to bytes and add to ZIP
                            bytes_io = BytesIO()
                            ds_decompressed.save_as(bytes_io)
                            bytes_io.seek(0)
                            zipf.writestr(uploaded_file.name, bytes_io.read())

                        except Exception as e:
                            st.error(f"Error processing {uploaded_file.name}: {e}")

                    with col2b:
                        if ds is not None:
                            try:
                                st.image(ds.pixel_array, caption="Preview", clamp=True, use_container_width=True)
                            except Exception:
                                st.warning("No image data available.")

with col1:
    # after loop, prepare download
    zip_buffer.seek(0)
    st.download_button(
        label="🡻 Download all decompressed files (.zip)",
        data=zip_buffer,
        file_name="decompressed_dicoms.zip",
        mime="application/zip"
    )
