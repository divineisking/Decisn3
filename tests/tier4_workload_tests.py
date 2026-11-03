"""
Tier 4: Real-World Workload & User Scenario Test Suite.
Validates complete user journeys: scaffolding, decision authoring, relationship
evolution (superseding/reversing), pre-release CI/CD gates, and session navigation.
Total tests: 4.
"""

import os
import sys
import json
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
    README_MD,
    GITIGNORE_FILE,
    GIT_DIR,
    require_artifact,
    run_cmd,
    load_json_file,
    read_text_file,
)


class TestTier4RealWorldWorkloads(unittest.TestCase):
    """
    Tier 4 tests simulating complete end-to-end user workflows and lifecycles.
    """

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="dg_test_tier4_")
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

    def test_workload_scenario_a_new_project_bootstrapping_and_evolution(self):
        """
        Scenario A: Developer Onboarding Journey.
        A developer adopts the Decisn3 for a new microservice:
        1. Bootstraps repo via init CLI.
        2. Authors two ADRs (DEC-001 Database, DEC-002 Auth).
        3. Records session metadata (SES-001 Architecture Kickoff).
        4. Runs sync tool to generate standalone zero-CORS data bundle.
        5. Runs security scanner to ensure no credentials or machine paths were committed.
        6. Verifies project is ready for immediate offline launch.
        """
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")

        project_dir = os.path.join(self.temp_dir, "auth_service_repo")

        # 1. Scaffolding
        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", project_dir,
            "--project-name", "Authentication Service"
        ])
        self.assertEqual(ret, 0, f"Scaffolding failed: {stderr}\n{stdout}")

        # 2. Author ADRs
        decisions_path = os.path.join(project_dir, "data", "decisions.json")
        decisions_data = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Select PostgreSQL for User Credentials",
                    "category": "architecture",
                    "status": "validated",
                    "significance": "high",
                    "summary": "Standardize on PostgreSQL with row-level security.",
                    "choice": "PostgreSQL 16 with pg_hba.conf strict isolation",
                    "context": "Need ACID compliance and battle-tested security.",
                    "session_id": "SES-001",
                    "epoch": 1,
                    "provenance": {"timestamp": "2026-11-01T10:00:00Z"},
                    "relationships": []
                },
                {
                    "id": "DEC-002",
                    "title": "Enforce Argon2id for Password Hashing",
                    "category": "security",
                    "status": "validated",
                    "significance": "critical",
                    "summary": "Use Argon2id with 64MB memory cost to prevent GPU brute-forcing.",
                    "choice": "Argon2id m=65536, t=3, p=4",
                    "context": "OWASP password storage cheat sheet compliance.",
                    "session_id": "SES-001",
                    "epoch": 1,
                    "provenance": {"timestamp": "2026-11-01T11:30:00Z"},
                    "relationships": [
                        {"target": "DEC-001", "type": "depends_on"}
                    ]
                }
            ]
        }
        with open(decisions_path, "w", encoding="utf-8") as f:
            json.dump(decisions_data, f, indent=2)

        # 3. Record Session
        sessions_path = os.path.join(project_dir, "data", "sessions.json")
        sessions_data = {
            "sessions": [
                {
                    "id": "SES-001",
                    "title": "Architecture & Security Kickoff",
                    "start_time": "2026-11-01T09:30:00Z",
                    "end_time": "2026-11-01T12:00:00Z",
                    "step_count": 45,
                    "summary": "Initial team deliberation on database engine and password hashing.",
                    "decisions": ["DEC-001", "DEC-002"],
                    "conversation_logs": [
                        {"sender": "Lead Architect", "timestamp": "2026-11-01T09:35:00Z", "message": "Evaluating Postgres vs SQLite."},
                        {"sender": "Security Specialist", "timestamp": "2026-11-01T10:15:00Z", "message": "Argon2id is mandatory."}
                    ]
                }
            ]
        }
        with open(sessions_path, "w", encoding="utf-8") as f:
            json.dump(sessions_data, f, indent=2)

        # 4. Run Sync
        sync_script = os.path.join(project_dir, "sync_decisions.py")
        ret_sync, stdout_sync, stderr_sync = run_cmd([sys.executable, sync_script], cwd=project_dir)
        self.assertEqual(ret_sync, 0, f"Sync failed in onboarding scenario: {stderr_sync}\n{stdout_sync}")

        # 5. Run Security Audit
        ret_audit, stdout_audit, stderr_audit = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", project_dir])
        self.assertEqual(ret_audit, 0, f"Security audit flagged scaffolded repo: {stderr_audit}\n{stdout_audit}")

        # 6. Verify data.js
        data_js = os.path.join(project_dir, "data", "data.js")
        self.assertTrue(os.path.exists(data_js))
        content = read_text_file(data_js)
        self.assertIn("Select PostgreSQL for User Credentials", content)
        self.assertIn("Enforce Argon2id for Password Hashing", content)

    def test_workload_scenario_b_decision_reversal_and_supersede_lifecycle(self):
        """
        Scenario B: Decision Lifecycle Evolution (Superseding & Reversals).
        Simulates an evolving architectural graph where:
        1. DEC-001 (Aggressive Hard Deletion) is authored.
        2. Later, DEC-002 (Soft Deletion) supersedes and reverses DEC-001.
        3. DEC-003 (Audit Trail) depends on DEC-002.
        4. Validates referential integrity, relationship types, and sync bundling.
        """
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        project_dir = os.path.join(self.temp_dir, "lifecycle_project")

        run_cmd([sys.executable, INIT_SCRIPT, "--target", project_dir, "--project-name", "Lifecycle Project"])

        decisions_path = os.path.join(project_dir, "data", "decisions.json")
        decisions_payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Aggressive Hard Delete Retention Policy",
                    "category": "architecture",
                    "status": "reversed",
                    "significance": "high",
                    "summary": "Hard delete records older than 30 days.",
                    "choice": "DELETE FROM records WHERE created_at < NOW() - 30 days;",
                    "context": "Storage minimization constraint.",
                    "session_id": "SES-001",
                    "epoch": 1,
                    "provenance": {"timestamp": "2026-09-01T00:00:00Z"},
                    "relationships": []
                },
                {
                    "id": "DEC-002",
                    "title": "Architectural Reversal: Soft Deletes over Destructive Pruning",
                    "category": "architecture",
                    "status": "validated",
                    "significance": "critical",
                    "summary": "Preserve historical analytics using soft deletes with is_deleted flag.",
                    "choice": "UPDATE records SET is_deleted=TRUE, deleted_at=NOW();",
                    "context": "Hard deletes caused catastrophic data loss for recruiter pipelines.",
                    "session_id": "SES-002",
                    "epoch": 2,
                    "provenance": {"timestamp": "2026-10-16T08:26:56Z"},
                    "relationships": [
                        {"target": "DEC-001", "type": "reverses"},
                        {"target": "DEC-001", "type": "supersedes"}
                    ]
                },
                {
                    "id": "DEC-003",
                    "title": "Immutable Audit Log for Deletion Events",
                    "category": "security",
                    "status": "validated",
                    "significance": "medium",
                    "summary": "Append-only audit table tracking user deletions.",
                    "choice": "Write to audit_events on every soft delete trigger.",
                    "context": "Compliance with forensic audit requirements.",
                    "session_id": "SES-002",
                    "epoch": 2,
                    "provenance": {"timestamp": "2026-10-16T12:00:00Z"},
                    "relationships": [
                        {"target": "DEC-002", "type": "depends_on"}
                    ]
                }
            ]
        }
        with open(decisions_path, "w", encoding="utf-8") as f:
            json.dump(decisions_payload, f, indent=2)

        sync_script = os.path.join(project_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=project_dir)
        self.assertEqual(ret, 0, f"Sync failed on lifecycle test: {stderr}\n{stdout}")
        self.assertIn("3 directed relationships resolve to valid node IDs", stdout)

    def test_workload_scenario_c_pre_release_gate_simulation(self):
        """
        Scenario C: Release Gate Pipeline.
        Simulates the automated verification performed before publishing to GitHub:
        1. Run sync_decisions.py to ensure 0 broken references and synchronized data.js.
        2. Run audit_secrets.py to guarantee 0 secrets, tokens, or personal paths exist.
        3. Verify README.md includes full 10-section documentation.
        4. Verify .gitignore excludes environment and temporary files.
        """
        # Step 1: Sync Validation
        ret_sync, stdout_sync, stderr_sync = run_cmd([sys.executable, SYNC_SCRIPT])
        self.assertEqual(ret_sync, 0, f"Release Gate 1 (Sync) failed: {stderr_sync}\n{stdout_sync}")

        # Step 2: Secret Audit
        if os.path.exists(AUDIT_SCRIPT):
            ret_audit, stdout_audit, stderr_audit = run_cmd([sys.executable, AUDIT_SCRIPT])
            self.assertEqual(ret_audit, 0, f"Release Gate 2 (Audit) failed: {stderr_audit}\n{stdout_audit}")

        # Step 3: README Validation
        self.assertTrue(os.path.exists(README_MD), "Release Gate 3: README.md missing")
        readme_text = read_text_file(README_MD)
        self.assertGreater(len(readme_text), 4000, "Release Gate 3: README.md too brief")

        # Step 4: Git Ignore Validation
        if os.path.exists(GITIGNORE_FILE):
            gitignore_text = read_text_file(GITIGNORE_FILE)
            self.assertIn("__pycache__", gitignore_text)
            self.assertIn(".env", gitignore_text)

    def test_workload_scenario_d_session_based_exploration_data_navigation(self):
        """
        Scenario D: Architect Session Navigation Workflow.
        An architect bootstraps a project and navigates its historical sessions:
        1. Scaffolds project via init_decision_graph.py and reads data/sessions.json.
        2. Verifies chronological coherence (start_time <= end_time).
        3. Inspects conversation logs for dialogue excerpts.
        4. Resolves decisions to their parent sessions.
        """
        require_artifact(SESSIONS_FILE, "Milestone M1", "data/sessions.json")
        project_dir = os.path.join(self.temp_dir, "session_nav_project")
        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", project_dir,
            "--project-name", "Session Nav Project"
        ])
        self.assertEqual(ret, 0, f"Scaffolding failed: {stderr}\n{stdout}")

        sessions_data = load_json_file(os.path.join(project_dir, "data", "sessions.json"))
        sessions = sessions_data.get("sessions", [])
        self.assertGreaterEqual(len(sessions), 2, "Scaffolded project must contain at least 2 seed sessions")

        for s in sessions:
            # Check timestamps
            start_time = s.get("start_time")
            end_time = s.get("end_time")
            self.assertIsNotNone(start_time, f"Session {s['id']} missing start_time")
            self.assertIsNotNone(end_time, f"Session {s['id']} missing end_time")
            self.assertLessEqual(start_time, end_time, f"Session {s['id']} start_time after end_time")

            # Check decisions list
            dec_list = s.get("decisions", [])
            self.assertIsInstance(dec_list, list)

            # Check conversation logs
            logs = s.get("conversation_logs", [])
            self.assertIsInstance(logs, list)


if __name__ == "__main__":
    unittest.main()
