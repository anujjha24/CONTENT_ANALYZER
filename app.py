import sys
import os
import re
import io
import shutil
import zipfile
import tempfile
import subprocess
from datetime import datetime

import pandas as pd
import streamlit as st

# UTF-8 fix
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def build_filename(channel: str, date_str: str) -> str:
    channel_clean = re.sub(r"[^A-Z0-9]", "", str(channel).upper().strip())

    if not channel_clean:
        channel_clean = "UNKNOWN"

    date_clean = ""

    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(date_str).strip())

    if m:
        date_clean = f"{m.group(1)}{m.group(2)}{m.group(3)}"

    else:
        m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(date_str).strip())

        if m2:
            date_clean = f"{m2.group(3)}{m2.group(2)}{m2.group(1)}"
        else:
            date_clean = "00000000"

    return f"{channel_clean}({date_clean}) barc_nct_comparison"


st.set_page_config(page_title="BARC NCT Comparison", layout="centered")

st.title("BARC NCT Comparison Tool")

uploaded_files = st.file_uploader(
    "Upload Excel Files",
    type=["xlsx"],
    accept_multiple_files=True
)

if st.button("Analyze Files"):

    if not uploaded_files:
        st.error("Please upload at least one file.")
        st.stop()

    results = []
    errors = []

    progress = st.progress(0)

    for idx, f in enumerate(uploaded_files):

        try:
            file_bytes = f.read()

            # Extract filename info
            try:
                df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)

                df_barc = df[
                    df.get("source", "").apply(
                        lambda x: str(x).upper().strip()
                    ) == "BARC XML"
                ]

                channel = (
                    str(df_barc["channel name"].iloc[0])
                    if len(df_barc)
                    else ""
                )

                date_val = (
                    str(df_barc["TelecastDate"].iloc[0])
                    if len(df_barc)
                    else ""
                )

                fname = build_filename(channel, date_val) + ".xlsx"

            except Exception:
                fname = "output.xlsx"

            with tempfile.TemporaryDirectory() as tempdir:

                # Save uploaded file
                input_path = os.path.join(
                    tempdir,
                    "brand_comparison_template.xlsx"
                )

                with open(input_path, "wb") as out_f:
                    out_f.write(file_bytes)

                # Copy processing script
                script_src = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "barc_nct_comparison.py"
                )

                script_dst = os.path.join(
                    tempdir,
                    "barc_nct_comparison.py"
                )

                shutil.copy(script_src, script_dst)

                # Run processing script
                result = subprocess.run(
                    [sys.executable, "-u", "barc_nct_comparison.py"],
                    cwd=tempdir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={
                        **os.environ,
                        "PYTHONIOENCODING": "utf-8"
                    }
                )

                # Read output
                output_path = os.path.join(
                    tempdir,
                    "barc_nct_comparison.xlsx"
                )

                if not os.path.exists(output_path):
                    errors.append({
                        "file": f.name,
                        "error": "Output file not generated"
                    })
                    continue

                with open(output_path, "rb") as out_f:
                    out_bytes = out_f.read()

                results.append({
                    "fname": fname,
                    "data": out_bytes
                })

        except subprocess.CalledProcessError as e:

            stderr_text = (
                e.stderr.decode("utf-8", errors="replace")
                if e.stderr else ""
            )

            errors.append({
                "file": f.name,
                "error": stderr_text
            })

        except Exception as e:

            errors.append({
                "file": f.name,
                "error": str(e)
            })

        progress.progress((idx + 1) / len(uploaded_files))

    # Download Section
    if results:

        if len(results) == 1:

            r = results[0]

            st.download_button(
                label="Download Processed File",
                data=r["data"],
                file_name=r["fname"],
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        else:

            zip_buf = io.BytesIO()

            with zipfile.ZipFile(
                zip_buf,
                "w",
                zipfile.ZIP_DEFLATED
            ) as zf:

                for r in results:
                    zf.writestr(r["fname"], r["data"])

            zip_buf.seek(0)

            zip_name = (
                f"barc_nct_batch_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            )

            st.download_button(
                label="Download ZIP File",
                data=zip_buf,
                file_name=zip_name,
                mime="application/zip"
            )

    if errors:
        st.error("Some files failed processing.")

        for err in errors:
            st.write(err)