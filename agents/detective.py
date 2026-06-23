"""
Specialist B: The Detective
===========================

The Detective answers questions about the graph.

You give it a plain-English question ("Which companies are risky?") and it writes
the matching database query (Cypher) to dig up the answer. Before writing anything,
it peeks at the live database to learn what labels, links, and properties actually
exist — so it asks for real data instead of guessing.
"""

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv

# Pull secrets (API keys, database login) out of the .env file into the environment.
load_dotenv()


# =============================================================================
# 1. LOOK AT THE LIVE DATABASE FIRST
# =============================================================================

def get_graph_schema() -> str:
    """
    Build a short "cheat sheet" describing what's actually in the database right now.

    It lists the node labels, the link types, the property names, plus a few real
    examples. Handing this to the AI keeps its queries grounded in reality (no APOC
    plugin needed — just built-in Cypher calls).
    """
    from src.utils import execute_query
    try:
        # The three basic lists: what kinds of nodes, links, and properties exist.
        node_labels = execute_query("CALL db.labels() YIELD label RETURN collect(label) AS labels")
        rel_types   = execute_query("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS types")
        prop_keys   = execute_query("CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS keys")

        # A few real links so the AI sees true source -> type -> target shapes.
        samples = execute_query("""
            MATCH (a)-[r]->(b)
            RETURN DISTINCT labels(a)[0] AS from_label, type(r) AS rel_type, labels(b)[0] AS to_label
            LIMIT 40
        """)

        # One real node per label so the AI sees which properties truly exist
        # (e.g. that a Company carries a numeric risk_score) and reads them, not guesses.
        prop_samples = execute_query("""
            MATCH (n)
            WITH labels(n)[0] AS label, properties(n) AS props
            WITH label, collect(props)[0] AS example
            RETURN label, example
        """)

        # Pull the plain lists out of the query results (or fall back to empty).
        labels = node_labels[0]["labels"] if node_labels else []
        types  = rel_types[0]["types"]    if rel_types   else []
        keys   = prop_keys[0]["keys"]     if prop_keys   else []

        # Turn the raw samples into easy-to-read lines for the AI to read.
        sample_lines = "\n".join(
            f"  (:{s['from_label']})-[:{s['rel_type']}]->(:{s['to_label']})"
            for s in (samples or [])
        )
        prop_lines = "\n".join(
            f"  (:{p['label']}) properties → {p['example']}"
            for p in (prop_samples or [])
        )

        return (
            f"Node Labels : {labels}\n"
            f"Relationship Types: {types}\n"
            f"Property Keys: {keys}\n"
            f"Example node properties per label (use these real property names directly):\n{prop_lines}\n"
            f"Existing relationship patterns in database:\n{sample_lines}"
        )
    except Exception as e:
        # If the database is unreachable, hand back a note instead of crashing.
        return f"[WARNING] Could not retrieve schema: {str(e)}"


# =============================================================================
# 2. THE SHAPE OF THE DATA WE WANT BACK
# =============================================================================

class QueryResult(BaseModel):
    """What the Detective returns: the query to run, plus why it wrote it that way."""

    cypher_query: str = Field(description="The executable Neo4j Cypher query generated to directly answer the audit question.")
    reasoning:    str = Field(description="A step-by-step explanation of the multi-hop traversal strategy used in the query.")


# =============================================================================
# 3. THE AI AGENT ITSELF
# =============================================================================
# The long house-rules below are hard-won lessons: each numbered rule prevents a
# specific kind of broken query the AI used to write.

detective_agent = Agent(
    os.environ.get('LLM_MODEL', 'anthropic:claude-haiku-4-5'),
    output_type=QueryResult,
    system_prompt=(
        "You are Specialist B: The Detective. "
        "Your role is to translate complex enterprise audit questions into Neo4j Cypher queries. "
        "You specialize in multi-hop reasoning. For example, finding indirect connections between "
        "a Person and a Company through shared Contracts or Assets. "
        "Always review the provided Neo4j Graph schema to ensure your queries use the correct node labels "
        "and relationship types (typically UPPER_SNAKE_CASE).\n\n"
        "STRICT CYPHER SYNTAX RULES — violations cause runtime errors:\n"
        "1. Never use WHERE after OPTIONAL MATCH without a node/relationship pattern on the same clause. "
        "   Instead use WITH to carry results forward before filtering: "
        "   OPTIONAL MATCH (n)-[r]->(m) WITH n,m WHERE m IS NOT NULL RETURN n\n"
        "2. Only query properties that exist in the provided schema. "
        "   Never invent property names like 'is_shell_company' unless they appear in the schema.\n"
        "3. Every MATCH/OPTIONAL MATCH must have a RETURN or be followed by WITH before the next clause.\n"
        "4. Do NOT include markdown formatting (```cypher) in cypher_query — raw Cypher only.\n"
        "5. Keep queries simple and focused. Use at most 3 OPTIONAL MATCH clauses per query. "
        "   Never use COLLECT inside a WITH that feeds another COLLECT. "
        "   Prefer multiple simple MATCH patterns over one giant query.\n"
        "6. Never use list comprehensions ([x IN list WHERE ...]) inside a RETURN that also has aggregations.\n"
        "7. When results are empty, broaden the MATCH pattern — do not add more OPTIONAL MATCH clauses.\n"
        "8. Do NOT use UNION. Express the whole answer as one MATCH plus OPTIONAL MATCH clauses with a "
        "single RETURN. UNION branches with mismatched return columns are a common runtime error here.\n"
        "9. GROUND ALL FACTS IN STORED PROPERTIES. Risk is stored as a numeric `risk_score` property "
        "(0.0–1.0, higher = riskier) on Company nodes. To assess or rank risk, RETURN the actual "
        "`risk_score` property — and likewise read jurisdiction, value_usd, employee_count, etc. from "
        "their real properties. NEVER fabricate a risk verdict (e.g. a 'risk_level' of HIGH/LOW) via a "
        "CASE expression or heuristic over ownership depth or counts; that invents facts not in the data."
    )
)


# =============================================================================
# 4. ASKING THE DETECTIVE A QUESTION
# =============================================================================

def analyze_audit_question(question: str) -> QueryResult:
    """
    Turn a plain-English audit question into a ready-to-run Cypher query.

    We first grab the live database cheat sheet, paste it next to the question, and
    let the AI write a query that fits the real data. Returns the query + reasoning.
    """
    # 1. Grab the live "what's in the database" cheat sheet.
    schema = get_graph_schema()

    # 2. Wrap the question and the cheat sheet together into one clear prompt.
    prompt = f"""
    The user is asking: {question}

    Live Graph Schema Context:
    {schema}

    Instructions:
    Generate a Cypher query to retrieve the answer.
    Focus on indirect multi-hop relationships if the question implies hidden connections.
    Do NOT include markdown formatting (like ```cypher) in the final cypher_query string, just the raw query.
    """

    # 3. Ask the AI and hand back its structured answer.
    result = detective_agent.run_sync(prompt)
    return result.output
