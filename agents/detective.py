"""
Specialist B: The Detective
-----------------------------

This module defines the Pydantic-AI agent responsible for translating natural language
audit questions into complex Neo4j Cypher queries. It leverages the Neo4j schema
to ensure generated queries are syntactically and semantically correct for the graph.
"""

import os
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv

# Load environment variables (API Keys, DB Credentials)
load_dotenv()

# ==========================================
# 1. GRAPH SCHEMA AWARENESS
# ==========================================

def get_graph_schema() -> str:
    """
    Retrieves the live Neo4j schema using built-in Cypher — no APOC required.
    Returns node labels, relationship types, and property keys actually present in the DB.
    """
    from src.utils import execute_query
    try:
        node_labels = execute_query("CALL db.labels() YIELD label RETURN collect(label) AS labels")
        rel_types   = execute_query("CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) AS types")
        prop_keys   = execute_query("CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) AS keys")

        # Sample actual relationships so the LLM sees real source→type→target triples
        samples = execute_query("""
            MATCH (a)-[r]->(b)
            RETURN DISTINCT labels(a)[0] AS from_label, type(r) AS rel_type, labels(b)[0] AS to_label
            LIMIT 40
        """)

        labels = node_labels[0]["labels"] if node_labels else []
        types  = rel_types[0]["types"]    if rel_types   else []
        keys   = prop_keys[0]["keys"]     if prop_keys   else []
        sample_lines = "\n".join(
            f"  (:{s['from_label']})-[:{s['rel_type']}]->(:{s['to_label']})"
            for s in (samples or [])
        )

        return (
            f"Node Labels : {labels}\n"
            f"Relationship Types: {types}\n"
            f"Property Keys: {keys}\n"
            f"Existing relationship patterns in database:\n{sample_lines}"
        )
    except Exception as e:
        return f"[WARNING] Could not retrieve schema: {str(e)}"

# ==========================================
# 2. DEFINE THE STRUCTURED OUTPUT SCHEMA
# ==========================================

class QueryResult(BaseModel):
    """The structured output expected from The Detective."""
    cypher_query: str = Field(description="The executable Neo4j Cypher query generated to directly answer the audit question.")
    reasoning: str = Field(description="A step-by-step explanation of the multi-hop traversal strategy used in the query.")

# ==========================================
# 3. INITIALIZE THE PYDANTIC-AI AGENT
# ==========================================

detective_agent = Agent(
    os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'),
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
        "7. When results are empty, broaden the MATCH pattern — do not add more OPTIONAL MATCH clauses."
    )
)

# ==========================================
# 4. EXECUTION LOGIC
# ==========================================

def analyze_audit_question(question: str) -> QueryResult:
    """
    Public entry point for query generation.
    
    This function dynamically injects the live Neo4j schema alongside the user's
    question to produce a highly accurate, zero-shot Cypher query.
    
    Args:
        question (str): The natural language query from the auditor.
        
    Returns:
        QueryResult: The generated Cypher query and the LLM's reasoning trace.
    """
    # 1. Fetch live schema context
    schema = get_graph_schema()
    
    # 2. Construct the enriched prompt
    prompt = f"""
    The user is asking: {question}
    
    Live Graph Schema Context:
    {schema}
    
    Instructions:
    Generate a Cypher query to retrieve the answer. 
    Focus on indirect multi-hop relationships if the question implies hidden connections.
    Do NOT include markdown formatting (like ```cypher) in the final cypher_query string, just the raw query.
    """
    
    # 3. Execute LLM synchronously
    result = detective_agent.run_sync(prompt)
    return result.output
