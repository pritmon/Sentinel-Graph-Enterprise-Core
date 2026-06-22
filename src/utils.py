"""
Database Helpers
================

Small, shared tools for talking to the Neo4j graph database. Every specialist uses
these two functions instead of opening their own connection, so the database details
live in just one place.
"""

import os

from neo4j import GraphDatabase
from dotenv import load_dotenv

# Pull the database login (and other secrets) out of the .env file.
load_dotenv()


def get_neo4j_driver():
    """
    Open a connection to the Neo4j database and hand it back.

    Reads the address and login from the environment. If anything goes wrong (wrong
    password, database is off, etc.) it prints the problem and returns None instead
    of crashing, so callers can fail gracefully.
    """
    uri      = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user     = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    try:
        # Build the connection...
        driver = GraphDatabase.driver(uri, auth=(user, password))

        # ...and make sure the database actually answers before we trust it.
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"[ERROR] Failed to connect to Neo4j Enterprise Graph: {e}")
        return None


def execute_query(query: str, parameters: dict = None):
    """
    Run one Cypher query and return its rows as a list of dictionaries.

    `parameters` lets you pass values separately from the query text, which keeps
    things safe from injection. Returns None if the connection or the query fails.
    """
    # Get a fresh connection for this query.
    driver = get_neo4j_driver()
    if not driver:
        return None

    # "with ... as session" guarantees the session is tidied up when we're done.
    with driver.session() as session:
        try:
            # Run the query and turn each returned row into a plain dictionary.
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
        except Exception as e:
            print(f"[ERROR] Cypher Execution Interrupted: {e}")
            return None
        finally:
            # Always close the connection so we don't leak open handles.
            driver.close()
