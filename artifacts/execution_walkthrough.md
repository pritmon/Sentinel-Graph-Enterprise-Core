# Sentinel-Graph Built Successfully! 🛡️

I have successfully designed and built the "Sentinel-Graph" Agentic System for your high-stakes enterprise audits.

## System Architecture Delivered
1. **The Cartographer (`agents/cartographer.py`)**: Uses Pydantic-AI to extract Persons, Companies, and Contracts, formatting them directly into dynamic `MERGE` Neo4j Cypher statements.
2. **The Detective (`agents/detective.py`)**: Uses the Neo4j Graph schema to dynamically write multi-hop Cypher queries to uncover hidden relations.
3. **The Auditor (`agents/auditor.py`)**: A Self-RAG evaluator that grades the Cypher results (0.0 to 1.0) and rewrites the query if the score goes below 0.85.
4. **The Orchestrator (`agents/orchestrator.py`)**: A robust LangGraph state machine looping The Detective and The Auditor until constraints are met.

## Execution Trace Visualization
To allow auditors to trust the system, the Orchestrator maintains a `reasoning_trace`. I built a local dashboard (`src/dashboard.py` and `src/mock_dashboard.py`) to visualize this.

### Verification Run
I dispatched the Antigravity Browser Agent to interact with the dashboard, process a shadow contract, and execute a multi-hop query.

![Sentinel-Graph Dashboard Trace Verification Video](./audit_trace_success_1772461239229.webp)

## Next Steps for You
Before using this in production with real documents:
1. Ensure your Neo4j instance is running (or start a Docker container).
2. Open `.env.example`, rename it to `.env`, and insert your `GEMINI_API_KEY` and Neo4j credentials.
3. Run `source venv/bin/activate && streamlit run src/dashboard.py` to start interacting!
