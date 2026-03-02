import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables (e.g., NEO4J_URI, GEMINI_API_KEY) from .env file
load_dotenv()

def get_neo4j_driver():
    """
    Initializes and returns a Neo4j driver connection.
    
    This function acts as the core database bridge for the Sentinel-Graph system.
    It reads the connection credentials from the environment and establishes a 
    persistent driver instance that can be used for querying the Enterprise Knowledge Graph.
    
    Returns:
        neo4j.Driver: A connected Neo4j driver instance, or None if the connection fails.
    """
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        # Establish connection using the official Neo4j Python driver
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        # Verify the database is actually reachable before returning
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"[ERROR] Failed to connect to Neo4j Enterprise Graph: {e}")
        return None

def execute_query(query: str, parameters: dict = None):
    """
    Executes a raw Cypher query against the Neo4j database safely.
    
    This utility is used by The Detective (for dynamic graph traversal) and 
    The Cartographer (for entity mapping) to interact with the database.
    
    Args:
        query (str): The Cypher query string to execute.
        parameters (dict, optional): Parameter dictionary to prevent Cypher injection risks.
        
    Returns:
        list[dict]: A list of records returned by the query, structured as dictionaries.
    """
    # Obtain a fresh driver connection
    driver = get_neo4j_driver()
    if not driver:
        return None
    
    # Use a session context manager to ensure the connection is cleanly closed
    with driver.session() as session:
        try:
            # Execute the query with optional safe parameters
            result = session.run(query, parameters or {})
            
            # Extract and return the raw data mappings from the Neo4j records
            return [record.data() for record in result]
        except Exception as e:
            print(f"[ERROR] Cypher Execution Interrupted: {e}")
            return None
        finally:
            # Always close the driver to prevent connection pooling leaks
            driver.close()
