"""
End-to-end system test with mocked LLM agents.

Tests:
  1. Neo4j connectivity
  2. Cartographer entity extraction + graph write (mocked LLM, real DB)
  3. Detective Cypher generation (mocked LLM)
  4. Full LangGraph orchestrator workflow: pass path and retry loop
"""

import os, sys, unittest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))


# ── helpers ──────────────────────────────────────────────────────────────────

def make_mock_run_result(output_obj):
    """Return a fake pydantic-ai RunResult whose .output is the given object."""
    m = MagicMock()
    m.output = output_obj
    return m


# ── 1. Neo4j connectivity ─────────────────────────────────────────────────────

class TestNeo4jConnection(unittest.TestCase):
    def test_driver_connects(self):
        from src.utils import get_neo4j_driver
        driver = get_neo4j_driver()
        self.assertIsNotNone(driver, "Neo4j driver should not be None")
        driver.close()

    def test_execute_query_returns_list(self):
        from src.utils import execute_query
        result = execute_query("RETURN 1 AS n")
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["n"], 1)


# ── 2. Cartographer (mocked LLM, real DB write) ───────────────────────────────

class TestCartographer(unittest.TestCase):
    def test_entity_extraction_and_neo4j_write(self):
        from agents.cartographer import ExtractedKnowledge, Entity, Relationship

        fake_knowledge = ExtractedKnowledge(
            entities=[
                Entity(name="Jane Smith",   type="Person"),
                Entity(name="Gamma Corp",   type="Company"),
                Entity(name="Contract-007", type="Contract"),
            ],
            relationships=[
                Relationship(source="Jane Smith",   target="Contract-007", relation_type="SIGNED"),
                Relationship(source="Gamma Corp",   target="Contract-007", relation_type="OWNS"),
            ]
        )

        with patch("agents.cartographer.cartographer_agent.run_sync",
                   return_value=make_mock_run_result(fake_knowledge)):
            from agents.cartographer import process_document
            result = process_document("Jane Smith signed Contract-007 on behalf of Gamma Corp.")

        self.assertEqual(len(result.entities), 3)
        self.assertEqual(len(result.relationships), 2)

        # Verify nodes actually landed in Neo4j
        from src.utils import execute_query
        rows = execute_query("MATCH (n {name: 'Jane Smith'}) RETURN n.name AS name")
        self.assertTrue(any(r["name"] == "Jane Smith" for r in rows),
                        "Jane Smith node not found in Neo4j")

    def tearDown(self):
        # Clean up test nodes so repeated runs stay idempotent
        from src.utils import execute_query
        execute_query("MATCH (n) WHERE n.name IN ['Jane Smith','Gamma Corp','Contract-007'] DETACH DELETE n")


# ── 3. Detective (mocked LLM) ─────────────────────────────────────────────────

class TestDetective(unittest.TestCase):
    def test_query_generation(self):
        from agents.detective import QueryResult

        fake_result = QueryResult(
            cypher_query="MATCH (p:Person)-[:SIGNED]->(c:Contract) RETURN p.name, c.name",
            reasoning="Match Person nodes connected to Contract nodes via SIGNED relationship."
        )

        with patch("agents.detective.detective_agent.run_sync",
                   return_value=make_mock_run_result(fake_result)):
            from agents.detective import analyze_audit_question
            result = analyze_audit_question("Who signed a contract?")

        self.assertIn("MATCH", result.cypher_query)
        self.assertIsInstance(result.reasoning, str)


# ── 4. Full LangGraph orchestrator ────────────────────────────────────────────

class TestOrchestrator(unittest.TestCase):
    def _run_workflow(self, audit_score: float, expected_retries: int):
        from agents.detective import QueryResult
        from agents.auditor import AuditEval

        fake_query = QueryResult(
            cypher_query="MATCH (n) RETURN n LIMIT 1",
            reasoning="Simple test query."
        )
        fake_eval = AuditEval(
            score=audit_score,
            reasoning="Test evaluation.",
            rewritten_query="" if audit_score >= 0.85 else "Rewritten: " + "Who owns the shell company?"
        )

        with patch("agents.detective.detective_agent.run_sync",
                   return_value=make_mock_run_result(fake_query)), \
             patch("agents.auditor.auditor_agent.run_sync",
                   return_value=make_mock_run_result(fake_eval)):

            from agents.orchestrator import build_workflow
            graph = build_workflow()
            state = {"question": "Who signed Project X?", "retries": 0, "reasoning_trace": []}
            final = graph.invoke(state)

        return final

    def test_passing_audit_completes_in_one_pass(self):
        final = self._run_workflow(audit_score=0.95, expected_retries=1)
        self.assertIn("findings are", final["final_answer"])
        self.assertEqual(final["retries"], 1, "Should complete without retries")

    def test_failing_audit_triggers_retry_then_caps(self):
        # Score of 0.1 forces retries up to the max (3)
        final = self._run_workflow(audit_score=0.1, expected_retries=3)
        self.assertGreaterEqual(final["retries"], 3, "Should hit max retry cap of 3")
        self.assertIn("findings are", final["final_answer"])

    def test_reasoning_trace_is_populated(self):
        final = self._run_workflow(audit_score=0.95, expected_retries=1)
        agents_seen = {step["agent"] for step in final["reasoning_trace"]}
        self.assertIn("Detective", agents_seen)
        self.assertIn("Auditor",   agents_seen)
        self.assertIn("System",    agents_seen)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
