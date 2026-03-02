# Sentinel-Graph Agentic Auditor 🛡️

Sentinel-Graph is a high-stakes Agentic Graph-RAG system designed for multi-million dollar enterprise audits. It utilizes a multi-agent orchestration pattern to ingest complex documents, dynamically navigate an Enterprise Knowledge Graph (Neo4j), and perform self-correcting logic loops to uncover hidden fraud or contract discrepancies.

## Key Features
- **Multi-Hop Reasoning**: Traverses complex graphs to find indirect connections (e.g., Person -> Contract -> Shell Company).
- **Self-RAG Evaluator**: Autonomously grades its own retrieval results and rewrites queries if it detects hallucinations or gaps in data.
- **Agentic Cartography**: Converts unstructured text into structured Neo4j Graph entities dynamically.

## Project Structure

```text
Sentinel-Graph-Enterprise-Core/
├── agents/                     # LangGraph Multi-Agent Definitions
│   ├── cartographer.py       # Specialist A: Converts text to Neo4j Entities
│   ├── detective.py          # Specialist B: Translates questions into Cypher
│   ├── auditor.py            # Specialist C: Self-RAG evaluator for results
│   └── orchestrator.py       # The StateGraph workflow tying agents together
├── src/                        # Core UI and Database bridges
│   ├── utils.py              # Neo4j connection handling
│   ├── dashboard.py          # Streamlit UI for Audit Verification
│   └── mock_dashboard.py     # Demo Streamlit UI for CI/CD Browser Testing
├── knowledge_base/             # Directory for sample raw documents
├── .env.example                # Template for DB and API Key credentials
├── requirements.txt            # Python dependencies (LangGraph, Neo4j, etc.)
├── README.md                   # This document
└── COMMANDS_USED.md            # History of commands used to initialize project
```

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/pritmon/Sentinel-Graph-Enterprise-Core.git
   cd Sentinel-Graph-Enterprise-Core
   ```

2. **Initialize the Virtual Environment & Dependencies:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   Rename `.env.example` to `.env` and fill in:
   - `GEMINI_API_KEY`: Your Google Gemini API Key.
   - `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`: Your Neo4j Database credentials (local, Docker, or Aura).

4. **Launch the Verification Dashboard:**
   ```bash
   streamlit run src/dashboard.py
   ```

## Agent Roles
1. **The Cartographer**: Navigates the `knowledge_base/` and uses Pydantic-AI to extract `Entities` (e.g., Persons, Companies) and `Relationships` (e.g., OWNS, SIGNED), mapping them directly into the Neo4j schema.
2. **The Detective**: Exposed to the live Neo4j schema, this agent writes complex Cypher queries to answer the auditor's high-level questions.
3. **The Auditor**: Grades the retrieved Neo4j data against the user's intent. If the score $< 0.85$, it autonomously restructures the query to force The Detective to try a different graph traversal path.
