"""
Specialist C: The Auditor
=========================

The Auditor is the quality checker.

After the Detective fetches some data, the Auditor looks at it and asks: "Does this
actually answer the question?" It gives a score from 0.0 (useless) to 1.0 (perfect).
If the score is too low, it also rewrites the question more clearly so the Detective
can try again and do better next time. This back-and-forth is the "self-correcting"
part of the system.
"""

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent


# =============================================================================
# 1. THE SHAPE OF THE DATA WE WANT BACK
# =============================================================================

class AuditEval(BaseModel):
    """The Auditor's report card for one attempt."""

    score:           float = Field(description="Relevance score between 0.0 and 1.0. 1.0 means perfect relevance to the user's audit question.")
    reasoning:       str   = Field(description="Explanation of why the score was assigned, pointing out missing data if applicable.")
    rewritten_query: str   = Field(description="If score < 0.85, a suggested rewritten audit question to yield better Graph connections. Empty if score is high enough.")


# =============================================================================
# 2. THE AI AGENT ITSELF
# =============================================================================

auditor_agent = Agent(
    os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'),
    output_type=AuditEval,
    system_prompt=(
        "You are Specialist C: The Auditor. "
        "Your role is to act as a rigorous Self-RAG evaluator for an Agentic Graph-RAG system. "
        "You will be given the original audit question, the Cypher query generated, and the results from the Neo4j Graph. "
        "Score the relevance and completeness of the retrieved facts from 0.0 to 1.0. "
        "If the score is < 0.85, you must autonomously rewrite the original question to be more explicit or structured to help The Detective generate a better query next time."
    )
)


# =============================================================================
# 3. GRADING ONE ATTEMPT
# =============================================================================

def evaluate_results(original_question: str, cypher_query: str, neo4j_results: str) -> AuditEval:
    """
    Show the AI three things — the question, the query that was run, and the data it
    returned — and ask it to grade how well they fit together.

    Returns the score, the reasoning, and (if needed) a rewritten question for a retry.
    """
    prompt = f"""
    Original Audit Question: {original_question}
    Generated Cypher Query: {cypher_query}
    Retrieved Results: {neo4j_results}

    Instructions:
    Evaluate if these retrieved results comprehensively answer the audit question.
    Assign a score. Provide reasoning. If the score is low, suggest a rewritten question.
    """

    # Run the grading and hand back the structured report card.
    result = auditor_agent.run_sync(prompt)
    return result.output
