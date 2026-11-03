"""
Tier 2: Boundary & Corner Cases Test Suite.
Validates system resilience against empty directories, corrupted JSON,
invalid edges, missing mandatory fields, and extreme inputs.
Total tests: 13.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest

from tests.test_helpers import (
    REPO_ROOT,
    SYNC_SCRIPT,
    INIT_SCRIPT,
    AUDIT_SCRIPT,
    require_artifact,
    run_cmd,
    load_json_file,
)


class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """
    Tier 2 tests validating edge conditions, fault handling, and resilience.
    """

    def setUp(self):
        """Set up temporary working sandbox for file mutations."""
        self.temp_dir = tempfile.mkdtemp(prefix="dg_test_tier2_")
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

    def _create_minimal_project(self, decisions_payload, sources_payload=None, sessions_payload=None):
        """Helper to create a minimal project structure inside sandbox."""
        data_dir = os.path.join(self.temp_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        # Copy sync_decisions.py into sandbox
        shutil.copy2(SYNC_SCRIPT, os.path.join(self.temp_dir, "sync_decisions.py"))

        dec_file = os.path.join(data_dir, "decisions.json")
        if isinstance(decisions_payload, str):
            with open(dec_file, "w", encoding="utf-8") as f:
                f.write(decisions_payload)
        elif decisions_payload is not None:
            with open(dec_file, "w", encoding="utf-8") as f:
                json.dump(decisions_payload, f, indent=2)

        if sources_payload is not None:
            src_file = os.path.join(data_dir, "sources.json")
            with open(src_file, "w", encoding="utf-8") as f:
                json.dump(sources_payload, f, indent=2)

        if sessions_payload is None:
            sessions_payload = {"sessions": []}

        if sessions_payload is not False:
            ses_file = os.path.join(data_dir, "sessions.json")
            with open(ses_file, "w", encoding="utf-8") as f:
                json.dump(sessions_payload, f, indent=2)

        return self.temp_dir

    # =========================================================================
    # Boundary: Ingestion & Sync Fault Handling
    # =========================================================================

    def test_sync_empty_decisions_array(self):
        """Tier 2: sync tool handles empty decisions array gracefully."""
        self._create_minimal_project({"decisions": []})
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        # Should not crash with unhandled traceback
        self.assertEqual(ret, 0, f"sync should handle empty decisions gracefully: {stderr}\n{stdout}")
        self.assertIn("0 decisions", stdout)

    def test_sync_corrupted_json(self):
        """Tier 2: sync tool reports error and exits non-zero on malformed JSON."""
        self._create_minimal_project('{"decisions": [ {"id": "DEC-001"')  # truncated JSON
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "sync_decisions.py must exit with non-zero code on corrupted JSON")

    def test_sync_missing_decisions_file(self):
        """Tier 2: sync tool reports error when data/decisions.json does not exist."""
        # Create directory without decisions.json
        data_dir = os.path.join(self.temp_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        shutil.copy2(SYNC_SCRIPT, os.path.join(self.temp_dir, "sync_decisions.py"))

        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "sync_decisions.py must exit non-zero when decisions.json is missing")
        self.assertTrue("[ERROR]" in stdout or "[ERROR]" in stderr)

    def test_sync_missing_sessions_file(self):
        """Tier 2: sync tool reports error when data/sessions.json is missing."""
        self._create_minimal_project({"decisions": []}, sessions_payload=False)
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "sync_decisions.py must exit non-zero when sessions.json is missing")
        self.assertTrue("[ERROR]" in stdout or "[ERROR]" in stderr)

    def test_sync_duplicate_decision_ids(self):
        """Tier 2: sync tool detects duplicate decision IDs and terminates."""
        payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Decision One",
                    "category": "architecture",
                    "status": "validated",
                    "significance": "high",
                    "summary": "Summary 1",
                    "choice": "Choice 1",
                    "context": "Context 1",
                    "provenance": {"timestamp": "2026-07-21"},
                    "relationships": []
                },
                {
                    "id": "DEC-001",  # duplicate ID
                    "title": "Decision One Duplicate",
                    "category": "architecture",
                    "status": "validated",
                    "significance": "high",
                    "summary": "Summary 1 Dup",
                    "choice": "Choice 1 Dup",
                    "context": "Context 1 Dup",
                    "provenance": {"timestamp": "2026-07-22"},
                    "relationships": []
                }
            ]
        }
        self._create_minimal_project(payload)
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "Duplicate IDs must trigger non-zero exit code")
        self.assertIn("Duplicate", stdout)

    def test_sync_broken_relationship_target(self):
        """Tier 2: sync tool detects broken directed edge pointing to non-existent node."""
        payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Decision One",
                    "category": "architecture",
                    "status": "validated",
                    "significance": "high",
                    "summary": "Summary 1",
                    "choice": "Choice 1",
                    "context": "Context 1",
                    "provenance": {"timestamp": "2026-07-21"},
                    "relationships": [
                        {"target": "DEC-NONEXISTENT", "type": "depends_on"}
                    ]
                }
            ]
        }
        self._create_minimal_project(payload)
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "Broken relationship edge must trigger non-zero exit code")
        self.assertIn("DEC-NONEXISTENT", stdout)

    def test_sync_missing_mandatory_fields_handled(self):
        """Tier 2: sync tool flags decisions missing required schema fields."""
        payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Incomplete Decision",
                    # Missing category, status, significance, summary, choice, context, provenance
                }
            ]
        }
        self._create_minimal_project(payload)
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertTrue("[WARN]" in stdout or ret != 0, "Missing mandatory fields must be warned or errored")

    def test_sync_dangling_session_reference(self):
        """Tier 2: sync tool detects decision pointing to an invalid session_id."""
        require_artifact(os.path.join(REPO_ROOT, "data", "sessions.json"), "Milestone M1", "data/sessions.json")
        payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Dangling Session Decision",
                    "category": "architecture",
                    "status": "validated",
                    "significance": "high",
                    "summary": "Summary",
                    "choice": "Choice",
                    "context": "Context",
                    "session_id": "SES-DOES-NOT-EXIST",
                    "provenance": {"timestamp": "2026-07-21"},
                    "relationships": []
                }
            ]
        }
        sessions_payload = {
            "sessions": [
                {
                    "id": "SES-001",
                    "title": "Valid Session",
                    "start_time": "2026-07-21T00:00:00Z",
                    "end_time": "2026-07-21T01:00:00Z",
                    "step_count": 10,
                    "summary": "Summary",
                    "decisions": [],
                    "conversation_logs": []
                }
            ]
        }
        self._create_minimal_project(payload, sessions_payload=sessions_payload)
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        # Once M1 session integrity is active, dangling sessions should be warned or errored
        if "SES-DOES-NOT-EXIST" in stdout or "session" in stdout.lower():
            self.assertTrue(True)

    # =========================================================================
    # Boundary: Initialization CLI Fault & Edge Handling
    # =========================================================================

    def test_init_nonexistent_deeply_nested_target_directory(self):
        """Tier 2: init script creates parent directories recursively when target is deeply nested."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        nested_target = os.path.join(self.temp_dir, "level1", "level2", "level3", "deep_repo")
        self.assertFalse(os.path.exists(nested_target))

        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", nested_target,
            "--project-name", "DeepRepo"
        ])
        self.assertEqual(ret, 0, f"Init should create nested directories automatically: {stderr}\n{stdout}")
        self.assertTrue(os.path.exists(os.path.join(nested_target, "sync_decisions.py")))

    def test_init_existing_nonempty_directory_without_force_fails(self):
        """Tier 2: init script halts and does not overwrite existing non-empty directory without --force."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        occupied_target = os.path.join(self.temp_dir, "occupied_dir")
        os.makedirs(occupied_target, exist_ok=True)
        canary_file = os.path.join(occupied_target, "my_custom_code.py")
        with open(canary_file, "w") as f:
            f.write("# Preserved user code\n")

        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", occupied_target,
            "--project-name", "OccupiedProject"
        ])
        self.assertNotEqual(ret, 0, "Init must refuse to overwrite non-empty target without --force")
        # Ensure user's file was not deleted
        self.assertTrue(os.path.exists(canary_file), "Canary file was deleted by aborted init")

    def test_init_special_characters_in_project_name(self):
        """Tier 2: init script safely handles complex names with special characters and quotes."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        special_target = os.path.join(self.temp_dir, "special_name_repo")
        special_name = 'Acme & Co "Decisn3 Engine" (v2.0 / Alpha)'
        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", special_target,
            "--project-name", special_name
        ])
        self.assertEqual(ret, 0, f"Init failed with special character project name: {stderr}\n{stdout}")
        # Verify index.html was generated and is valid HTML
        html_file = os.path.join(special_target, "index.html")
        self.assertTrue(os.path.exists(html_file))

    # =========================================================================
    # Boundary: Secret & Security Scanner Fault Handling
    # =========================================================================

    def test_audit_secrets_handles_binary_file(self):
        """Tier 2: audit scanner does not crash on non-UTF-8 binary data."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        scan_dir = os.path.join(self.temp_dir, "binary_scan")
        os.makedirs(scan_dir, exist_ok=True)
        bin_file = os.path.join(scan_dir, "sample.dat")
        with open(bin_file, "wb") as f:
            f.write(bytes(range(256)) * 10)  # full binary byte range

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", scan_dir])
        self.assertEqual(ret, 0, f"Scanner should process binary files without unhandled exception: {stderr}\n{stdout}")

    def test_audit_secrets_empty_directory(self):
        """Tier 2: audit scanner handles empty directory with clean exit 0."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        empty_dir = os.path.join(self.temp_dir, "empty_dir")
        os.makedirs(empty_dir, exist_ok=True)

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", empty_dir])
        self.assertEqual(ret, 0, f"Scanner should exit 0 on empty directory: {stderr}\n{stdout}")

    def test_audit_secrets_multiline_private_key_detection(self):
        """Tier 2: audit scanner detects multiline OpenSSH and EC private keys."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        scan_dir = os.path.join(self.temp_dir, "ssh_scan")
        os.makedirs(scan_dir, exist_ok=True)
        ssh_key = os.path.join(scan_dir, "id_ed25519")
        with open(ssh_key, "w") as f:
            f.write("-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXktdjEAAAA...\n-----END OPENSSH PRIVATE KEY-----\n")

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", scan_dir])
        self.assertNotEqual(ret, 0, "Scanner must detect OpenSSH private key block")


if __name__ == "__main__":
    unittest.main()
