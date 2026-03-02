# Production Fixes & Troubleshooting Log

This document tracks all the live-environment bugs identified and resolved during the final deployment and testing phases of the Sentinel-Graph system.

## 1. Missing Dependency: `langchain_community`
- **Issue**: The Streamlit dashboard crashed on startup with a `ModuleNotFoundError` for `langchain_community`.
- **Cause**: The `Neo4jGraph` component used by The Detective agent relies on `langchain_community`, which was previously bundled inside LangChain but is now separated.
- **Resolution**:
  - Activated the virtual environment (`venv`).
  - Ran `pip install langchain-community` directly.
  - Added `langchain-community>=0.0.1` explicitly to `requirements.txt` to ensure any future clones of the repository install it automatically.

## 2. Pydantic-AI Version Syntax Error: `result_type`
- **Issue**: The application threw a `pydantic_ai.exceptions.UserError: Unknown keyword arguments: 'result_type'` during Agent initialization.
- **Cause**: The local machine downloaded the newest version of `pydantic-ai` (v0.8.1). This version introduced a breaking syntax change to the `Agent()` setup, deprecating older input formats.
- **Resolution**:
  - Diagnosed documentation for `pydantic_ai.Agent.__init__` via Python REPL.
  - Refactored `agents/cartographer.py`, `agents/detective.py`, and `agents/auditor.py`.
  - Shifted the Gemini LLM string from a keyword argument (`model='...'`) to a strict positional argument.
  - Re-applied `result_type=...` as a strict keyword argument to satisfy the v0.8.1 engine.

## 3. Git Large File Push Error (HTTP 400)
- **Issue**: While attempting to push the `artifacts/` folder (which contained a 3.7MB `.webp` video) to GitHub, git threw an `HTTP 400 curl 22 The requested URL returned error: 400` and disconnected.
- **Cause**: The Git HTTP post buffer size was too small to handle the large blob transfer in a single chunk over the current network connection.
- **Resolution**: 
  - Ran `git config http.postBuffer 524288000` to increase the buffer limit to 500MB.
  - Successfully pushed the large WebP video asset to the `origin/main` repository.

## 4. Documentation Reorganization
- **Issue**: The user requested that the `COMMANDS_USED.md` file be moved from the root directory into the `artifacts/` directory for better project cleanliness.
- **Resolution**:
  - Used `git mv` to shift the file while retaining its commit history.
  - Updated the directory tree graphic inside `README.md` to accurately reflect the new location of the commands log.
