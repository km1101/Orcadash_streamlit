"""Load Files — file manager: upload, folder scan, search/filter, favorites."""
import time

import streamlit as st

from components.cards import pill, section_header
from utils.cache import get_favorites, get_recent_files, toggle_favorite
from utils.cache import get_cached_model_summary
from utils.loaders import ensure_session_state, register_loaded_file, save_uploaded_file, scan_folder_for_sim_files

ensure_session_state()

section_header("Load Files", "Upload .sim files, scan a folder, or reopen something recent.", icon="📂")

tab_upload, tab_folder, tab_manage = st.tabs(["⬆ Upload", "📁 Scan a folder", "🗂️ Manage loaded files"])

# --- Upload tab (single or multiple, drag & drop) ---------------------------
with tab_upload:
    st.caption("Drag and drop one or more `.sim` files, or click to browse.")
    uploads = st.file_uploader(
        "OrcaFlex simulation files", type=["sim"], accept_multiple_files=True, label_visibility="collapsed"
    )

    if uploads:
        progress = st.progress(0.0, text="Processing uploaded files...")
        for i, uploaded in enumerate(uploads):
            with st.spinner(f"Reading {uploaded.name}..."):
                dest = save_uploaded_file(uploaded)
                register_loaded_file(uploaded.name, dest)
                get_cached_model_summary(dest)  # warm the cache
                time.sleep(0.05)  # small, deliberate pause so the progress bar is visible for fast local files
            progress.progress((i + 1) / len(uploads), text=f"Loaded {uploaded.name}")
        progress.empty()
        st.success(f"Loaded {len(uploads)} file(s). Head to **Single Simulation** to start analyzing.")

# --- Folder scan tab ------------------------------------------------------------
with tab_folder:
    st.caption("Point at a local folder (searched recursively) to find `.sim` files without uploading them one by one.")
    folder_path = st.text_input("Folder path", placeholder=r"C:\Projects\OrcaFlex\Models")
    if st.button("🔍 Scan folder", disabled=not folder_path):
        with st.spinner("Scanning folder for .sim files..."):
            found = scan_folder_for_sim_files(folder_path)
        if not found:
            st.warning("No `.sim` files found under that path.")
        else:
            st.session_state["_folder_scan_results"] = [str(p) for p in found]
            st.success(f"Found {len(found)} file(s).")

    scan_results = st.session_state.get("_folder_scan_results", [])
    if scan_results:
        selected = st.multiselect("Select files to load", scan_results, default=scan_results[: min(5, len(scan_results))])
        if st.button("➕ Add selected to session", disabled=not selected):
            progress = st.progress(0.0, text="Loading selected files...")
            for i, path in enumerate(selected):
                from pathlib import Path
                register_loaded_file(Path(path).name, path)
                get_cached_model_summary(path)
                progress.progress((i + 1) / len(selected), text=f"Loaded {Path(path).name}")
            progress.empty()
            st.success(f"Added {len(selected)} file(s) to this session.")

# --- Manage loaded files tab -----------------------------------------------------
with tab_manage:
    search_col, filter_col = st.columns([3, 2])
    search_term = search_col.text_input("🔎 Search by name", placeholder="e.g. riser, C05, mooring")
    filter_type = filter_col.selectbox("Filter by object type", ["All", "Line", "Vessel", "6DBuoy", "3DBuoy", "Winch", "Link"])

    loaded = st.session_state.get("loaded_files", {})
    recent = get_recent_files(limit=15)
    favorites = {f["path"] for f in get_favorites()}

    # Merge: loaded-this-session files first, then recent files not already loaded
    rows = [{"name": n, "path": p} for n, p in loaded.items()]
    seen_paths = {r["path"] for r in rows}
    for r in recent:
        if r["path"] not in seen_paths:
            rows.append({"name": r["name"], "path": r["path"]})
            seen_paths.add(r["path"])

    if search_term:
        rows = [r for r in rows if search_term.lower() in r["name"].lower()]

    if not rows:
        st.info("No files match your search yet. Upload one in the **Upload** tab.")

    for row in rows:
        summary = get_cached_model_summary(row["path"])
        if filter_type != "All" and not summary.get("objects", {}).get(filter_type):
            continue

        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([4, 2, 2, 2])
            with c1:
                fav_marker = "⭐ " if row["path"] in favorites else ""
                st.markdown(f"**{fav_marker}{row['name']}**")
                if summary.get("error"):
                    st.markdown(pill("unreadable", "accent_red"))
                else:
                    counts = summary.get("objects", {})
                    badges = " ".join(
                        pill(f"{t}: {len(names)}", "accent_blue")
                        for t, names in counts.items() if names
                    )
                    st.markdown(badges or pill("no objects found", "accent_amber"))
            with c2:
                st.caption(f"{summary.get('file_size_mb', 0)} MB")
                duration = summary.get("duration_s")
                st.caption(f"{duration:,.0f}s simulated" if duration else "—")
            with c3:
                if st.button("Open", key=f"mgr_open_{row['path']}"):
                    register_loaded_file(row["name"], row["path"])
                    st.switch_page("app_pages/Single_Simulation.py")
                fav_label = "★ Unfavorite" if row["path"] in favorites else "☆ Favorite"
                if st.button(fav_label, key=f"mgr_fav_{row['path']}"):
                    toggle_favorite(row["path"], row["name"])
                    st.rerun()
            with c4:
                with st.expander("Preview metadata"):
                    st.json({
                        "file": row["name"],
                        "path": row["path"],
                        "size_mb": summary.get("file_size_mb"),
                        "duration_s": summary.get("duration_s"),
                        "objects": summary.get("objects"),
                        "error": summary.get("error"),
                    })
