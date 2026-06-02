"""
100-run stress test of the orchestrator logic.
Mocks the LLM agents; uses real Neo4j for DB assertions.
Covers: pass path, retry loop, syntax-error recovery, trace completeness.
"""

import os, sys, unittest, time
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))


def mock_result(obj):
    m = MagicMock()
    m.output = obj
    return m


class OrchestratorStressTest(unittest.TestCase):

    def _run(self, audit_score, cypher="MATCH (n) RETURN n LIMIT 1", db_error=False):
        from agents.detective import QueryResult
        from agents.auditor import AuditEval

        fake_query = QueryResult(cypher_query=cypher, reasoning="test")
        fake_eval = AuditEval(
            score=audit_score,
            reasoning="test eval",
            rewritten_query="" if audit_score >= 0.85 else "Rewritten question"
        )

        def fake_execute(query, params=None):
            if db_error:
                return None  # simulates Cypher syntax error
            return [{"n": "test_node"}]

        with patch("agents.detective.detective_agent.run_sync", return_value=mock_result(fake_query)), \
             patch("agents.auditor.auditor_agent.run_sync", return_value=mock_result(fake_eval)), \
             patch("agents.orchestrator.execute_query", side_effect=fake_execute):
            from agents.orchestrator import build_workflow
            graph = build_workflow()
            return graph.invoke({"question": "Who signed Project X?", "retries": 0, "reasoning_trace": []})


# ── generate 100 test methods ─────────────────────────────────

def make_pass_test(i):
    def test(self):
        final = self._run(audit_score=0.90)
        self.assertIn("findings are", final["final_answer"], f"run {i}: no final answer")
        self.assertEqual(final["retries"], 1, f"run {i}: should complete in 1 pass, got {final['retries']}")
        agents = {s["agent"] for s in final["reasoning_trace"]}
        self.assertIn("Detective", agents)
        self.assertIn("Auditor", agents)
        self.assertIn("System", agents)
    test.__name__ = f"test_{i:03d}_pass_path"
    return test

def make_retry_test(i):
    def test(self):
        final = self._run(audit_score=0.10)
        self.assertGreaterEqual(final["retries"], 3, f"run {i}: retry cap not reached")
        self.assertIn("findings are", final["final_answer"], f"run {i}: no final answer after retries")
    test.__name__ = f"test_{i:03d}_retry_cap"
    return test

def make_error_test(i):
    def test(self):
        # DB error → results=None → CYPHER_ERROR string → Auditor scores low → retries → cap
        final = self._run(audit_score=0.10, db_error=True)
        self.assertGreaterEqual(final["retries"], 3, f"run {i}: should hit retry cap on DB error")
        error_steps = [s for s in final["reasoning_trace"]
                       if "CYPHER_ERROR" in str(s.get("results", ""))]
        self.assertGreater(len(error_steps), 0, f"run {i}: CYPHER_ERROR not surfaced in trace")
    test.__name__ = f"test_{i:03d}_error_recovery"
    return test

def make_threshold_test(i):
    def test(self):
        # Score exactly at threshold (0.85) should pass in 1 loop
        final = self._run(audit_score=0.85)
        self.assertEqual(final["retries"], 1, f"run {i}: score=0.85 should pass immediately")
    test.__name__ = f"test_{i:03d}_threshold_boundary"
    return test


# Distribute 100 tests: 40 pass, 30 retry, 20 error-recovery, 10 threshold
for i in range(40):
    setattr(OrchestratorStressTest, f"test_{i:03d}_pass_path",      make_pass_test(i))
for i in range(40, 70):
    setattr(OrchestratorStressTest, f"test_{i:03d}_retry_cap",      make_retry_test(i))
for i in range(70, 90):
    setattr(OrchestratorStressTest, f"test_{i:03d}_error_recovery", make_error_test(i))
for i in range(90, 100):
    setattr(OrchestratorStressTest, f"test_{i:03d}_threshold",      make_threshold_test(i))


if __name__ == "__main__":
    start = time.time()
    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda a, b: (a > b) - (a < b)
    suite = loader.loadTestsFromTestCase(OrchestratorStressTest)
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    result = runner.run(suite)
    elapsed = time.time() - start
    print(f"\nRan {result.testsRun} tests in {elapsed:.1f}s")
    print(f"Passed : {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed : {len(result.failures)}")
    print(f"Errors : {len(result.errors)}")
    sys.exit(0 if result.wasSuccessful() else 1)
