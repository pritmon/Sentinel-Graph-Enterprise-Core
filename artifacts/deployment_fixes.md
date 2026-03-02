# Sentinel-Graph: Development & Deployment Refinement Log

This document serves as a comprehensive history of the bugs, architectural hurdles, and live-environment issues that were identified and resolved during the build and deployment of the Sentinel-Graph system.

## 1. Initial Environment Bootstrapping
- **Issue**: System commands like `pip` and `streamlit` were failing globally because an isolated Python environment had not been initialized.
- **Resolution**: 
  - Bootstrapped a dedicated Python virtual environment (`python3 -m venv venv`).
  - Activated the environment and isolated all system dependencies using `requirements.txt` to prevent local machine pollution.

## 2. Cypher Traversal Execution Errors (Markdown Stripping)
- **Issue**: When "The Detective" agent generated Cypher queries, the LLM occasionally wrapped the output in markdown code blocks (e.g., ` ```cypher MATCH (n) RETURN n ``` `). Passing this raw string to the Neo4j Python driver caused immediate database syntax exceptions.
- **Resolution**:
  - Implemented a sanitization function inside `agents/orchestrator.py` during the `execute_cypher` node.
  - Added `.replace("```cypher", "").replace("```", "").strip()` to guarantee only pure, executable Cypher reaches the Neo4j database. 

## 3. Database Security & Utility Refactoring
- **Issue**: Initial connection logic to Neo4j was functional but lacked enterprise-grade security standards and readability.
- **Resolution**:
  - Refactored `src/utils.py` to enforce parameterized query architecture, actively preventing Cypher injection vulnerabilities.
  - Added comprehensive docstrings to all database connection and execution functions.

## 4. LangGraph State Machine Transparency
- **Issue**: While the multi-agent system successfully executed self-RAG loops, the user could not see *why* the agents made decisions or what "The Auditor" scored the initial results.
- **Resolution**:
  - Modified `agents/orchestrator.py` to compile a persistent `reasoning_trace` array within the `GraphState`.
  - Configured the Streamlit dashboard to render these JSON traces sequentially, exposing the internal reasoning of The Cartographer, The Detective, and The Auditor to the end-user.

## 5. Missing Dependency: `langchain_community`
- **Issue**: The Streamlit dashboard crashed on startup with a `ModuleNotFoundError: No module named 'langchain_community'`.
- **Cause**: The `Neo4jGraph` schema tool used by The Detective agent relies on `langchain_community`. This package was historically bundled directly inside `langchain`, but was recently externalized by the maintainers.
- **Resolution**:
  - Installed `langchain-community` directly into the active `venv`.
  - Added `langchain-community>=0.0.1` explicitly to `requirements.txt` to ensure any future developers cloning the repository install it automatically.

## 6. Pydantic-AI Version Compatibility (`output_type` & Model String)
- **Issue**: The application threw a terminal `pydantic_ai.exceptions.UserError: Unknown keyword arguments: 'result_type'` during Agent initialization, crashing the UI instantly. Furthermore, the `google-gla:gemini...` model string was rejected.
- **Cause**: The system downloaded `pydantic-ai` v0.8.1. This version introduced two breaking syntax changes to the `Agent()` setup:
  1. The `model=` keyword was deprecated in favor of a positional argument, and it now strictly expects `gemini-1.5-pro` rather than the `google-gla:` prefix.
  2. The `result_type` parameter was completely renamed to `output_type`.
- **Resolution**:
  - Wrote a custom Python `test_pydantic_ai.py` script to simulate and diagnose the `Agent.__init__` signature using Python's `inspect` module.
  - Refactored `cartographer.py`, `detective.py`, and `auditor.py`.
  - Shifted the Gemini LLM string to the officially supported positional string: `Agent('gemini-1.5-pro')`.
  - Replaced the deprecated `result_type=` kwarg with the new `output_type=` kwarg, satisfying the v0.8.1 engine.

## 7. Git Large File Push Error (HTTP 400)
- **Issue**: While attempting to push the `artifacts/` folder to GitHub, Git threw an `HTTP 400 curl 22 The requested URL returned error: 400` and disconnected the push pipeline.
- **Cause**: The `artifacts/` folder contained a 3.7MB `.webp` verification video. The default Git HTTP post buffer size was too small to handle the large blob transfer over the current TLS connection.
- **Resolution**: 
  - Executed `git config http.postBuffer 524288000` to globally increase the blob limit to 500MB.
  - Successfully pushed the large WebP video asset to the `origin/main` repository alongside the documentation.

## 8. Git `.gitignore` Expansion & Architecture Cleanup
- **Issue**: Project root contained heavy, unnecessary local directories that should never be pushed to enterprise version control.
- **Resolution**:
  - Configured a `.gitignore` to block `/venv`, `/__pycache__/`, and the `.env` credentials file to strictly protect data sovereignty.
  - Migrated `COMMANDS_USED.md` down into the `/artifacts` directory for a cleaner repository root.
  - Updated the `README.md` file tree schema map points to correctly render the new documentation layout.
