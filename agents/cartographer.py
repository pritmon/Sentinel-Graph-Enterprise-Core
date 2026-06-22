"""
Specialist A: The Cartographer
--------------------------------

This module defines the Pydantic-AI agent responsible for extracting structured
knowledge (Entities and Relationships) from raw unstructured audit documents 
and mapping them directly into the Neo4j Enterprise Graph Database.
"""

import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv
from src.utils import get_neo4j_driver

# Load environment variables (API Keys, DB Credentials)
load_dotenv()

# ==========================================
# 1. DEFINE THE STRUCTURED OUTPUT SCHEMA
# ==========================================
# We use Pydantic models to force the LLM to return data in a strict, predictable JSON format.

class Entity(BaseModel):
    """Represents a discrete node in the knowledge graph."""
    name: str = Field(description="The normalized name of the entity, e.g., 'Acme Corp', 'John Doe'")
    type: str = Field(description="The category of the entity. Must be one of: 'Company', 'Person', 'Contract'")
    properties: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Flat key/value attributes of the entity, stored directly on the graph node. "
            "Values must be primitives (string, number, or boolean) — never nested objects or lists. "
            "Capture every quantitative or categorical fact the document states about the entity, e.g. for a Company: "
            "{'risk_score': 0.95, 'jurisdiction': 'British Virgin Islands', 'incorporation_date': '2019-03-03', "
            "'employee_count': 0, 'is_shell': true, 'business_activity': 'none'}; "
            "for a Contract: {'value_usd': 5000000, 'signed_date': '2024-01-15'}."
        ),
    )
    
class Relationship(BaseModel):
    """Represents a directed edge connecting two entities in the knowledge graph."""
    source: str = Field(description="The name of the origin/source entity")
    target: str = Field(description="The name of the destination/target entity")
    relation_type: str = Field(description="The type of relationship, formatted in UPPER_SNAKE_CASE e.g., 'OWNS', 'SIGNED', 'VALUED_AT'")

class ExtractedKnowledge(BaseModel):
    """The complete payload expected from the LLM after processing a document."""
    entities: List[Entity] = Field(default_factory=list, description="List of all extracted entities discovered in the text")
    relationships: List[Relationship] = Field(default_factory=list, description="List of all extracted logical relationships bridging the entities")

# ==========================================
# 2. INITIALIZE THE PYDANTIC-AI AGENT
# ==========================================
cartographer_agent = Agent(
    os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash'), 
    output_type=ExtractedKnowledge,
    system_prompt=(
        "You are Specialist A: The Cartographer. "
        "Your role is to analyze high-stakes enterprise audit documents and extract complex entities and their relationships. "
        "Create a node ONLY for first-class actors and objects, using exactly these types:\n"
        "  - 'Person'   (e.g. John Doe)\n"
        "  - 'Company'  (e.g. Alpha Corp, Beta Ltd)\n"
        "  - 'Contract' (e.g. Project X)\n"
        "CRITICAL — attributes are node PROPERTIES, never their own nodes:\n"
        "  - A risk score, jurisdiction/country, incorporation date, employee count, business activity, "
        "or shell-company flag describes a Company → put it in that Company's `properties`, "
        "e.g. risk_score, jurisdiction, incorporation_date, employee_count, is_shell, business_activity.\n"
        "  - A monetary amount or signing date describes a Contract → put it in that Contract's `properties` "
        "(value_usd, signed_date). Do NOT create separate 'Amount', 'Date', or jurisdiction nodes.\n"
        "Always capture numeric risk scores exactly as stated (e.g. 0.95, 0.12) under the `risk_score` property. "
        "Then map the logical relationships (OWNS, SIGNED, BENEFICIAL_OWNER_OF, INVOLVES) between the nodes. "
        "Structure the output exactly as requested."
    ),
)

# ==========================================
# 3. DEFINE NEO4J PERSISTENCE LOGIC
# ==========================================

@cartographer_agent.tool
def merge_knowledge_to_neo4j(ctx: RunContext[None], extracted_data: ExtractedKnowledge) -> str:
    """
    Takes the structured knowledge extracted by the LLM and commits it to Neo4j.
    It builds robust Cypher MERGE statements to ensure idempotency (no duplicate nodes).
    
    Args:
        ctx (RunContext): Context injected by Pydantic-AI.
        extracted_data (ExtractedKnowledge): The structured output from the LLM.
        
    Returns:
        str: A telemetry message indicating success and operation counts.
    """
    driver = get_neo4j_driver()
    if not driver:
        return "Failed to connect to Neo4j database."
    
    created_entities = 0
    created_rels = 0
    
    # Use a session to batch the transaction
    with driver.session() as session:
        # Phase 1: Create or Match Nodes (Entities)
        # We process nodes first to ensure relationships have valid anchoring points.
        for ent in extracted_data.entities:
            # We use parameterized queries ($name/$props) to prevent Cypher injection vulnerabilities.
            # MERGE anchors on name; SET n += $props writes the extracted attributes (risk_score,
            # jurisdiction, value_usd, ...) directly onto the node so The Detective can query them.
            q = f"MERGE (n:`{ent.type}` {{name: $name}}) SET n += $props"
            session.run(q, name=ent.name, props=ent.properties or {})
            created_entities += 1
            
        # Phase 2: Create or Match Edges (Relationships)
        for rel in extracted_data.relationships:
            # Ensure the relationship type is Neo4j compliant (UPPER_SNAKE_CASE)
            safe_rel_type = rel.relation_type.replace(' ', '_').upper()
            
            # The MERGE command here creates the relationship only if it doesn't already exist
            # between the specific Source and Target nodes.
            q = f"""
            MATCH (s {{name: $source}})
            MATCH (t {{name: $target}})
            MERGE (s)-[r:`{safe_rel_type}`]->(t)
            """
            session.run(q, source=rel.source, target=rel.target)
            created_rels += 1
            
    driver.close()
    return f"Successfully merged {created_entities} entities and {created_rels} relationships to Neo4j."


def process_document(document_text: str) -> ExtractedKnowledge:
    """
    Public entry point for processing a new audit document.
    
    This function:
    1. Triggers the LLM to extract the structured knowledge.
    2. Explicitly triggers the Neo4j merge process to save the findings.
    
    Args:
        document_text (str): The raw text of the document to ingest.
        
    Returns:
        ExtractedKnowledge: The finalized JSON payload generated by the agent.
    """
    # 1. Run the LLM extraction synchronously
    result = cartographer_agent.run_sync(document_text)
    extracted = result.output
    
    # 2. Persist to Graph Database
    merge_knowledge_to_neo4j(None, extracted)
    
    return extracted

if __name__ == "__main__":
    # Internal Unit Test logic
    sample_text = "On January 15, 2024, John Doe, CEO of Alpha Corp, signed a shadow contract named 'Project X' valued at $5,000,000 USD with a shell company called Beta Ltd."
    print("Testing Cartographer Agent...")
    res = process_document(sample_text)
    print("Extracted Info:", res)
