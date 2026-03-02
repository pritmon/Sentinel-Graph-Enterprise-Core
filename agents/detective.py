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
from langchain_community.graphs import Neo4jGraph
from dotenv import load_dotenv

# Load environment variables (API Keys, DB Credentials)
load_dotenv()

# ==========================================
# 1. GRAPH SCHEMA AWARENESS
# ==========================================

def get_graph_schema() -> str:
    """
    Connects to Neo4j to retrieve the current database schema.
    
    This schema (Nodes, Relationships, Properties) is injected into the LLM's prompt.
    This grounding technique prevents hallucinations and ensures the LLM writes 
    Cypher queries that actually match the existing data structure.
    
    Returns:
        str: A text representation of the Neo4j schema, or an error message.
    """
    try:
        # We leverage Langchain's Neo4jGraph wrapper specifically for its excellent schema extraction
        graph = Neo4jGraph(
            url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            username=os.getenv("NEO4J_USERNAME", "neo4j"),
            password=os.getenv("NEO4J_PASSWORD", "password")
        )
        return graph.get_schema
    except Exception as e:
        return f"[WARNING] Could not retrieve schema. Reasoning may degrade: {str(e)}"

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
        "and relationship types (typically UPPER_SNAKE_CASE)."
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
    return result.data
