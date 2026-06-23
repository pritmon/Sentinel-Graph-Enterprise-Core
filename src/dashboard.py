"""
The Dashboard
=============

This is the web page people actually see and click on (built with Streamlit).

From here you can load a document into the graph and ask audit questions. Behind
the buttons, it calls the three specialists and shows their step-by-step thinking.

Cloud note: when running on Streamlit Community Cloud the database login and API key
come from "secrets"; when running on your own machine they come from a .env file.
The little secrets→environment bridge below MUST run BEFORE the agents are imported,
because each agent reads those settings the moment it is created.
"""

import os
import sys
import ast

import streamlit as st

# Set up the browser tab (title, icon, wide layout) before anything is drawn.
st.set_page_config(
    page_title="Sentinel-Graph Enterprise Auditor",
    page_icon="🛡️",
    layout="wide",
)


# =============================================================================
# 1. SETTINGS: COPY CLOUD "SECRETS" INTO THE ENVIRONMENT
# =============================================================================
# On the cloud, settings live in st.secrets. The agents expect them as environment
# variables, so we copy them across here — and this has to happen before we import
# the agents further down.
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float, bool)):
            os.environ[str(_k)] = str(_v)
except Exception:
    # No secrets file (the normal case when running locally) — we'll use .env instead.
    pass

from dotenv import load_dotenv
load_dotenv()  # fills in anything not already set from st.secrets

# Let Python find the project's modules (agents/, src/) no matter where we're launched.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# 2. LOOK AND FEEL (the page's colors and styling)
# =============================================================================
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

