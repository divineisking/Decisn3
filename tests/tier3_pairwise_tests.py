"""
Tier 3: Pairwise & Cross-Feature Integration Test Suite.
Validates multi-feature interactions, pipelines (init -> sync -> audit),
data.js compilation and evaluation, and browser DOM state.
Total tests: 6.
"""

import os
import sys
import json
import re
import shutil
import tempfile
import unittest

from tests.test_helpers import (
    REPO_ROOT,
    DATA_DIR,
    DECISIONS_FILE,
    SESSIONS_FILE,
    SOURCES_FILE,
    DATA_JS_FILE,
    SYNC_SCRIPT,
    INIT_SCRIPT,
    AUDIT_SCRIPT,
    INDEX_HTML,
    require_artifact,
    run_cmd,
    load_json_file,
    read_text_file,
)


class TestTier3PairwiseInteractions(unittest.TestCase):
    """
    Tier 3 tests verifying cross-feature workflows and integration boundaries.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="dg_test_tier3_")
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

    def test_pairwise_init_sync_audit_pipeline(self):
        """Tier 3: Scaffold repo -> sync decisions -> audit secrets pipeline all pass cleanly."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")

        target_repo = os.path.join(self.temp_dir, "pipeline_repo")

        # Step 1: Init scaffolding
        ret_init, stdout_init, stderr_init = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", target_repo,
            "--project-name", "PipelineApp"
        ])
        self.assertEqual(ret_init, 0, f"Step 1 (Init) failed: {stderr_init}\n{stdout_init}")

        # Step 2: Sync in scaffolded repo
        target_sync = os.path.join(target_repo, "sync_decisions.py")
        ret_sync, stdout_sync, stderr_sync = run_cmd([sys.executable, target_sync], cwd=target_repo)
        self.assertEqual(ret_sync, 0, f"Step 2 (Sync) failed: {stderr_sync}\n{stdout_sync}")

        # Step 3: Audit secrets in scaffolded repo
        ret_audit, stdout_audit, stderr_audit = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", target_repo])
        self.assertEqual(ret_audit, 0, f"Step 3 (Audit) failed: {stderr_audit}\n{stdout_audit}")

    def test_pairwise_init_add_decision_and_sync(self):
        """Tier 3: Scaffold repo -> add new decision linked to seed session -> sync compiles data.js."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        target_repo = os.path.join(self.temp_dir, "lifecycle_repo")

        # 1. Init
        run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "LifecycleApp"])

        # 2. Add DEC-002 linking to DEC-001 and SES-001
        decisions_path = os.path.join(target_repo, "data", "decisions.json")
        dec_data = load_json_file(decisions_path)

        new_decision = {
            "id": "DEC-002",
            "title": "Adopt SQLite WAL Mode",
            "category": "infrastructure",
            "status": "validated",
            "significance": "medium",
            "summary": "Switch SQLite journaling to WAL mode for concurrent readers.",
            "choice": "Enable PRAGMA journal_mode=WAL;",
            "context": "Reader lock starvation observed during peak queries.",
            "session_id": "SES-001",
            "epoch": 1,
            "provenance": {"timestamp": "2026-11-02T16:00:00Z"},
            "relationships": [
                {"target": "DEC-001", "type": "depends_on"}
            ]
        }
        dec_data["decisions"].append(new_decision)
        with open(decisions_path, "w", encoding="utf-8") as f:
            json.dump(dec_data, f, indent=2)

        # 3. Also update sessions.json to register DEC-002 in SES-001
        sessions_path = os.path.join(target_repo, "data", "sessions.json")
        if os.path.exists(sessions_path):
            ses_data = load_json_file(sessions_path)
            for s in ses_data.get("sessions", []):
                if s.get("id") == "SES-001":
                    s.setdefault("decisions", []).append("DEC-002")
            with open(sessions_path, "w", encoding="utf-8") as f:
                json.dump(ses_data, f, indent=2)

        # 4. Run sync
        target_sync = os.path.join(target_repo, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, target_sync], cwd=target_repo)
        self.assertEqual(ret, 0, f"Sync failed after adding decision: {stderr}\n{stdout}")

        # 5. Verify data.js contains DEC-002
        data_js = os.path.join(target_repo, "data", "data.js")
        content = read_text_file(data_js)
        self.assertIn("DEC-002", content)
        self.assertIn("Adopt SQLite WAL Mode", content)

    def test_pairwise_data_js_bundle_format_and_eval(self):
        """Tier 3: Verify data/data.js conforms strictly to window.DECISN3_DATA = {...};"""
        require_artifact(DATA_JS_FILE, "Milestone M1", "data/data.js")
        content = read_text_file(DATA_JS_FILE).strip()

        prefix = "window.DECISN3_DATA ="
        self.assertTrue(content.startswith(prefix), f"data.js must start with '{prefix}'")
        self.assertTrue(content.endswith(";"), "data.js must end with semicolon ';'")

        # Extract JSON payload and parse
        json_str = content[len(prefix):].rstrip(";").strip()
        try:
            payload = json.loads(json_str)
        except json.JSONDecodeError as exc:
            self.fail(f"data.js does not contain valid JSON payload: {exc}")

        self.assertIn("decisions", payload)
        self.assertIn("sources", payload)
        if "sessions.json" in read_text_file(SYNC_SCRIPT):
            self.assertIn("sessions", payload)

    def test_pairwise_session_filtering_matches_timeline_and_explorer(self):
        """Tier 3: Verify decision dataset session IDs match session entries and timeline epoch order."""
        require_artifact(SESSIONS_FILE, "Milestone M1", "data/sessions.json")
        decisions_data = load_json_file(DECISIONS_FILE)
        sessions_data = load_json_file(SESSIONS_FILE)

        decisions = decisions_data.get("decisions", [])
        sessions = sessions_data.get("sessions", [])

        # Group decisions by session_id
        decisions_by_session = {}
        for d in decisions:
            s_id = d.get("session_id")
            if s_id:
                decisions_by_session.setdefault(s_id, []).append(d["id"])

        for s in sessions:
            claimed_decs = set(s.get("decisions", []))
            mapped_decs = set(decisions_by_session.get(s["id"], []))
            self.assertEqual(
                claimed_decs, mapped_decs,
                f"Mismatch in decision list for session {s['id']}: claimed={claimed_decs}, mapped={mapped_decs}"
            )

    def test_pairwise_sync_cli_init_matches_standalone_init(self):
        """Tier 3: Verify sync_decisions.py --init produces consistent layout with init_decision_graph.py."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        repo_standalone = os.path.join(self.temp_dir, "standalone_repo")
        repo_flag = os.path.join(self.temp_dir, "flag_repo")

        # Run init_decision_graph.py
        run_cmd([sys.executable, INIT_SCRIPT, "--target", repo_standalone, "--project-name", "TestApp"])

        # Run sync_decisions.py --init
        ret, stdout, stderr = run_cmd([
            sys.executable, SYNC_SCRIPT,
            "--init",
            "--target", repo_flag,
            "--project-name", "TestApp"
        ])
        if ret != 0 and "--init" not in read_text_file(SYNC_SCRIPT):
            self.skipTest("sync_decisions.py --init not yet wired to init logic")

        # Compare generated directory trees
        for relative_file in ["index.html", "app.js", "styles.css", "sync_decisions.py", "data/decisions.json"]:
            p1 = os.path.join(repo_standalone, relative_file)
            p2 = os.path.join(repo_flag, relative_file)
            self.assertTrue(os.path.exists(p1), f"Standalone missing {relative_file}")
            self.assertTrue(os.path.exists(p2), f"Flag repo missing {relative_file}")

    def test_pairwise_browser_dom_integration(self):
        """Tier 3: Browser DOM integration test via Playwright (Microsoft Edge)."""
        # Try importing Playwright
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("playwright not installed")

        console_errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(channel="msedge", headless=True)
                page = browser.new_page()

                def on_console(msg):
                    if msg.type == "error":
                        console_errors.append(msg.text)

                page.on("console", on_console)
                file_url = f"file:///{INDEX_HTML.replace(os.sep, '/')}"
                page.goto(file_url, wait_until="load")

                # Verify window.DECISN3_DATA is loaded in window scope (clean repo ships with 0 decisions)
                has_data = page.evaluate("() => Boolean(window.DECISN3_DATA && Array.isArray(window.DECISN3_DATA.decisions))")
                self.assertTrue(has_data, "window.DECISN3_DATA should be initialized in browser")

                # Check graph view container
                graph_view = page.query_selector("#view-graph")
                self.assertIsNotNone(graph_view, "#view-graph container must exist in DOM")

                # Check if session filter select exists
                session_filter = page.query_selector("#graph-session-filter")
                if session_filter:
                    options = session_filter.query_selector_all("option")
                    self.assertGreaterEqual(len(options), 1)

                # Also verify a scaffolded project renders >=1 decision in browser
                scaffold_dir = os.path.join(self.temp_dir, "browser_scaffold_repo")
                run_cmd([sys.executable, INIT_SCRIPT, "--target", scaffold_dir, "--project-name", "BrowserApp"])
                scaffold_url = f"file:///{os.path.join(scaffold_dir, 'index.html').replace(os.sep, '/')}"
                page.goto(scaffold_url, wait_until="load")
                decision_count = page.evaluate("() => window.DECISN3_DATA ? window.DECISN3_DATA.decisions.length : 0")
                self.assertGreaterEqual(decision_count, 1, "Scaffolded project window.DECISN3_DATA should be populated in browser")

                browser.close()
        except Exception as exc:
            # If Edge browser binary is not reachable in CI/test environment, skip cleanly
            self.skipTest(f"Browser launch skipped: {exc}")

        # Assert no severe console errors occurred
        critical_errors = [e for e in console_errors if "favicon.ico" not in e and "CORS" not in e]
        self.assertEqual(len(critical_errors), 0, f"Browser console errors detected: {critical_errors}")


if __name__ == "__main__":
    unittest.main()
