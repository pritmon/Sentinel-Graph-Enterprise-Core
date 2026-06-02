"""
Live end-to-end test: real LLM (Claude Haiku) + real Neo4j.
Run with: source venv/bin/activate && export $(grep -v '^#' .env | xargs) && python run_live_test.py
"""

import os, sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("[ERROR] ANTHROPIC_API_KEY not set.")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("SENTINEL-GRAPH LIVE END-TO-END TEST")
print("Model :", os.getenv("GEMINI_MODEL"))
print("Neo4j :", os.getenv("NEO4J_URI"))
print("=" * 60)

# ── 1. Cartographer ───────────────────────────────────────────
print("\n[1/2] CARTOGRAPHER — Ingest enriched document into Neo4j")

from agents.cartographer import process_document

doc = """
CLASSIFIED AUDIT REPORT — FRAUD INVESTIGATION FILE #2024-FIN-009

On January 15, 2024, John Doe, CEO of Alpha Corp, signed a shadow contract
named 'Project X' valued at $5,000,000 USD with Beta Ltd, a known shell company
registered in the British Virgin Islands with zero employees and no declared
business activity.

Beta Ltd is a shell company incorporated on March 3, 2019 in the jurisdiction
of British Virgin Islands. It has zero employees, no declared business activity,
and its beneficial owner is listed as John Doe via a nominee arrangement.
Beta Ltd's registered address is: Suite 4B, Offshore House, Road Town, Tortola, BVI.
Beta Ltd has a risk score of 0.95 out of 1.0, flagged as high-risk shell company.

Alpha Corp is a legitimate logistics company incorporated in Delaware, USA in 2010,
with 320 employees and primary business activity in freight forwarding.
Alpha Corp's risk score is 0.12.

John Doe has a history of signing contracts with offshore entities. He also
owns Gamma Holdings LLC, another shell company registered in the Cayman Islands
with zero employees, incorporated on June 6, 2021, risk score 0.91, and no
declared business activity. Gamma Holdings LLC is the beneficial owner of Delta
Ventures Ltd, a shell company in Panama, risk score 0.88, incorporated 2020.

All three shell companies (Beta Ltd, Gamma Holdings LLC, Delta Ventures Ltd)
are connected to John Doe either directly or through ownership chains.
Project X contract is suspected to be a mechanism for siphoning $5,000,000
from Alpha Corp to entities controlled by John Doe.
"""

result = process_document(doc)

print(f"  Entities extracted    : {len(result.entities)}")
for e in result.entities:
    print(f"    [{e.type:10s}] {e.name}")
print(f"  Relationships extracted: {len(result.relationships)}")
for r in result.relationships:
    print(f"    {r.source} --[{r.relation_type}]--> {r.target}")

# ── 2. Full orchestrator audit trace ──────────────────────────
print("\n[2/2] ORCHESTRATOR — Full audit trace (Detective + Auditor loop)")

from agents.orchestrator import build_workflow

graph = build_workflow()
state = {
    "question": "Which shell companies is John Doe connected to through contracts, and what are their jurisdictions and risk scores?",
    "retries": 0,
    "reasoning_trace": [],
}

final = graph.invoke(state)

print(f"\n  Final Answer:\n    {final['final_answer']}")
print(f"\n  Reasoning Trace ({len(final['reasoning_trace'])} steps):")
for step in final["reasoning_trace"]:
    detail = step.get("query") or step.get("results") or step.get("score") or step.get("answer") or ""
    if isinstance(detail, str) and len(detail) > 100:
        detail = detail[:100] + "..."
    print(f"    [{step['agent']:10s}] {step['action']}: {detail}")

print("\n" + "=" * 60)
print("LIVE TEST COMPLETE")
print("=" * 60)
