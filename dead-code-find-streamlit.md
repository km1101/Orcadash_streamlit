# Dead code find (Streamlit project)

## Trigger

User runs `/dead-code` or asks to find dead code, unused code, audit dead code, find unused imports, find unused functions, remove dead code, clean up unused code, or clear out leftover React files.

## Project context

- **Main deliverable:** `app.py` — the Python entry point that runs the Streamlit dashboard (`streamlit run app.py`). Treat this as the root of the live application.
- **Legacy artifact:** The repo also contains files left over from an earlier React-based version of the project (e.g. `package.json`, `package-lock.json`/`yarn.lock`, `src/*.jsx`/`*.tsx`, `public/`, `vite.config.*`, `webpack.config.*`, `.eslintrc*`, `tsconfig.json`, `node_modules/`, component/CSS files). These are almost never imported by anything Python runs and are strong dead-code candidates as **whole files**, not just individual symbols.
- Any Python module imported (directly or transitively) by `app.py` is "live" application code. Anything never reached from `app.py` is a dead-code candidate.

## Scope resolution

- **Explicit:** If the user names a path, file, or glob, use that.
- **Selection:** If the user has a selection in the editor, scope to that file.
- **Default:** Whole repo, since the goal is (a) tracing what `app.py` actually uses and (b) identifying leftover non-Python/React material. Start from `app.py` and walk its import graph (local modules, `pages/` if using Streamlit multipage, helper modules, `.streamlit/` config) to establish the "live" set before flagging anything as dead.
- **Limit:** Process a bounded set of files; if the repo is very large, say so and suggest narrowing (e.g. "just check the React leftovers" or "just check app.py and its imports").

## Skip paths (do not analyze line-by-line by default)

- `node_modules/`, `dist/`, `build/`, `.venv/`, `venv/`, `__pycache__/`, `.git/`, coverage/cache dirs, minified/bundled artifacts.
- Lockfiles and generated files (`package-lock.json`, `yarn.lock`, `poetry.lock`, `.streamlit/secrets.toml` — never inspect secrets content).
- These are skipped for *content* analysis but `node_modules/`-adjacent **project-defining** files (`package.json`, config files at repo root) are still surfaced at the file level as candidates for the React-cleanup pass below.

## Two passes

### Pass 1 — React leftovers (whole-file dead code)

Identify files that belong to the old React toolchain rather than the Streamlit app:

