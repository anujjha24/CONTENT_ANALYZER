import sys
import os

# Force UTF-8 stdout on Windows to prevent UnicodeEncodeError
# when printing subprocess output containing special chars (−, ✓, ✗, →)
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import re
import io
import shutil
import zipfile
import tempfile
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
# Expose Content-Disposition so frontend can read filename
CORS(app, expose_headers=["Content-Disposition"])

def build_filename(channel: str, date_str: str) -> str:
    channel_clean = re.sub(r"[^A-Z0-9]", "", str(channel).upper().strip())
    if not channel_clean: channel_clean = "UNKNOWN"
    
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


@app.route("/", methods=["GET"])
def index():
    return send_file("content_analyzer.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    results = []
    errors = []

    for f in files:
        if not f.filename: continue
        
        # Read file to extract channel and date for the filename
        file_bytes = f.read()
        try:
            df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
            df_barc = df[df.get("source", "").apply(lambda x: str(x).upper().strip()) == "BARC XML"]
            channel = str(df_barc["channel name"].iloc[0]) if len(df_barc) else ""
            date_val = str(df_barc["TelecastDate"].iloc[0]) if len(df_barc) else ""
            fname = build_filename(channel, date_val) + ".xlsx"
        except Exception:
            fname = "output.xlsx"

        # Create a temp dir to run the script safely without race conditions
        with tempfile.TemporaryDirectory() as tempdir:
            # 1. Write the input file
            input_path = os.path.join(tempdir, "brand_comparison_template.xlsx")
            with open(input_path, "wb") as out_f:
                out_f.write(file_bytes)
                
            # 2. Copy the script to tempdir
            script_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "barc_nct_comparison.py")
            script_dst = os.path.join(tempdir, "barc_nct_comparison.py")
            shutil.copy(script_src, script_dst)
            
            # 3. Run the script
            try:
                result = subprocess.run(
                    [sys.executable, "-u", "barc_nct_comparison.py"],
                    cwd=tempdir, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"}
                )
                print(f"[OK] Script completed for {f.filename}", flush=True)
            except subprocess.CalledProcessError as e:
                stderr_text = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
                # Sanitise for Windows console before printing
                safe_stderr = stderr_text.encode("ascii", errors="replace").decode("ascii")
                print(f"[ERROR] Script failed for {f.filename} (rc={e.returncode}): {safe_stderr}", flush=True)
                errors.append({"file": f.filename, "error": "Script crashed", "details": stderr_text})
                continue
            except Exception as e:
                print(f"[ERROR] Unexpected: {type(e).__name__}: {e}", flush=True)
                errors.append({"file": f.filename, "error": str(e)})
                continue
                
            # 4. Read the output file
            output_path = os.path.join(tempdir, "barc_nct_comparison.xlsx")
            if not os.path.exists(output_path):
                errors.append({"file": f.filename, "error": "Output file not generated"})
                continue
                
            with open(output_path, "rb") as out_f:
                out_bytes = out_f.read()
                
            results.append({"fname": fname, "data": out_bytes})

    if not results:
        return jsonify({"error": "All files failed", "details": errors}), 500

    if len(results) == 1 and not errors:
        r = results[0]
        return send_file(
            io.BytesIO(r["data"]),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=r["fname"],
        )
    else:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for r in results:
                zf.writestr(r["fname"], r["data"])
        zip_buf.seek(0)
        zip_name = f"barc_nct_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=zip_name,
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Server starting on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
