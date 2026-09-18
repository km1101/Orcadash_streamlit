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

On Windows, prefer **`run_app.bat`** (uses the repo `.venv` so OrcFxAPI and scipy match the app):

```bat
run_app.bat
```

If you see **“No module named 'OrcFxAPI'”**, Streamlit is usually running under the wrong Python. Close it and start via `run_app.bat`, or copy `OrcFxAPI.py` and `OrcFxAPIConfig.py` from your OrcaFlex install into that Python’s `site-packages`.

Requires a machine with **OrcaFlex installed and licensed** (`OrcFxAPI`). Without it, the UI still loads; extractions are disabled and the app shows a setup banner.

## Documentation

- [streamlit_app/README.md](streamlit_app/README.md) — dashboard workflow (steps 1–7), navigation, architecture
- [backend/README.md](backend/README.md) — extraction modules
