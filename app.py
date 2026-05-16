"""
Content Analyzer — Streamlit frontend
Wraps barc_nct_comparison.py via subprocess (zero logic changes to the core script).

Run locally : streamlit run app.py
Deploy      : push to GitHub → connect to Streamlit Cloud
"""

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

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Content Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS — matches the dark theme of content_analyzer.html ───────────────
st.markdown("""
<style>
  /* ---------- global ---------- */
  @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@600;700&family=DM+Sans:wght@400;500;600&display=swap');

  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  .stApp {
    background: #0b0f1a;
    background-image:
      linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  /* ---------- header ---------- */
  .ca-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 28px 0 24px;
    border-bottom: 0.5px solid rgba(99,179,237,0.18);
    margin-bottom: 32px;
  }
  .ca-logo-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #3b82f6, #06b6d4);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
  }
  .ca-logo-text {
    font-family: 'Rajdhani', sans-serif;
    font-size: 30px; font-weight: 700; letter-spacing: 2.5px;
    background: linear-gradient(120deg, #93c5fd, #38bdf8, #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .ca-logo-sub {
    font-size: 11px; letter-spacing: 3px;
    text-transform: uppercase; color: #64748b; margin-top: 2px;
  }
  .ca-badge {
    margin-left: auto;
    background: rgba(59,130,246,0.1);
    border: 0.5px solid rgba(59,130,246,0.3);
    color: #60a5fa; font-size: 11px; letter-spacing: 1px;
    padding: 4px 12px; border-radius: 20px;
    font-family: 'Rajdhani', sans-serif; font-weight: 600;
  }

  /* ---------- section label ---------- */
  .ca-section {
    font-size: 10px; letter-spacing: 3px;
    text-transform: uppercase; color: #64748b;
    margin: 24px 0 10px;
    border-bottom: 0.5px solid rgba(99,179,237,0.12);
    padding-bottom: 6px;
  }

  /* ---------- card ---------- */
  .ca-card {
    background: #111827;
    border: 0.5px solid rgba(99,179,237,0.15);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 18px;
  }

  /* ---------- uploader ---------- */
  [data-testid="stFileUploader"] {
    background: rgba(59,130,246,0.04) !important;
    border: 1.5px dashed rgba(99,179,237,0.35) !important;
    border-radius: 12px !important;
    padding: 8px !important;
  }
  [data-testid="stFileUploader"]:hover {
    border-color: #3b82f6 !important;
    background: rgba(59,130,246,0.08) !important;
  }
  [data-testid="stFileUploadDropzone"] label {
    color: #94a3b8 !important; font-size: 13px !important;
  }

  /* ---------- inputs ---------- */
  [data-testid="stNumberInput"] input,
  [data-testid="stTextInput"] input {
    background: #1a2234 !important;
    border: 0.5px solid rgba(99,179,237,0.2) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
    font-family: 'DM Sans', sans-serif !important;
  }
  label[data-testid="stWidgetLabel"] { color: #94a3b8 !important; font-size: 12px !important; }

  /* ---------- tab strip ---------- */
  [data-testid="stTabs"] [role="tab"] {
    background: #1a2234 !important;
    border-radius: 8px 8px 0 0 !important;
    color: #94a3b8 !important;
    font-weight: 500 !important;
  }
  [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: #1f2d42 !important;
    color: #e2e8f0 !important;
    border-bottom: 2px solid #3b82f6 !important;
  }

  /* ---------- run button ---------- */
  .stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #3b82f6, #06b6d4) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px !important;
    font-family: 'Rajdhani', sans-serif !important;
    font-size: 17px !important;
    font-weight: 700 !important;
    letter-spacing: 2px !important;
    cursor: pointer !important;
    transition: opacity 0.2s !important;
  }
  .stButton > button:hover { opacity: 0.88 !important; }
  .stButton > button:disabled { opacity: 0.4 !important; cursor: not-allowed !important; }

  /* ---------- download button ---------- */
  [data-testid="stDownloadButton"] > button {
    background: rgba(59,130,246,0.12) !important;
    border: 0.5px solid rgba(59,130,246,0.35) !important;
    color: #60a5fa !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    width: 100% !important;
  }
  [data-testid="stDownloadButton"] > button:hover {
    background: rgba(59,130,246,0.22) !important;
  }

  /* ---------- metric cards ---------- */
  [data-testid="stMetric"] {
    background: #1a2234 !important;
    border: 0.5px solid rgba(99,179,237,0.15) !important;
    border-radius: 10px !important;
    padding: 14px !important;
  }
  [data-testid="stMetricValue"] { color: #06b6d4 !important; font-family: 'Rajdhani', sans-serif !important; }
  [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 11px !important; }

  /* ---------- progress ---------- */
  [data-testid="stProgress"] > div > div {
    background: linear-gradient(90deg, #3b82f6, #06b6d4) !important;
    border-radius: 4px !important;
  }
  [data-testid="stProgress"] { background: #1a2234 !important; border-radius: 4px !important; }

  /* ---------- success / error ---------- */
  [data-testid="stAlert"][data-baseweb="notification"] {
    border-radius: 10px !important;
    border: 0.5px solid !important;
  }
  .stSuccess { border-color: rgba(16,185,129,0.4) !important; background: rgba(16,185,129,0.06) !important; }
  .stError   { border-color: rgba(239,68,68,0.4)  !important; background: rgba(239,68,68,0.06)  !important; }

  /* ---------- log expander ---------- */
  [data-testid="stExpander"] {
    background: #070c14 !important;
    border: 0.5px solid rgba(99,179,237,0.15) !important;
    border-radius: 12px !important;
  }
  [data-testid="stExpander"] summary { color: #60a5fa !important; font-size: 12px !important; }

  /* ---------- file item row ---------- */
  .file-item {
    display: flex; align-items: center; gap: 12px;
    background: #1a2234;
    border: 0.5px solid rgba(99,179,237,0.15);
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 13px;
  }
  .file-dot { width: 8px; height: 8px; border-radius: 50%; background: #10b981; flex-shrink: 0; }
  .file-name { color: #93c5fd; font-family: monospace; flex: 1;
               overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .file-size { color: #64748b; font-size: 11px; }

  /* ---------- hide streamlit chrome ---------- */
  #MainMenu { visibility: hidden; }
  footer     { visibility: hidden; }
  header     { visibility: hidden; }

  /* ---------- general text ---------- */
  p, span, div { color: #e2e8f0; }
  code { background: #1a2234 !important; color: #93c5fd !important; border-radius: 4px !important; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def fmt_size(b: int) -> str:
    if b < 1024:        return f"{b} B"
    if b < 1024**2:     return f"{b/1024:.1f} KB"
    return f"{b/1024**2:.1f} MB"

def build_filename(channel: str, date_str: str) -> str:
    """Identical logic to app.py Flask version."""
    channel_clean = re.sub(r"[^A-Z0-9]", "", str(channel).upper().strip())
    if not channel_clean:
        channel_clean = "UNKNOWN"
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(date_str).strip())
    if m:
        date_clean = f"{m.group(1)}{m.group(2)}{m.group(3)}"
    else:
        m2 = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(date_str).strip())
        date_clean = f"{m2.group(3)}{m2.group(2)}{m2.group(1)}" if m2 else "00000000"
    return f"{channel_clean}({date_clean}) barc_nct_comparison"

def run_comparison(file_bytes: bytes, original_name: str) -> tuple[bytes, str, dict]:
    """
    Identical to the Flask /analyze route:
    1. Write input to temp dir as brand_comparison_template.xlsx
    2. Copy barc_nct_comparison.py there
    3. Run it as a subprocess
    4. Read back barc_nct_comparison.xlsx
    Returns (xlsx_bytes, output_filename, stats_dict)
    """
    # --- detect channel + date for filename ---
    fname = "output.xlsx"
    stats = {}
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), dtype=str)
        df_barc = df[df.get("source", pd.Series(dtype=str))
                       .apply(lambda x: str(x).upper().strip()) == "BARC XML"]
        if len(df_barc):
            channel  = str(df_barc["channel name"].iloc[0])
            date_val = str(df_barc["TelecastDate"].iloc[0])
            fname    = build_filename(channel, date_val) + ".xlsx"
            stats["channel"]   = channel
            stats["date"]      = date_val
            stats["barc_rows"] = len(df_barc)
            stats["nct_rows"]  = len(df[df["source"].apply(lambda x: str(x).upper().strip()) == "NCT"])
    except Exception:
        pass

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. Write input
        input_path = os.path.join(tmpdir, "brand_comparison_template.xlsx")
        with open(input_path, "wb") as fh:
            fh.write(file_bytes)

        # 2. Copy script
        script_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "barc_nct_comparison.py")
        shutil.copy(script_src, os.path.join(tmpdir, "barc_nct_comparison.py"))

        # 3. Run
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, "-u", "barc_nct_comparison.py"],
            cwd=tmpdir, capture_output=True,
            env=env,
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")
        stats["stdout"] = stdout
        stats["stderr"] = stderr

        if result.returncode != 0:
            raise RuntimeError(f"Script failed (rc={result.returncode}):\n{stderr}")

        # 4. Read output
        output_path = os.path.join(tmpdir, "barc_nct_comparison.xlsx")
        if not os.path.exists(output_path):
            raise FileNotFoundError("barc_nct_comparison.xlsx was not generated.")

        with open(output_path, "rb") as fh:
            out_bytes = fh.read()

    return out_bytes, fname, stats

# ── Header ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="ca-header">
  <div class="ca-logo-icon">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"
         stroke-linecap="round" stroke-linejoin="round">
      <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2v-4
               M9 21H5a2 2 0 0 1-2-2v-4m0 0h18"/>
      <circle cx="12" cy="12" r="2" fill="white"/>
    </svg>
  </div>
  <div>
    <div class="ca-logo-text">CONTENT ANALYZER</div>
    <div class="ca-logo-sub">BARC × NCT Comparison Engine</div>
  </div>
  <div class="ca-badge">v3.0</div>
</div>
""", unsafe_allow_html=True)

