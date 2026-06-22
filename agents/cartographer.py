"""
Specialist A: The Cartographer
==============================

Think of the Cartographer as the map-maker of the system.

It reads a messy, free-text audit document and turns it into a tidy map:
  - "things"  -> nodes      (a Person, a Company, a Contract)
  - "links"   -> edges       (who OWNS what, who SIGNED what)
  - "details" -> properties  (a company's risk score, a contract's value)

Once the map is built, it saves everything straight into the Neo4j graph
database so the other specialists can ask questions about it later.
"""

import os
from typing import List, Dict, Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from dotenv import load_dotenv

from src.utils import get_neo4j_driver

# Pull secrets (API keys, database login) out of the .env file into the environment.
load_dotenv()


# =============================================================================
# 1. THE SHAPE OF THE DATA WE WANT BACK
# =============================================================================
# These models are a strict "fill-in-the-blanks" form for the AI. By describing
# exactly what we expect, the AI is forced to answer in clean, predictable JSON
# instead of free-form text we'd have to clean up ourselves.

class Entity(BaseModel):
    """One "thing" in the graph — a Person, a Company, or a Contract."""

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
    """One "link" that joins two things together, with a direction (source -> target)."""

    source:        str = Field(description="The name of the origin/source entity")
    target:        str = Field(description="The name of the destination/target entity")
    relation_type: str = Field(description="The type of relationship, formatted in UPPER_SNAKE_CASE e.g., 'OWNS', 'SIGNED', 'VALUED_AT'")


class ExtractedKnowledge(BaseModel):
    """The whole map the AI hands back: a list of things plus a list of links."""

    entities:      List[Entity]       = Field(default_factory=list, description="List of all extracted entities discovered in the text")
    relationships: List[Relationship] = Field(default_factory=list, description="List of all extracted logical relationships bridging the entities")


# =============================================================================
# 2. THE AI AGENT ITSELF
# =============================================================================
# We hand the AI a model name, the "form" to fill in (output_type), and a set of
# house rules (system_prompt) that teach it exactly how to read the document.

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


# =============================================================================
# 3. SAVING THE MAP INTO NEO4J
# =============================================================================

@cartographer_agent.tool
def merge_knowledge_to_neo4j(ctx: RunContext[None], extracted_data: ExtractedKnowledge) -> str:
    """
    Write the extracted map into the Neo4j database.

    We use Cypher's MERGE command, which means "create this if it's new, otherwise
    reuse the one that's already there." That keeps the graph clean — running the
    same document twice will never create duplicate nodes.

    Returns a short status message saying how much was saved.
    """
    driver = get_neo4j_driver()
    if not driver:
        return "Failed to connect to Neo4j database."

    created_entities = 0
    created_rels     = 0

    # One database session covers both writing steps below.
    with driver.session() as session:

        # Step 1: add the "things" (nodes) first, so the links have something to attach to.
        for ent in extracted_data.entities:
            # $name / $props are passed separately (parameterized) so user text can never
            # be misread as code — this is what keeps the query safe from injection.
            # MERGE finds-or-creates the node; "SET n += $props" stamps the details onto it.
            query = f"MERGE (n:`{ent.type}` {{name: $name}}) SET n += $props"
            session.run(query, name=ent.name, props=ent.properties or {})
            created_entities += 1

        # Step 2: add the "links" (edges) between the things we just created.
        for rel in extracted_data.relationships:
            # Tidy the label into Neo4j's expected style, e.g. "owned by" -> "OWNED_BY".
            safe_rel_type = rel.relation_type.replace(' ', '_').upper()

            # Find both ends by name, then MERGE the link so it's added only once.
            query = f"""
            MATCH (s {{name: $source}})
            MATCH (t {{name: $target}})
            MERGE (s)-[r:`{safe_rel_type}`]->(t)
            """
            session.run(query, source=rel.source, target=rel.target)
            created_rels += 1

    driver.close()
    return f"Successfully merged {created_entities} entities and {created_rels} relationships to Neo4j."


def process_document(document_text: str) -> ExtractedKnowledge:
    """
    The front door for ingesting a new document. Two simple steps:

      1. Ask the AI to read the text and pull out the map.
      2. Save that map into the graph database.

    Returns the map so the caller can show what was found.
    """
    # Step 1: let the AI do the reading and extracting.
    result    = cartographer_agent.run_sync(document_text)
    extracted = result.output

    # Step 2: store everything in Neo4j.
    merge_knowledge_to_neo4j(None, extracted)

    return extracted


if __name__ == "__main__":
    # A tiny manual check you can run with `python agents/cartographer.py`.
    sample_text = "On January 15, 2024, John Doe, CEO of Alpha Corp, signed a shadow contract named 'Project X' valued at $5,000,000 USD with a shell company called Beta Ltd."
    print("Testing Cartographer Agent...")
    res = process_document(sample_text)
    print("Extracted Info:", res)
