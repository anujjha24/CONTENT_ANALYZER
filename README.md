# BARC vs NCT Comparison Tool

A Streamlit-based web application for comparing BARC and NCT brand data with automated analysis and reporting.

## Features

- 📊 Side-by-side brand comparison
- 🔄 Automatic brand matching
- ⏱️ Duration analysis
- 📈 Commercial metrics
- 📦 Batch processing support
- 📥 Multi-file upload with ZIP download

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## Deploying to Streamlit Cloud

1. Push your code to GitHub
2. Go to [Streamlit Cloud](https://streamlit.io/cloud)
3. Click "New app"
4. Select your repository and branch
5. Set the main file to `app.py`
6. Click "Deploy"

## Files

- `app.py` - Main Streamlit application
- `barc_nct_comparison.py` - Core comparison logic and analysis engine
- `requirements.txt` - Python dependencies
- `.streamlit/config.toml` - Streamlit configuration

## Input Format

Accepts Excel files (.xlsx) with BARC XML data and NCT comparison templates.

## Output

- Single file: Direct Excel download
- Multiple files: ZIP archive with all results

---

**No localhost required!** This app is fully cloud-ready for deployment.
