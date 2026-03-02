# Sentinel-Graph Implementation Plan

This document outlines the architecture and execution steps for building the "Sentinel-Graph" Agentic Graph-RAG system requested.

## User Review Required
Please review the proposed architecture and agent responsibilities. 
- **Neo4j Instance**: Does the project have an existing Neo4j instance available, or should we assume a local Neo4j Docker container / Neo4j Aura sandbox for development? I will set up the code to use environment variables (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`), so it can easily map to whichever instance you bring.
- **Model Choice**: I will map `pydantic-ai` and `langchain` components to Google's Gemini models (since you mentioned Gemini 3.1 Pro). Ensure you have a valid `GEMINI_API_KEY`.

## Proposed Changes

### Core Infrastructure
#### [NEW] requirements.txt
Add required dependencies:
- `langgraph`
- `langchain-neo4j`
- `neo4j`
- `pydantic-ai`
- `streamlit` (for local dashboard verification and reasoning trace visualization)
- `python-dotenv`
- `langchain-google-genai`

#### Directories
- `src/`: Core logic, Neo4j connection utilities, and dashboard UI.
- `agents/`: Individual agent definitions.
- `knowledge_base/`: Directory for sample documents to test the Cartographer.

### Agent Implementation (`agents/`)
#### [NEW] agents/cartographer.py
**Specialist A (The Cartographer):**
- **Skill**: Document Entity Extraction.
- **Logic**: Reads documents from the knowledge base, extracts Entities (Contracts, Stakeholders, Dates, USD Amounts) and their Relationships using `pydantic-ai` structured outputs.
- **Action**: Maps extracted structured data into nodes and relationships in Neo4j using the Neo4j python driver.

#### [NEW] agents/detective.py
**Specialist B (The Detective):**
- **Skill**: Graph Traversal and Cypher Generation.
- **Logic**: Receives complex audit questions. Explores the graph schema and designs Cypher queries for multi-hop reasoning (e.g., finding hidden connections between entities). Executes queries against Neo4j and formulates findings.

#### [NEW] agents/auditor.py
**Specialist C (The Auditor):**
- **Skill**: Self-RAG Feedback Loop.
- **Logic**: Evaluates the relevance of the results retrieved by The Detective. Calculates a relevance score. If `< 0.85`, it autonomously rewrites the search query and signals a retry to the Detective.

#### [NEW] agents/orchestrator.py
**LangGraph State Machine:**
- Defines the State (`messages`, `query`, `graph_context`, `auditor_score`, `reasoning_trace`).
- Orchestrates the flow: Query -> Detective -> Auditor -> (Retry if fail) -> Generate Final Answer.
- Appends intermediate steps (Agent name, action, output) into a `reasoning_trace` list to expose the thought process.

### Verification (`src/`)
#### [NEW] src/dashboard.py
- A Streamlit interface to input audit questions, visualize the final answer, and display the step-by-step Reasoning Trace.

## Verification Plan
1. **Automated Verification**: We will launch the `dashboard.py` locally.
2. **Browser Subagent**: We will dispatch the Antigravity Browser Agent to interact with the local dashboard, submit a complex multi-hop audit question, verify the output and trace, and record a `.webp` video of the success.
