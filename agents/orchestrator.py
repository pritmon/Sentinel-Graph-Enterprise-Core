"""
Agentic Workflow Orchestrator
-------------------------------

This module defines the core LangGraph state machine that governs the Sentinel-Graph system.
It ties together The Detective (Query Generation), the Database (Execution), and
The Auditor (Self-RAG Evaluation) into a robust, autonomous retry loop.
"""

import os
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from agents.detective import analyze_audit_question
from agents.auditor import evaluate_results
from src.utils import execute_query

# ==========================================
# 1. GRAPH STATE DEFINITION
# ==========================================

class GraphState(TypedDict):
    """
    The shared memory structure passed between LangGraph nodes.
    This holds the current context of the audit investigation.
    """
    question: str                  # The original user question
    cypher_query: str              # The latest generated Cypher query
    db_results: str                # The raw JSON results from Neo4j
    relevance_score: float         # The grade assigned by The Auditor
    rewritten_question: str        # The updated question if the previous attempt failed
    retries: int                   # Attempt counter to prevent infinite loops
    reasoning_trace: List[dict]    # The step-by-step audit log shown in the Dashboard
    final_answer: str              # The synthesized final output

# ==========================================
# 2. DEFINE GRAPH NODES (Workflow Steps)
# ==========================================

def generate_cypher(state: GraphState) -> GraphState:
    """
    Node: The Detective (Specialist B) designs the Cypher Query.
    """
    question = state.get("rewritten_question") or state["question"]
    trace = state.get("reasoning_trace", [])
    
    print(f"--- DETECTIVE: Generating Cypher for: '{question}' ---")
    
    result = analyze_audit_question(question)
    
    # Append the action to the audit trace for transparency
    trace.append({
        "agent": "Detective",
        "action": "Generated Cypher",
        "query": result.cypher_query,
        "reasoning": result.reasoning
    })
    
    return {
        "cypher_query": result.cypher_query,
        "reasoning_trace": trace,
        "retries": state.get("retries", 0) + 1
    }

def execute_cypher(state: GraphState) -> GraphState:
    """
    Node: System executes the generated query against the Neo4j Graph.
    """
    query = state["cypher_query"]
    trace = state["reasoning_trace"]
    
    print(f"--- DATABASE: Executing Cypher ---")
    
    # Sanitize the LLM output in case it included markdown blocks (```cypher ... ```)
    clean_query = query.replace("```cypher", "").replace("```", "").strip()
    
    results = execute_query(clean_query)
    str_results = str(results) if results else "No results found."
    
    trace.append({
        "agent": "System",
        "action": "Database Execution",
        "results": str_results
    })
    
    return {"db_results": str_results, "reasoning_trace": trace}

def audit_results(state: GraphState) -> GraphState:
    """
    Node: The Auditor (Specialist C) evaluates the retrieved graph data.
    Implements the Self-RAG (Retrieval-Augmented Generation) feedback loop.
    """
    question = state.get("rewritten_question") or state["question"]
    query = state["cypher_query"]
    results = state["db_results"]
    trace = state["reasoning_trace"]
    
    print(f"--- AUDITOR: Evaluating Results against Original Question ---")
    
    eval_result = evaluate_results(question, query, results)
    
    trace.append({
        "agent": "Auditor",
        "action": "Evaluated Retrieval",
        "score": eval_result.score,
        "reasoning": eval_result.reasoning
    })
    
    return {
        "relevance_score": eval_result.score,
        # If score is failing (< 0.85), store the LLM's suggested rewrite for the next loop
        "rewritten_question": eval_result.rewritten_query if eval_result.score < 0.85 else "",
        "reasoning_trace": trace
    }

def generate_final_answer(state: GraphState) -> GraphState:
    """
    Node: Synthesizes final answer for the user interface.
    """
    results = state["db_results"]
    trace = state["reasoning_trace"]
    
    print(f"--- SYSTEM: Generating Final Answer ---")
    
    # In a production system, another LLM call could be used to write a prose response.
    # For this system, appending the structured results suffices.
    final_ans = f"Based on the audit traversal, the findings are: {results}"
    
    trace.append({
        "agent": "System",
        "action": "Final Output Generation",
        "answer": final_ans
    })
    
    return {"final_answer": final_ans, "reasoning_trace": trace}

# ==========================================
# 3. DEFINE ROUTING LOGIC (Edges)
# ==========================================

def should_retry(state: GraphState) -> str:
    """
    Conditional Edge Router: Decides whether to break the loop or retry.
    """
    score = state.get("relevance_score", 0.0)
    retries = state.get("retries", 0)
    
    if score >= 0.85 or retries >= 3:
        print(f"--- ROUTER: Score {score} passes threshold (or max retries reached). Moving to Final Answer. ---")
        return "generate_final_answer"
    else:
        print(f"--- ROUTER: Score {score} is too low. Sending back to The Detective with rewritten query. ---")
        return "generate_cypher"

# ==========================================
# 4. BUILD AND COMPILE THE GRAPH
# ==========================================

def build_workflow():
    """Compiles the LangGraph state machine workflow."""
    workflow = StateGraph(GraphState)
    
    # Register all functional nodes
    workflow.add_node("generate_cypher", generate_cypher)
    workflow.add_node("execute_cypher", execute_cypher)
    workflow.add_node("audit_results", audit_results)
    workflow.add_node("generate_final_answer", generate_final_answer)
    
    # Define the strict linear sequence of the pipeline
    workflow.set_entry_point("generate_cypher")
    workflow.add_edge("generate_cypher", "execute_cypher")
    workflow.add_edge("execute_cypher", "audit_results")
    
    # Define the conditional loop back mechanism (Self-RAG)
    workflow.add_conditional_edges(
        "audit_results",
        should_retry,
        {
            "generate_cypher": "generate_cypher",
            "generate_final_answer": "generate_final_answer"
        }
    )
    
    workflow.add_edge("generate_final_answer", END)
    
    return workflow.compile()

# Export the compiled graph instance for the Dashboard to use
audit_graph = build_workflow()

if __name__ == "__main__":
    # Internal Unit Test
    test_state = {"question": "Who signed Project X?", "retries": 0, "reasoning_trace": []}
    res = audit_graph.invoke(test_state)
    print("Final State:", res)
