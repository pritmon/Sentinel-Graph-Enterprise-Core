<div align="center">
  
# 🛡️ Sentinel-Graph Enterprise Core
**Autonomous Agentic Graph-RAG for High-Stakes Financial Audits**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/release/python-390/)
[![Neo4j](https://img.shields.io/badge/Neo4j-Graph_Database-4d7fc1.svg)](https://neo4j.com/)
[![Gemini](https://img.shields.io/badge/Google_AI-Gemini_2.5_Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg)](https://streamlit.io/)
[![Pydantic-AI](https://img.shields.io/badge/Pydantic--AI-v0.8.x-purple.svg)](https://ai.pydantic.dev/)

*Navigate complex enterprise data using Agentic Multi-Hop reasoning and Self-refining RAG loops.*

---

</div>

## 📌 Executive Summary
Sentinel-Graph is a next-generation orchestration system designed for multi-million dollar enterprise audits. It utilizes a **Multi-Agent StateGraph architecture** to ingest complex financial documents, dynamically navigate an Enterprise Knowledge Graph (Neo4j), and perform self-correcting logic loops to uncover hidden corporate fraud or contract discrepancies.

## 🏗️ 2026 Technology Stack
The Sentinel-Graph Core is built on a modern, ultra-fast agentic framework:
- **Orchestration Engine**: [LangGraph](https://langchain-ai.github.io/langgraph/) - Manages the state machine and cyclical agent loops.
- **Agent Intelligence**: [Pydantic-AI (v0.8.x)](https://ai.pydantic.dev/) - Enforces strict JSON output schemas (`AgentRunResult.output`) to guarantee deterministic agent responses.
- **LLM Foundation**: [Google Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/) - Provides lightning-fast, high-quota multi-hop reasoning.
- **Knowledge Graph**: [Neo4j](https://neo4j.com/) - Stores unstructured test as structured Nodes and Relationships for multi-hop Cypher traversal.
- **User Interface**: [Streamlit](https://streamlit.io/) - Renders live interactive reasoning traces for human-in-the-loop verification.

---

## 🤖 The Multi-Agent Architecture
The system consists of three distinct AI Specialists operating within a continuous LangGraph loop.

### 1. `Specialist A:` The Cartographer (`agents/cartographer.py`)
- **Role**: Data Ingestion & Entity Mapping.
- **Function**: Ingests raw text (e.g., hidden logistic contracts) and uses Pydantic-AI to extract Persons, Companies, Contracts, Dates, and USD Amounts. It immediately persists these entities and their semantic relationships (`OWNED_BY`, `SIGNED`, `VALUED_AT`) directly into the Neo4j database using dynamic, parameterized Cypher `MERGE` commands.

### 2. `Specialist B:` The Detective (`agents/detective.py`)
- **Role**: Multi-Hop Traversal Graph Queries.
- **Function**: Translates natural language audit questions into highly optimized Neo4j Cypher queries. The Detective is actively grounded against the live Neo4j database schema, virtually eliminating hallucinations.

### 3. `Specialist C:` The Auditor (`agents/auditor.py`)
- **Role**: Self-RAG Quality Assurance layer.
- **Function**: Evaluates the data retrieved by The Detective. It scores the relevance from `0.0` to `1.0`. If the score falls below `0.85%`, The Auditor dynamically rewrites the original question and forces the LangGraph state machine to loop back to The Detective for a retry.

---

## 📂 Repository Structure

```text
Sentinel-Graph-Enterprise-Core/
├── agents/                     # LangGraph Multi-Agent Definitions
│   ├── cartographer.py         # Configures Specialist A
│   ├── detective.py            # Configures Specialist B
│   ├── auditor.py              # Configures Specialist C
│   └── orchestrator.py         # The LangGraph workflow connecting the agents
├── src/                        # Core Application Layer
│   ├── utils.py                # Parameterized Neo4j connection logic
│   └── dashboard.py            # Live Streamlit UI & Trace Visualizer
├── artifacts/                  # System documentation and execution walkthroughs
│   ├── deployment_fixes.md     # Engineering log of Pydantic and Quota bug resolutions
│   └── execution_walkthrough.md# Final Graph-RAG visual proofs
├── .env                        # Local database and API Key credentials (Gitignored)
├── requirements.txt            # Locked Python dependencies
└── README.md                   # This document
```

---

## ⚙️ Setup & Deployment

1. **Clone the Enterprise Repository:**
   ```bash
   git clone https://github.com/pritmon/Sentinel-Graph-Enterprise-Core.git
   cd Sentinel-Graph-Enterprise-Core
   ```

2. **Initialize Isolated Environment:**
   Run the standard bootstrapping commands to isolate dependencies.
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure the Authentication `.env`:**
   Generate the required `.env` file containing your cloud or local Neo4j instance strings, and Google AI Studio key.
   ```env
   # .env
   GEMINI_MODEL=gemini-2.5-flash
   GEMINI_API_KEY=AIzaSy...
   GOOGLE_API_KEY=AIzaSy...
   
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=password
   ```

4. **Launch the Sentinel Dashboard:**
   Boot up the live audit tracing interface.
   ```bash
   streamlit run src/dashboard.py
   ```
