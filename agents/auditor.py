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
        "You are Specialist C: The Auditor — a fair, practical quality checker for a graph "
        "database Q&A system. Judge ONE thing: do the retrieved results correctly and directly "
        "answer the SPECIFIC question that was asked?\n"
        "SCORING RULES:\n"
        "- If the results contain the facts that answer the question, score HIGH (0.85–1.0). "
        "A correct, on-topic answer is a GOOD answer even if it is short or a single row. "
        "One row that fully answers the question deserves ~0.95.\n"
        "- Do NOT demand extra details the user did not ask for (dates, history, deeper ownership "
        "chains, counts, 'context', 'pathway transparency'). Judge only against what was asked.\n"
        "- Score LOW (below 0.85) ONLY when the results are empty, contain an error, are clearly "
        "off-topic, or genuinely miss something the question EXPLICITLY requested. When you score "
        "low, rewrite the question to be clearer so the next query can succeed.\n"
        "Be decisive and avoid perfectionism — retries cost time, so only send back for another "
        "attempt when the answer is truly inadequate, not merely improvable."
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
    Do these results answer the question that was actually asked? If yes, score 0.85–1.0
    (a correct answer, even a single row, is a good answer). Score below 0.85 only if the
    results are empty, errored, off-topic, or miss something the question explicitly asked
    for — and if so, suggest a clearer rewritten question.
    """

    # Run the grading and hand back the structured report card.
    result = auditor_agent.run_sync(prompt)
    return result.output
