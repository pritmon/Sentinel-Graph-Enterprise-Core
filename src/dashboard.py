"""
Sentinel-Graph Enterprise Auditor — Streamlit dashboard.

Cloud-ready: on Streamlit Community Cloud the connection settings and API keys come
from st.secrets; locally they come from .env. The secrets→env bridge below MUST run
before the agents are imported, because each Pydantic-AI Agent reads GEMINI_MODEL /
ANTHROPIC_API_KEY from the environment at construction time.
"""

import os
import sys
import ast

import streamlit as st

st.set_page_config(
    page_title="Sentinel-Graph Enterprise Auditor",
    page_icon="🛡️",
    layout="wide",
)

# ── secrets → environment (must precede agent imports) ────────────────────────
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float, bool)):
            os.environ[str(_k)] = str(_v)
except Exception:
    # No secrets.toml (typical when running locally) — fall back to .env below.
    pass

from dotenv import load_dotenv
load_dotenv()  # does not override values already set from st.secrets

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── styling ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      .block-container { padding-top: 2.2rem; max-width: 1200px; }
      .sg-hero {
        background: linear-gradient(120deg, #0b1e3b 0%, #15366b 55%, #1c4e8a 100%);
        border-radius: 16px; padding: 26px 30px; margin-bottom: 18px;
        border: 1px solid rgba(255,255,255,0.08);
      }
      .sg-hero h1 { color: #fff; margin: 0; font-size: 1.9rem; letter-spacing: .3px; }
      .sg-hero p  { color: #b9cbe6; margin: 6px 0 0; font-size: .98rem; }
      .sg-badge {
        display:inline-block; padding:3px 10px; border-radius:999px; font-size:.72rem;
        font-weight:600; letter-spacing:.4px; margin-right:6px;
      }
      .sg-ok   { background:#0f3d2e; color:#4ade80; border:1px solid #166534; }
      .sg-bad  { background:#3d1212; color:#f87171; border:1px solid #7f1d1d; }
      .agent-chip {
        display:inline-block; padding:2px 9px; border-radius:6px; font-size:.74rem;
        font-weight:700; color:#fff; margin-right:8px;
      }
      .a-Detective { background:#2563eb; }
      .a-Auditor   { background:#9333ea; }
      .a-System    { background:#475569; }
      .score-wrap  { background:#1e293b; border-radius:6px; height:10px; width:100%; overflow:hidden; }
      .score-fill  { height:10px; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="sg-hero">
      <h1>🛡️ Sentinel-Graph Enterprise Auditor</h1>
      <p>Autonomous Agentic Graph-RAG — multi-hop Cypher reasoning with a self-correcting audit loop.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── DB helpers (degrade gracefully if Neo4j unreachable) ──────────────────────
def graph_stats():
    """Return (nodes, relationships, label_counts) or None if the DB is unreachable."""
    try:
        from src.utils import execute_query
        nodes = execute_query("MATCH (n) RETURN count(n) AS c")
        rels = execute_query("MATCH ()-[r]->() RETURN count(r) AS c")
        labels = execute_query(
            "MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS c ORDER BY c DESC"
        )
        if nodes is None:
            return None
        return nodes[0]["c"], (rels[0]["c"] if rels else 0), (labels or [])
    except Exception:
        return None


SAMPLE_DOC = """
CLASSIFIED AUDIT REPORT — FRAUD INVESTIGATION FILE #2024-FIN-009

On January 15, 2024, John Doe, CEO of Alpha Corp, signed a shadow contract named
'Project X' valued at $5,000,000 USD with Beta Ltd, a known shell company registered
in the British Virgin Islands with zero employees and no declared business activity.

Beta Ltd was incorporated on March 3, 2019 in the British Virgin Islands, has zero
employees, no declared business activity, beneficial owner John Doe via a nominee, and
a risk score of 0.95 out of 1.0 (high-risk shell company).

Alpha Corp is a legitimate logistics company incorporated in Delaware, USA in 2010,
320 employees, freight forwarding, risk score 0.12.

John Doe also owns Gamma Holdings LLC, a shell company in the Cayman Islands, zero
employees, incorporated June 6, 2021, risk score 0.91. Gamma Holdings LLC is the
beneficial owner of Delta Ventures Ltd, a shell company in Panama, risk score 0.88,
incorporated 2020. Project X is suspected to siphon $5,000,000 from Alpha Corp to
entities controlled by John Doe.
""".strip()

SAMPLE_QUESTIONS = [
    "Which shell companies is John Doe connected to through contracts, and what are their risk scores?",
    "List every company ranked by risk_score, with its jurisdiction.",
    "Who is the beneficial owner of Delta Ventures Ltd, and through which ownership chain?",
    "What is the value and signing date of Project X, and which companies does it involve?",
]

# ── sidebar: status + ingestion ───────────────────────────────────────────────
with st.sidebar:
    st.subheader("⚙️ System Status")
    model = os.getenv("GEMINI_MODEL", "(unset)")
    stats = graph_stats()
    if stats is not None:
        st.markdown(
            f'<span class="sg-badge sg-ok">● NEO4J CONNECTED</span>', unsafe_allow_html=True
        )
        n, r, labels = stats
        c1, c2 = st.columns(2)
        c1.metric("Nodes", n)
        c2.metric("Relationships", r)
        if labels:
            st.caption(" · ".join(f"{x['label']} ({x['c']})" for x in labels))
    else:
        st.markdown(
            f'<span class="sg-badge sg-bad">● NEO4J UNREACHABLE</span>', unsafe_allow_html=True
        )
        st.caption("Set NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD in secrets.")
    st.caption(f"🧠 Reasoning model: `{model}`")

    st.divider()
    st.subheader("🗺️ The Cartographer")
    st.caption("Specialist A — extract entities + properties into Neo4j.")

    if st.button("⚡ Seed sample fraud dataset", use_container_width=True):
        with st.spinner("Ingesting sample document…"):
            try:
                from agents.cartographer import process_document
                res = process_document(SAMPLE_DOC)
                st.success(f"Seeded {len(res.entities)} entities, {len(res.relationships)} relationships.")
                st.rerun()
            except Exception as e:
                st.error(f"Seed failed: {e}")

    new_doc = st.text_area("Or paste your own audit document:", height=140)
    if st.button("Process & Map Entities", use_container_width=True):
        if not new_doc.strip():
            st.warning("Paste a document first.")
        else:
            with st.spinner("Extracting entities and mapping to graph…"):
                try:
                    from agents.cartographer import process_document
                    res = process_document(new_doc)
                    st.success(f"Extracted {len(res.entities)} entities, {len(res.relationships)} relationships.")
                    with st.expander("Extracted payload"):
                        st.json(res.model_dump())
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

# ── main: the audit ───────────────────────────────────────────────────────────
st.subheader("🔍 Run an Audit")
st.caption("Specialist B (Detective) writes Cypher → DB executes → Specialist C (Auditor) grades and may loop.")

if "sg_query" not in st.session_state:
    st.session_state.sg_query = ""

st.write("**Try a sample question:**")
cols = st.columns(2)
for i, q in enumerate(SAMPLE_QUESTIONS):
    if cols[i % 2].button(q, key=f"sample_{i}", use_container_width=True):
        st.session_state.sg_query = q

query = st.text_input(
    "Audit question",
    value=st.session_state.sg_query,
    placeholder="e.g. Which shell companies is the CEO connected to?",
)

run = st.button("▶ Run Audit Trace", type="primary", use_container_width=True)


def render_trace(trace):
    """Render the multi-agent reasoning trace with agent-coloured steps and score bars."""
    for i, step in enumerate(trace, 1):
        agent = step.get("agent", "System")
        action = step.get("action", "")
        st.markdown(
            f'<span class="agent-chip a-{agent}">{agent}</span> '
            f'<b>Step {i} — {action}</b>',
            unsafe_allow_html=True,
        )
        if step.get("query"):
            st.code(step["query"], language="cypher")
        if step.get("reasoning"):
            st.caption(step["reasoning"])
        if "score" in step and isinstance(step.get("score"), (int, float)):
            sc = float(step["score"])
            color = "#4ade80" if sc >= 0.85 else ("#facc15" if sc >= 0.5 else "#f87171")
            st.markdown(
                f'<div class="score-wrap"><div class="score-fill" '
                f'style="width:{sc*100:.0f}%;background:{color};"></div></div>'
                f'<small>relevance score: <b>{sc:.2f}</b> '
                f'(loop-back threshold 0.85)</small>',
                unsafe_allow_html=True,
            )
        if step.get("results"):
            with st.expander("DB results"):
                st.code(step["results"])
        st.divider()


if run:
    if not query.strip():
        st.warning("Enter an audit question.")
    elif graph_stats() is None:
        st.error("Neo4j is unreachable — configure the connection secrets first.")
    else:
        with st.spinner("Running the LangGraph audit workflow…"):
            try:
                from agents.orchestrator import audit_graph
                final = audit_graph.invoke(
                    {"question": query, "retries": 0, "reasoning_trace": []}
                )

                st.markdown("### ✅ Final Audit Answer")
                answer = final.get("final_answer", "No answer generated.")
                # The answer carries a stringified list of result rows; pretty-print if possible.
                payload = answer.split("findings are:", 1)[-1].strip()
                try:
                    st.dataframe(ast.literal_eval(payload), use_container_width=True)
                except Exception:
                    st.info(answer)

                m1, m2 = st.columns(2)
                m1.metric("Detective ↔ Auditor passes", final.get("retries", 0))
                m2.metric("Best relevance", f"{final.get('best_score', 0.0):.2f}")

                st.markdown("### 🧠 Multi-Agent Reasoning Trace")
                render_trace(final.get("reasoning_trace", []))
            except Exception as e:
                st.error(f"Audit failed: {e}")
                st.caption("Check that API keys and the Neo4j connection are configured in secrets.")