- Markers: `package.json`, `package-lock.json`/`yarn.lock`/`pnpm-lock.yaml`, `tsconfig.json`, `vite.config.*`, `webpack.config.*`, `babel.config.*`, `.eslintrc*`, `.babelrc`, `src/**/*.jsx`, `src/**/*.tsx`, `src/App.js`/`App.tsx`, `public/index.html`, `.css`/`.scss` files tied to those components, `node_modules/` (flag the folder itself, don't enumerate contents).
- **Verify before flagging:** confirm `app.py` (and anything it imports) never shells out to or reads these files (e.g. no `subprocess` call to `npm`/`node`, no reading of `package.json` for version info, no iframe/static file serving of the React build via `st.components.v1` or similar). If such a reference exists, do **not** mark as dead — note the dependency instead.
- Report these as **whole-file removal candidates**, grouped under a "Legacy React artifacts" section, separate from the Python findings table.

### Pass 2 — Python dead code within the Streamlit app

Applies to `app.py` and any `.py` files it imports (directly or transitively), plus any other top-level `.py` files in the repo not reached from `app.py` (these are themselves candidates for "unused module").

| Type | Meaning | Verification |
|------|---------|--------------|
| `unused-import` | Imported but never used in the file | No reference to that name in the file. Streamlit-specific: `import streamlit as st` is essentially always used; watch for leftover imports from removed features (e.g. an unused `plotly`, `altair`, `matplotlib` import after a chart was swapped out). |
| `unused-variable` | Assigned but never read | No read of that name in scope. Be careful with Streamlit's script-rerun model: a variable set via `st.session_state` may be read on a later rerun, not later in the same script pass — don't flag `st.session_state[...]` writes as unused just because there's no same-file read. |
| `unused-function` | Defined but never called in analyzed scope | No call site found. Watch for Streamlit callback functions passed by reference (`on_click=my_func`, `on_change=my_func`) — these count as a use even though there's no direct `my_func()` call. |
| `unused-module` | A `.py` file in the repo never imported by `app.py` or anything it imports | Not reachable from the `app.py` import graph. Note as "possible unused" if it looks like a script meant to be run standalone (e.g. has `if __name__ == "__main__":`, is a data-prep/ingestion script, or matches a `scripts/`, `notebooks/`, or `etl/` convention). |
| `unreachable` | Code after `return`/`raise`/`st.stop()` or in a branch never taken | Control flow shows it never executes. Streamlit's `st.stop()` halts the script — treat it like `return`/`raise` for reachability. |
| `unused-export` (n/a for typical single-app Streamlit projects) | Only relevant if the project also exposes a shared Python package (`import`-able elsewhere). Skip unless the repo has a `setup.py`/`pyproject.toml` making it a library. | Search all `.py` files in scope. |

## Workflow

1. **Map the live graph:** Starting from `app.py`, follow local imports (and Streamlit multipage `pages/*.py` if present) to build the set of files that are actually executed by the dashboard.
2. **Pass 1 (React leftovers):** Scan the repo root and any `src/`/`public/`-style dirs for the React markers above. Verify no runtime dependency from `app.py`. List as whole-file removal candidates.
3. **Pass 2 (Python dead code):** For each file in the live graph, and separately for any `.py` file outside it, identify unused imports/variables/functions/unreachable code per the table above.
4. **Deduplicate and annotate** with a remediation ("Remove import", "Delete unreachable block", "Delete file — legacy React artifact, not referenced by app.py", "Delete file — Python module unreachable from app.py").
5. **Output report** (see below). **Do not edit or delete files** unless the user explicitly asked to "remove", "fix", "clean up", or "clear out" the code/files.
6. **If user asked to remove/clear:**
   - Legacy React files: delete whole files/folders (after confirming no runtime reference).
   - Python dead code: apply in safe order — (a) unused imports, (b) unused variables, (c) unreachable blocks, (d) unused functions, (e) unreachable/unused whole modules.
   - After each change to a `.py` file, re-check it still parses (and, where feasible, that `app.py` still imports cleanly).
   - Summarize what was removed.

## Report format

- **Header:** e.g. "Streamlit project scope: repo root, live graph rooted at `app.py`."
- **Section A — Legacy React artifacts:** File/folder | Why flagged | Confidence (verified no reference / likely unused) | Remediation.
- **Section B — Python dead code:** File | Line(s) | Type | Symbol/snippet | Remediation | Confidence.
- **Summary line:** e.g. "3 legacy React files/folders and 7 Python dead-code findings across 4 files."
- **Caveats:** note any Streamlit-specific judgment calls (session_state writes, callback references, standalone scripts) that were deliberately not flagged.

## Guardrails

- Never flag `st.session_state` writes as unused solely due to no same-run read.
- Never flag a function passed as a Streamlit callback (`on_click`, `on_change`, `key=` widget callbacks) as unused.
- Don't delete a React-era file if `app.py` or its imports reference it (e.g. serving a built static asset, reading `package.json` for a version string).
- Standalone scripts (data prep, migrations, notebooks) reachable only by being run directly, not imported, are noted as "possible unused module" rather than asserted dead, unless the user confirms they're obsolete.
- All removals must be semantics-preserving — the dashboard should still run identically after Python cleanup.
- If the user did not ask to remove, only report; do not edit or delete files.

## Output

- Structured report (scope, two-section findings, summary, caveats).
- If removal was requested: list of files deleted and edits applied, plus a one-line summary (e.g. "Removed legacy React toolchain (5 files, 1 folder) and cleaned 4 unused imports + 1 unreachable block in app.py and utils.py.").
