"""
The Orchestrator
================

This is the conductor that makes the three specialists work together.

It runs a simple, repeating loop:

    Detective writes a query  ->  Database runs it  ->  Auditor grades the result

If the Auditor is happy (or we've tried enough times), we stop and report the answer.
If not, the Auditor's rewritten question is sent back to the Detective for another try.
LangGraph handles the wiring of these steps and the loop-back.
"""

from typing import TypedDict, List

from langgraph.graph import StateGraph, END

from agents.detective import analyze_audit_question
from agents.auditor import evaluate_results
from src.utils import execute_query


# =============================================================================
# 1. THE SHARED NOTEPAD
# =============================================================================
# Every step reads from and writes to this single shared dictionary. It's the
# "memory" that travels through the loop, carrying everything we've learned so far.

class GraphState(TypedDict):
    """The shared memory passed between every step of the workflow."""

    question:        str         # The original user question
    cypher_query:    str         # The latest query the Detective wrote
    db_results:      str         # What the database returned for that query
    relevance_score: float       # The Auditor's grade for the latest attempt
    rewritten_question: str      # A clearer question to retry with, if needed
    retries:         int         # How many attempts we've made (stops endless loops)
    reasoning_trace: List[dict]  # A running log of every step, shown in the dashboard
    best_results:    str         # The best good answer seen across all attempts
    best_score:      float       # The grade that came with best_results
    final_answer:    str         # The finished answer we hand back


# =============================================================================
# 2. THE STEPS OF THE LOOP
# =============================================================================

def generate_cypher(state: GraphState) -> GraphState:
    """Step 1 — The Detective writes a database query for the question."""
    # Use the rewritten question if a previous round produced one, else the original.
    question = state.get("rewritten_question") or state["question"]
    trace    = state.get("reasoning_trace", [])

    print(f"--- DETECTIVE: Generating Cypher for: '{question}' ---")

    result = analyze_audit_question(question)

    # Jot this step down in the log so the dashboard can show the full story.
    trace.append({
        "agent":     "Detective",
        "action":    "Generated Cypher",
        "query":     result.cypher_query,
        "reasoning": result.reasoning,
    })

    return {
        "cypher_query":    result.cypher_query,
        "reasoning_trace": trace,
        "retries":         state.get("retries", 0) + 1,
    }


def execute_cypher(state: GraphState) -> GraphState:
    """Step 2 — Run the Detective's query against the Neo4j database."""
    query = state["cypher_query"]
    trace = state["reasoning_trace"]

    print("--- DATABASE: Executing Cypher ---")

    # The AI sometimes wraps its query in ```cypher fences — strip those off.
    clean_query = query.replace("```cypher", "").replace("```", "").strip()

    # Run it, then describe the outcome in three clear cases: error, empty, or data.
    results = execute_query(clean_query)
    if results is None:
        str_results = f"CYPHER_ERROR: Query failed to execute. The query may have a syntax error or reference non-existent properties. Query was: {clean_query}"
    elif len(results) == 0:
        str_results = "No results found."
    else:
        str_results = str(results)

    trace.append({
        "agent":   "System",
        "action":  "Database Execution",
        "results": str_results,
    })

    return {"db_results": str_results, "reasoning_trace": trace}


def audit_results(state: GraphState) -> GraphState:
    """Step 3 — The Auditor grades the result and decides if a retry is worth it."""
    question = state.get("rewritten_question") or state["question"]
    query    = state["cypher_query"]
    results  = state["db_results"]
    trace    = state["reasoning_trace"]

    print("--- AUDITOR: Evaluating Results against Original Question ---")

    eval_result = evaluate_results(question, query, results)

    trace.append({
        "agent":     "Auditor",
        "action":    "Evaluated Retrieval",
        "score":     eval_result.score,
        "reasoning": eval_result.reasoning,
    })

    # Remember the best *usable* answer so far. A later attempt that errors out or comes
    # back empty must never be allowed to overwrite a good answer we already found.
    best_results = state.get("best_results", "")
    best_score   = state.get("best_score", -1.0)
    is_usable    = bool(results) and not results.startswith("CYPHER_ERROR") and results != "No results found."
    if is_usable and eval_result.score > best_score:
        best_results = results
        best_score   = eval_result.score

    return {
        "relevance_score": eval_result.score,
        # Keep the rewritten question only when the grade was too low (we'll retry with it).
        "rewritten_question": eval_result.rewritten_query if eval_result.score < 0.85 else "",
        "reasoning_trace": trace,
        "best_results":    best_results,
        "best_score":      best_score,
    }


def generate_final_answer(state: GraphState) -> GraphState:
    """Step 4 — Wrap up: report the best answer we gathered along the way."""
    # Prefer the best good answer from any attempt; only fall back to the latest raw
    # result if no attempt ever produced something usable.
    results = state.get("best_results") or state["db_results"]
    trace   = state["reasoning_trace"]

    print("--- SYSTEM: Generating Final Answer ---")

    # A fuller system might have an AI rewrite this into prose; here the data speaks.
    final_ans = f"Based on the audit traversal, the findings are: {results}"

    trace.append({
        "agent":  "System",
        "action": "Final Output Generation",
        "answer": final_ans,
    })

    return {"final_answer": final_ans, "reasoning_trace": trace}


# =============================================================================
# 3. THE DECISION: STOP OR TRY AGAIN?
# =============================================================================

def should_retry(state: GraphState) -> str:
    """After grading, pick the next step: finish up, or loop back to the Detective."""
    score   = state.get("relevance_score", 0.0)
    retries = state.get("retries", 0)

    # Good enough (0.85+) OR we've already tried 3 times → stop and report.
    if score >= 0.85 or retries >= 3:
        print(f"--- ROUTER: Score {score} passes threshold (or max retries reached). Moving to Final Answer. ---")
        return "generate_final_answer"

    # Otherwise, go around again with the Auditor's clearer question.
    print(f"--- ROUTER: Score {score} is too low. Sending back to The Detective with rewritten query. ---")
    return "generate_cypher"


# =============================================================================
# 4. WIRING THE STEPS TOGETHER
# =============================================================================

def build_workflow():
    """Connect the four steps into a loop and hand back the ready-to-run workflow."""
    workflow = StateGraph(GraphState)

    # Register each step as a node in the graph.
    workflow.add_node("generate_cypher",       generate_cypher)
    workflow.add_node("execute_cypher",        execute_cypher)
    workflow.add_node("audit_results",         audit_results)
    workflow.add_node("generate_final_answer", generate_final_answer)

    # The straight-line part: write -> run -> grade.
    workflow.set_entry_point("generate_cypher")
    workflow.add_edge("generate_cypher", "execute_cypher")
    workflow.add_edge("execute_cypher",  "audit_results")

    # The loop-back part: after grading, should_retry() picks where to go next.
    workflow.add_conditional_edges(
        "audit_results",
        should_retry,
        {
            "generate_cypher":       "generate_cypher",
            "generate_final_answer": "generate_final_answer",
        },
    )

    # Finishing the answer ends the run.
    workflow.add_edge("generate_final_answer", END)

    return workflow.compile()


# The ready-to-use workflow the dashboard imports and runs.
audit_graph = build_workflow()


if __name__ == "__main__":
    # A tiny manual check you can run with `python agents/orchestrator.py`.
    test_state = {"question": "Who signed Project X?", "retries": 0, "reasoning_trace": []}
    res = audit_graph.invoke(test_state)
    print("Final State:", res)