# The big banner at the top of the page.
st.markdown(
    """
    <div class="sg-hero">
      <h1>🛡️ Sentinel-Graph Enterprise Auditor</h1>
      <p>Autonomous Agentic Graph-RAG — multi-hop Cypher reasoning with a self-correcting audit loop.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# 3. SMALL HELPERS AND SAMPLE CONTENT
# =============================================================================

def graph_stats():
    """
    Peek at the database and count what's inside.

    Returns (number of nodes, number of links, per-label counts), or None if the
    database can't be reached — which lets the page show a friendly status instead
    of an error.
    """
    try:
        from src.utils import execute_query
        nodes  = execute_query("MATCH (n) RETURN count(n) AS c")
        rels   = execute_query("MATCH ()-[r]->() RETURN count(r) AS c")
        labels = execute_query(
            "MATCH (n) UNWIND labels(n) AS l RETURN l AS label, count(*) AS c ORDER BY c DESC"
        )
        if nodes is None:
            return None
        return nodes[0]["c"], (rels[0]["c"] if rels else 0), (labels or [])
    except Exception:
        return None


# A ready-made fraud report used by the "Seed sample" button so a fresh, empty
# database has something interesting to explore right away.
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

# One-click example questions shown as buttons.
SAMPLE_QUESTIONS = [
    "Which shell companies is John Doe connected to through contracts, and what are their risk scores?",
    "List every company ranked by risk_score, with its jurisdiction.",
    "Who is the beneficial owner of Delta Ventures Ltd, and through which ownership chain?",
    "What is the value and signing date of Project X, and which companies does it involve?",
]


# =============================================================================
# 4. THE SIDEBAR: STATUS + LOADING DOCUMENTS
# =============================================================================
with st.sidebar:
    st.subheader("⚙️ System Status")

    # Show whether the database is reachable, plus a quick count of what's inside.
    model = os.getenv("LLM_MODEL", "(unset)")
    stats = graph_stats()
    if stats is not None:
        st.markdown('<span class="sg-badge sg-ok">● NEO4J CONNECTED</span>', unsafe_allow_html=True)
        n, r, labels = stats
        c1, c2 = st.columns(2)
        c1.metric("Nodes", n)
        c2.metric("Relationships", r)
        if labels:
            st.caption(" · ".join(f"{x['label']} ({x['c']})" for x in labels))
    else:
        st.markdown('<span class="sg-badge sg-bad">● NEO4J UNREACHABLE</span>', unsafe_allow_html=True)
        st.caption("Set NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD in secrets.")
    st.caption(f"🧠 Reasoning model: `{model}`")

    st.divider()
    st.subheader("🗺️ The Cartographer")
    st.caption("Specialist A — extract entities + properties into Neo4j.")

    # Button 1: load the built-in sample report.
    if st.button("⚡ Seed sample fraud dataset", use_container_width=True):
        with st.spinner("Ingesting sample document…"):
            try:
                from agents.cartographer import process_document
                res = process_document(SAMPLE_DOC)
                st.success(f"Seeded {len(res.entities)} entities, {len(res.relationships)} relationships.")
                st.rerun()  # refresh so the new counts show up
            except Exception as e:
                st.error(f"Seed failed: {e}")

    # Button 2: load whatever document the user pastes in.
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


# =============================================================================
# 5. THE MAIN AREA: ASK A QUESTION
# =============================================================================
st.subheader("🔍 Run an Audit")
with st.expander("ℹ️ How this works (3 AI specialists)"):
    st.markdown(
        "1. **🕵️ The Detective** turns your question into a database query.\n"
        "2. **💾 The Database** runs that query and returns matching records.\n"
        "3. **⚖️ The Auditor** checks the answer. If it's good (score ≥ 0.85) you get the result; "
        "if not, it sends the Detective back to try again (up to 3 times).\n\n"
        "The steps below show exactly what each specialist did."
    )

# Remember the chosen question between clicks.
if "sg_query" not in st.session_state:
    st.session_state.sg_query = ""

# Show the example questions as a two-column grid of buttons.
st.write("**Try a sample question:**")
cols = st.columns(2)
for i, q in enumerate(SAMPLE_QUESTIONS):
    if cols[i % 2].button(q, key=f"sample_{i}", use_container_width=True):
        st.session_state.sg_query = q

# The free-text box (pre-filled if a sample button was clicked) and the run button.
query = st.text_input(
    "Audit question",
    value=st.session_state.sg_query,
    placeholder="e.g. Which shell companies is the CEO connected to?",
)

run = st.button("▶ Run Audit Trace", type="primary", use_container_width=True)


def _row_count(results_text):
    """Best-effort count of how many records the database returned, from its text form."""
    if not results_text or results_text == "No results found.":
        return 0
    if results_text.startswith("CYPHER_ERROR"):
        return None  # signals an error, not a count
    try:
        data = ast.literal_eval(results_text)
        return len(data) if isinstance(data, list) else 1
    except Exception:
        return None


def render_trace(trace):
    """
    Tell the step-by-step story in plain language.

    Each specialist gets a colored tag and a one-line summary of what it did, so the
    reader can follow the flow without reading raw query output.
    """
    for step in trace:
        agent  = step.get("agent", "System")
        action = step.get("action", "")

        # ── The Detective wrote a query ──────────────────────────────────────
        if action == "Generated Cypher":
            st.markdown(
                '<span class="agent-chip a-Detective">Detective</span> '
                '<b>wrote a database query</b>', unsafe_allow_html=True)
            st.code(step.get("query", ""), language="cypher")
            if step.get("reasoning"):
                with st.expander("Why it wrote this query"):
                    st.write(step["reasoning"])

        # ── The database ran it ──────────────────────────────────────────────
        elif action == "Database Execution":
            results = step.get("results", "")
            count   = _row_count(results)
            if count is None:
                st.markdown(
                    '<span class="agent-chip a-System">Database</span> '
                    '<b>⚠️ the query had an error</b>', unsafe_allow_html=True)
            elif count == 0:
                st.markdown(
                    '<span class="agent-chip a-System">Database</span> '
                    '<b>returned 0 matching records</b>', unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<span class="agent-chip a-System">Database</span> '
                    f'<b>returned {count} matching record(s)</b>', unsafe_allow_html=True)
                try:
                    st.dataframe(ast.literal_eval(results), use_container_width=True)
                except Exception:
                    st.code(results)

        # ── The Auditor graded it ────────────────────────────────────────────
        elif action == "Evaluated Retrieval":
            sc      = float(step.get("score", 0.0))
            passed  = sc >= 0.85
            color   = "#4ade80" if passed else ("#facc15" if sc >= 0.5 else "#f87171")
            verdict = "✅ good enough — accepted" if passed else "↩︎ below 0.85 — sending the Detective back to try again"
            st.markdown(
                f'<span class="agent-chip a-Auditor">Auditor</span> '
                f'<b>graded the answer: {sc:.2f}</b> &nbsp; {verdict}', unsafe_allow_html=True)
            st.markdown(
                f'<div class="score-wrap"><div class="score-fill" '
                f'style="width:{sc*100:.0f}%;background:{color};"></div></div>',
                unsafe_allow_html=True)
            if step.get("reasoning"):
                with st.expander("Auditor's notes"):
                    st.write(step["reasoning"])

        # The final-answer step is already shown up top, so skip it (and anything unknown).
        else:
            continue

        st.divider()


# When the run button is pressed, do the checks, then run the full workflow.
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

                # The headline answer. It arrives as text holding a list of rows, so we
                # try to show it as a neat table and fall back to plain text if needed.
                st.markdown("### ✅ Final Answer")
                answer  = final.get("final_answer", "No answer generated.")
                payload = answer.split("findings are:", 1)[-1].strip()

                rows = None
                try:
                    parsed = ast.literal_eval(payload)
                    rows = parsed if isinstance(parsed, list) else None
                except Exception:
                    pass

                if rows:
                    st.success(f"Found {len(rows)} matching record(s):")
                    st.dataframe(rows, use_container_width=True)
                elif rows == []:
                    st.warning("No matching records were found for this question.")
                else:
                    st.info(answer)

                # Two plain-language stats: how many tries it took, and how confident it was.
                attempts   = final.get("retries", 0)
                confidence = final.get("best_score", 0.0)
                m1, m2 = st.columns(2)
                m1.metric("Attempts", attempts, help="How many times the Detective↔Auditor loop ran (max 3).")
                m2.metric("Confidence", f"{confidence:.0%}", help="The Auditor's grade for the answer (≥85% passes).")

                # The full behind-the-scenes story, in plain language.
                st.markdown("### 🧠 What each specialist did")
                render_trace(final.get("reasoning_trace", []))
            except Exception as e:
                st.error(f"Audit failed: {e}")
                st.caption("Check that API keys and the Neo4j connection are configured in secrets.")
