# Orcadash Streamlit

ORCAFLEX post-simulation results console built with Streamlit. Extraction logic lives in [`backend/var_and_func`](backend/var_and_func) and is loaded by [`streamlit_app/utils/loaders.py`](streamlit_app/utils/loaders.py).

## Clone and run locally

```bash
git clone https://github.com/km1101/Orcadash_streamlit.git
cd Orcadash_streamlit
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
streamlit run streamlit_app/app.py
```

Requires a machine with **OrcaFlex installed and licensed** (`OrcFxAPI`). Without it, the UI still loads; extractions are disabled and **Settings** shows API status.

## Streamlit Community Cloud

This app is **not** a fit for public Streamlit Cloud hosting: OrcFxAPI is proprietary and must be installed locally with a license. Use the steps above on a workstation that has OrcaFlex.

## Documentation

- [streamlit_app/README.md](streamlit_app/README.md) — dashboard workflow (steps 1–7), navigation, architecture
- [backend/README.md](backend/README.md) — extraction modules