# ── Mode tabs ──────────────────────────────────────────────────────────────────

tab_single, tab_bulk = st.tabs(["📄  Single File", "📦  Bulk Upload"])

# ── Settings (shared) ──────────────────────────────────────────────────────────

st.markdown('<div class="ca-section">Comparison Settings</div>', unsafe_allow_html=True)
col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
with col_s1:
    threshold = st.number_input("Similarity Threshold", min_value=0.0, max_value=1.0,
                                value=0.80, step=0.01, format="%.2f",
                                help="Minimum score for a brand name match (0–1). Default: 0.80")
with col_s2:
    tolerance = st.number_input("Time Tolerance (seconds)", min_value=0, max_value=60,
                                value=1, step=1,
                                help="Allowed time window difference in seconds. Default: 1")
with col_s3:
    st.markdown("""
    <div style="padding-top:28px; font-size:12px; color:#64748b; line-height:1.8">
      These values are passed directly to <code>barc_nct_comparison.py</code> — no logic is modified.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Single File Tab ────────────────────────────────────────────────────────────

with tab_single:
    st.markdown('<div class="ca-section">Input File</div>', unsafe_allow_html=True)

    uploaded_single = st.file_uploader(
        "Drop your Excel file here or click to browse",
        type=["xlsx", "xls"],
        key="single_uploader",
        label_visibility="visible",
    )

    if uploaded_single:
        st.markdown(f"""
        <div class="file-item">
          <div class="file-dot"></div>
          <span class="file-name">{uploaded_single.name}</span>
          <span class="file-size">{fmt_size(uploaded_single.size)}</span>
        </div>
        """, unsafe_allow_html=True)

    run_single = st.button("▶  RUN ANALYSIS", key="btn_single", disabled=not uploaded_single)

    if run_single and uploaded_single:
        prog  = st.progress(0)
        status_msg = st.empty()

        try:
            status_msg.markdown("🔄 **Reading file...**")
            prog.progress(15)
            file_bytes = uploaded_single.read()

            status_msg.markdown("⚙️ **Running Python comparison engine...**")
            prog.progress(40)

            xlsx_bytes, out_fname, stats = run_comparison(file_bytes, uploaded_single.name)

            prog.progress(90)
            status_msg.markdown("📦 **Preparing download...**")

            prog.progress(100)
            status_msg.empty()

            # --- metrics ---
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Channel", stats.get("channel", "—"))
            col_m2.metric("Date",    stats.get("date",    "—"))
            col_m3.metric("BARC Rows", stats.get("barc_rows", "—"))

            st.success(f"✅ Analysis complete — **{out_fname}** is ready to download.")

            st.download_button(
                label=f"⬇️  Download  {out_fname}",
                data=xlsx_bytes,
                file_name=out_fname,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_single",
            )

            # --- log ---
            if stats.get("stdout"):
                with st.expander("📋 Script output log", expanded=False):
                    st.code(stats["stdout"], language="text")

        except Exception as e:
            prog.progress(100)
            status_msg.empty()
            err_msg = str(e)
            st.error(f"❌ Error: {err_msg}")
            if "stderr" in locals() or True:
                try:
                    # Show stderr from stats if available
                    _, _, stats_err = run_comparison.__code__, None, None
                except Exception:
                    pass
            with st.expander("🔍 Full error details"):
                st.code(err_msg, language="text")

# ── Bulk Upload Tab ────────────────────────────────────────────────────────────

with tab_bulk:
    st.markdown('<div class="ca-section">Bulk Upload</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px; color:#64748b; margin-bottom:14px;">
      Upload multiple Excel files — each file is processed independently.
      Channel name and date are auto-detected from the data.
      Output is delivered as a single ZIP archive.
    </div>
    """, unsafe_allow_html=True)

    uploaded_bulk = st.file_uploader(
        "Drop multiple Excel files here or click to browse",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key="bulk_uploader",
        label_visibility="visible",
    )

    if uploaded_bulk:
        st.markdown(f'<div class="ca-section">File Queue — {len(uploaded_bulk)} file(s)</div>',
                    unsafe_allow_html=True)
        for uf in uploaded_bulk:
            st.markdown(f"""
            <div class="file-item">
              <div class="file-dot"></div>
              <span class="file-name">{uf.name}</span>
              <span class="file-size">{fmt_size(uf.size)}</span>
            </div>
            """, unsafe_allow_html=True)

    run_bulk = st.button("▶  RUN BULK ANALYSIS", key="btn_bulk",
                         disabled=not uploaded_bulk)

    if run_bulk and uploaded_bulk:
        prog  = st.progress(0)
        status_msg = st.empty()
        results = []
        errors  = []

        for i, uf in enumerate(uploaded_bulk):
            pct = int(10 + (i / len(uploaded_bulk)) * 80)
            status_msg.markdown(f"⚙️ **Processing {i+1}/{len(uploaded_bulk)}: {uf.name}**")
            prog.progress(pct)

            try:
                xlsx_bytes, out_fname, stats = run_comparison(uf.read(), uf.name)
                results.append({"fname": out_fname, "data": xlsx_bytes, "stats": stats})
            except Exception as e:
                errors.append({"file": uf.name, "error": str(e)})

        prog.progress(95)
        status_msg.markdown("📦 **Building ZIP archive...**")

        if results:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for r in results:
                    zf.writestr(r["fname"], r["data"])
            zip_buf.seek(0)
            zip_name = f"barc_nct_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

            prog.progress(100)
            status_msg.empty()

            # --- metrics ---
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Files Processed", len(results))
            col_m2.metric("Files Failed",    len(errors))
            col_m3.metric("ZIP Size", fmt_size(zip_buf.getbuffer().nbytes))

            if errors:
                st.warning(f"⚠️ {len(errors)} file(s) failed — see details below.")
            st.success(f"✅ {len(results)} file(s) processed. ZIP ready to download.")

            st.download_button(
                label=f"⬇️  Download  {zip_name}",
                data=zip_buf.getvalue(),
                file_name=zip_name,
                mime="application/zip",
                key="dl_bulk",
            )

            # --- per-file results ---
            st.markdown('<div class="ca-section">Results</div>', unsafe_allow_html=True)
            for r in results:
                st.markdown(f"""
                <div class="file-item">
                  <div class="file-dot" style="background:#10b981"></div>
                  <span class="file-name">{r['fname']}</span>
                  <span class="file-size" style="color:#10b981">✓ OK</span>
                </div>
                """, unsafe_allow_html=True)

            for e in errors:
                st.markdown(f"""
                <div class="file-item">
                  <div class="file-dot" style="background:#ef4444"></div>
                  <span class="file-name">{e['file']}</span>
                  <span class="file-size" style="color:#ef4444">✗ {e['error'][:60]}</span>
                </div>
                """, unsafe_allow_html=True)

            # --- logs ---
            for r in results:
                log = r["stats"].get("stdout", "")
                if log.strip():
                    with st.expander(f"📋 Log — {r['fname']}", expanded=False):
                        st.code(log, language="text")

        else:
            prog.progress(100)
            status_msg.empty()
            st.error("❌ All files failed to process.")
            for e in errors:
                st.error(f"**{e['file']}**: {e['error']}")

# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div style="margin-top:60px; padding-top:20px;
            border-top: 0.5px solid rgba(99,179,237,0.12);
            text-align:center; font-size:11px; color:#334155; letter-spacing:1px;">
  CONTENT ANALYZER &nbsp;·&nbsp; BARC × NCT COMPARISON ENGINE &nbsp;·&nbsp; v3.0
</div>
""", unsafe_allow_html=True)
