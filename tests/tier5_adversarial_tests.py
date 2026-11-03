"""
Tier 5: Adversarial Coverage Hardening Test Suite (tier5_adversarial_tests.py)

White-box adversarial tests stress-testing boundary conditions, failure modes,
secret scanner resilience, schema validation, graph topology cycles, and
cross-project scaffolding edge cases.

Total tests: 16.
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
    APP_JS,
    INDEX_HTML,
    require_artifact,
    run_cmd,
    load_json_file,
    read_text_file,
)


class TestTier5AdversarialHardening(unittest.TestCase):
    """
    Tier 5: White-Box Adversarial Hardening Suite.
    Exhaustively stress-tests error paths, edge inputs, and fault conditions.
    """

    def setUp(self):
        """Set up isolated sandbox directory for each test."""
        self.temp_dir = tempfile.mkdtemp(prefix="dg_tier5_sandbox_")
        self.addCleanup(shutil.rmtree, self.temp_dir, ignore_errors=True)

    def _create_minimal_valid_project(self, target_dir):
        """Helper to create minimal valid project in target_dir."""
        data_dir = os.path.join(target_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        shutil.copy2(SYNC_SCRIPT, os.path.join(target_dir, "sync_decisions.py"))

        decisions_payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Minimal Seed Decision",
                    "category": "architecture",
                    "status": "implemented",
                    "significance": "foundational",
                    "summary": "Summary text",
                    "choice": "Choice text",
                    "context": "Context text",
                    "provenance": {
                        "source": "SRC-001",
                        "timestamp": "2026-11-03T10:00:00Z"
                    },
                    "session_id": "SES-001",
                    "epoch": 1,
                    "relationships": []
                }
            ]
        }
        with open(os.path.join(data_dir, "decisions.json"), "w", encoding="utf-8") as f:
            json.dump(decisions_payload, f, indent=2)

        sessions_payload = {
            "sessions": [
                {
                    "id": "SES-001",
                    "title": "Minimal Seed Session",
                    "start_time": "2026-11-03T10:00:00Z",
                    "end_time": "2026-11-03T11:00:00Z",
                    "step_count": 1,
                    "summary": "Session summary",
                    "decisions": ["DEC-001"],
                    "conversation_logs": []
                }
            ]
        }
        with open(os.path.join(data_dir, "sessions.json"), "w", encoding="utf-8") as f:
            json.dump(sessions_payload, f, indent=2)

        sources_payload = {
            "sources": [
                {
                    "id": "SRC-001",
                    "name": "Seed Source",
                    "path": "README.md",
                    "type": "documentation",
                    "accessible": True
                }
            ]
        }
        with open(os.path.join(data_dir, "sources.json"), "w", encoding="utf-8") as f:
            json.dump(sources_payload, f, indent=2)

    # =========================================================================
    # 1. Scaffolding Edge Cases
    # =========================================================================

    def test_01_adversarial_scaffolding_collision_and_force_override(self):
        """Tier 5: Scaffolding into non-empty directory fails without --force and preserves files; succeeds with --force."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        nested_target = os.path.join(self.temp_dir, "lvl1", "lvl2", "target_app")
        os.makedirs(nested_target, exist_ok=True)

        user_canary = os.path.join(nested_target, "user_canary_code.py")
        user_content = "# Critical user implementation code - must not be lost\nVAL = 42\n"
        with open(user_canary, "w", encoding="utf-8") as f:
            f.write(user_content)

        # 1. Attempt init without --force -> must fail
        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", nested_target,
            "--project-name", "CollisionTest"
        ])
        self.assertNotEqual(ret, 0, "Init must reject non-empty target directory without --force")
        self.assertIn("Use --force", stderr + stdout)
        # Verify user file is completely untouched
        self.assertTrue(os.path.exists(user_canary))
        self.assertEqual(read_text_file(user_canary), user_content)

        # 2. Attempt init with --force -> must succeed
        ret_force, stdout_force, stderr_force = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", nested_target,
            "--project-name", "CollisionTest",
            "--force"
        ])
        self.assertEqual(ret_force, 0, f"Init with --force must succeed: {stderr_force}\n{stdout_force}")
        self.assertTrue(os.path.exists(user_canary), "User canary file must not be removed by --force scaffolding")
        self.assertTrue(os.path.exists(os.path.join(nested_target, "data", "decisions.json")))
        self.assertTrue(os.path.exists(os.path.join(nested_target, "data", "data.js")))
        self.assertTrue(os.path.exists(os.path.join(nested_target, "index.html")))

        # 3. Verify target sync succeeds cleanly
        sync_script = os.path.join(nested_target, "sync_decisions.py")
        ret_sync, out_sync, err_sync = run_cmd([sys.executable, sync_script], cwd=nested_target)
        self.assertEqual(ret_sync, 0, f"Target sync failed after forced scaffolding: {err_sync}\n{out_sync}")

    def test_02_adversarial_scaffolding_malicious_xss_and_special_chars(self):
        """Tier 5: Scaffolding with malicious XSS and special characters safely escapes index.html."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        xss_target = os.path.join(self.temp_dir, "xss_scaffold_test")
        malicious_name = '<script>alert("XSS & Attack")</script> "Double" \'Single\' & Backslash \\'

        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            "--target", xss_target,
            "--project-name", malicious_name
        ])
        self.assertEqual(ret, 0, f"Init should handle special characters in project name: {stderr}\n{stdout}")

        # Check index.html escaping
        html_path = os.path.join(xss_target, "index.html")
        html_content = read_text_file(html_path)
        self.assertNotIn('<script>alert("XSS & Attack")</script>', html_content, "Raw unescaped script tag found in HTML")
        self.assertIn('&lt;script&gt;alert(&quot;XSS &amp; Attack&quot;)&lt;/script&gt;', html_content)

        # Check JSON files remain valid
        decisions_json = load_json_file(os.path.join(xss_target, "data", "decisions.json"))
        self.assertIn(malicious_name, decisions_json["decisions"][0]["context"])

        # Check sync produces valid data.js
        ret_sync, out_sync, err_sync = run_cmd([sys.executable, "sync_decisions.py"], cwd=xss_target)
        self.assertEqual(ret_sync, 0, f"Sync failed with special characters in seed: {err_sync}\n{out_sync}")

    def test_03_adversarial_scaffolding_missing_source_assets_graceful_failure(self):
        """Tier 5: scaffold_project handles missing source assets gracefully returning False."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        try:
            from init_decision_graph import scaffold_project
        except ImportError:
            sys.path.insert(0, REPO_ROOT)
            from init_decision_graph import scaffold_project

        empty_source = os.path.join(self.temp_dir, "empty_source_dir")
        os.makedirs(empty_source, exist_ok=True)
        dest_dir = os.path.join(self.temp_dir, "dest_dir")

        # scaffold_project should return False rather than raising unhandled exception
        result = scaffold_project(target_dir=dest_dir, source_dir=empty_source)
        self.assertFalse(result, "scaffold_project must return False when source assets are missing")

    def test_04_adversarial_scaffolding_cli_positional_target_parsing(self):
        """Tier 5: CLI correctly accepts target as positional argument without --target flag."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        pos_target = os.path.join(self.temp_dir, "positional_repo")

        ret, stdout, stderr = run_cmd([
            sys.executable, INIT_SCRIPT,
            pos_target,
            "--project-name", "PositionalTargetProject"
        ])
        self.assertEqual(ret, 0, f"Positional target argument must succeed: {stderr}\n{stdout}")
        self.assertTrue(os.path.exists(os.path.join(pos_target, "sync_decisions.py")))
        self.assertTrue(os.path.exists(os.path.join(pos_target, "data", "data.js")))

    # =========================================================================
    # 2. Secret Scanner Edge Cases
    # =========================================================================

    def test_05_adversarial_secret_scanner_pem_mutations(self):
        """Tier 5: Secret scanner flags all variants and mutations of cryptographic private key headers."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        scan_dir = os.path.join(self.temp_dir, "pem_mutations")
        os.makedirs(scan_dir, exist_ok=True)

        # Build headers dynamically to prevent tripping static scans on this test file
        pem_variants = {
            "dsa_key.txt": "-----" + "BEGIN DSA PRIVATE " + "KEY-----\n",
            "lowercase_ec.txt": "-----" + "begin ec private " + "key-----\n",
            "encrypted.txt": "-----" + "BEGIN ENCRYPTED PRIVATE " + "KEY-----\n",
            "multiple_spaces.txt": "-----" + "BEGIN   PRIVATE   " + "KEY-----\n",
            "openssh.txt": "-----" + "BEGIN OPENSSH PRIVATE " + "KEY-----\n",
        }

        for filename, content in pem_variants.items():
            with open(os.path.join(scan_dir, filename), "w", encoding="utf-8") as f:
                f.write(content)

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", scan_dir])
        self.assertEqual(ret, 1, "Scanner must exit 1 when private keys are present")

        for filename in pem_variants.keys():
            self.assertIn(filename, stdout, f"Scanner failed to flag {filename}")

    def test_06_adversarial_secret_scanner_api_tokens_and_code_pattern_whitelist(self):
        """Tier 5: Secret scanner flags genuine API tokens but whitelists Python regex pattern definitions."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        scan_dir = os.path.join(self.temp_dir, "token_and_whitelist")
        os.makedirs(scan_dir, exist_ok=True)

        # Real token candidates (dynamically assembled)
        tokens = {
            "openai.env": "OPENAI_API_KEY=" + "s" + "k-proj-abc1234567890abcdef1234567890abcdef12345\n",
            "github.env": "GH_TOKEN=" + "g" + "ithub_pat_11ABCD123456789012345678901234567890123456789012345678901234567890\n",
            "google.env": "GOOGLE_KEY=" + "A" + "IzaSyD1234567890abcdef1234567890123456\n",
            "aws.env": "AWS_KEY=" + "A" + "KIAIOSFODNN7EXAMPLE\n",
            "slack.env": "SLACK_TOKEN=" + "x" + "oxb-123456789012-1234567890123-abcdefghijklmnopqrstuvwx\n"
        }

        for filename, content in tokens.items():
            with open(os.path.join(scan_dir, filename), "w", encoding="utf-8") as f:
                f.write(content)

        # Python regex pattern definition file (should NOT be flagged due to is_sanitizer_or_pattern_def)
        whitelist_py = os.path.join(scan_dir, "sanitizer_patterns.py")
        with open(whitelist_py, "w", encoding="utf-8") as f:
            f.write("import re\n")
            f.write("RE_TOKEN = re.compile(r'\\bs" + "k-[a-zA-Z0-9_-]{20,}\\b')\n")
            f.write("def clean(text):\n")
            f.write("    return re.sub(r'g" + "hp_[a-zA-Z0-9]{36,}', '[REDACTED]', text)\n")

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", scan_dir])
        self.assertEqual(ret, 1, "Scanner must exit 1 on detected API tokens")

        for filename in tokens.keys():
            self.assertIn(filename, stdout, f"Scanner missed token in {filename}")

        # Ensure sanitizer_patterns.py was whitelisted and NOT flagged
        self.assertNotIn("sanitizer_patterns.py", stdout, "Pattern definition lines in Python must not be false positives")

    def test_07_adversarial_secret_scanner_deep_directory_nesting_and_skips(self):
        """Tier 5: Secret scanner recursively finds secrets 10 levels deep and skips ignored directory trees."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        deep_root = os.path.join(self.temp_dir, "deep_root")
        current_dir = deep_root
        for i in range(1, 11):
            current_dir = os.path.join(current_dir, f"lvl_{i}")
        os.makedirs(current_dir, exist_ok=True)

        deep_secret_file = os.path.join(current_dir, "buried_secret.txt")
        with open(deep_secret_file, "w", encoding="utf-8") as f:
            f.write("SECRET=" + "s" + "k-proj-deep1234567890abcdef1234567890\n")

        # Create fake secret in skipped directories
        for skip_dir_name in [".git", "node_modules", "__pycache__", ".venv", ".agents"]:
            skip_dir = os.path.join(deep_root, skip_dir_name)
            os.makedirs(skip_dir, exist_ok=True)
            with open(os.path.join(skip_dir, "ignored_secret.txt"), "w", encoding="utf-8") as f:
                f.write("IGNORE_ME=" + "s" + "k-proj-ignored1234567890abcdef1234567890\n")

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", deep_root])
        self.assertEqual(ret, 1, "Scanner must detect buried secret")
        self.assertIn("buried_secret.txt", stdout)

        # None of the skipped directories should appear in violations
        for skip_dir_name in [".git", "node_modules", "__pycache__", ".venv", ".agents"]:
            self.assertNotIn(skip_dir_name, stdout, f"Directory {skip_dir_name} should have been skipped")

    def test_08_adversarial_secret_scanner_binary_null_bytes_and_encodings(self):
        """Tier 5: Secret scanner identifies binary null bytes and non-standard text encodings without crashing."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        bin_dir = os.path.join(self.temp_dir, "binary_encoding_test")
        os.makedirs(bin_dir, exist_ok=True)

        # 1. Null-byte file without extension
        with open(os.path.join(bin_dir, "raw_chunk.data"), "wb") as f:
            f.write(b"PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + (b"s" + b"k-1234567890abcdef1234567890abcdef"))

        # 2. Known binary extension
        with open(os.path.join(bin_dir, "sample.png"), "wb") as f:
            f.write(b"fake image bytes \x00\x01\x02\x03")

        # 3. UTF-16 LE encoded text (contains null bytes for ASCII chars)
        with open(os.path.join(bin_dir, "utf16_text.txt"), "wb") as f:
            f.write(("Secret token: " + "s" + "k-1234567890abcdef1234567890").encode("utf-16le"))

        # 4. Text with invalid UTF-8 bytes (processed safely via errors='replace')
        with open(os.path.join(bin_dir, "corrupt_utf8.txt"), "wb") as f:
            f.write(b"\xff\xfe\x80\x81 Clean text without secrets\n")

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", bin_dir])
        # Binary files must be skipped and corrupted text handled cleanly
        self.assertEqual(ret, 0, f"Scanner should process all binary/corrupt files without error: {stderr}\n{stdout}")
        self.assertIn("[PASS]", stdout)

    def test_09_adversarial_secret_scanner_mixed_slashes_and_local_paths(self):
        """Tier 5: Secret scanner flags all variations of absolute local user filesystem paths."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        path_dir = os.path.join(self.temp_dir, "path_scan_test")
        os.makedirs(path_dir, exist_ok=True)

        test_paths = {
            "win_std.txt": "Path: C" + ":\\Users\\" + "developer_one\\project\n",
            "win_url.json": '{"path": "file:///c' + '%3a/Users/' + 'developer_two/repo"}\n',
            "win_mixed_slash.txt": "Target: C" + ":\\/Users/\\developer_three\\app\n",
            "win_escaped.json": '{"dir": "C' + ':\\\\\\\\Users\\\\\\\\developer_four"}\n',
            "unix_home.txt": "Working dir: " + "/home/" + "developer_five/workspace\n",
            "macos_users.txt": "Home dir: " + "/Users/" + "developer_six/Documents\n",
        }

        for filename, content in test_paths.items():
            with open(os.path.join(path_dir, filename), "w", encoding="utf-8") as f:
                f.write(content)

        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", path_dir])
        self.assertEqual(ret, 1, "Scanner must exit 1 when local user paths are detected")

        for filename in test_paths.keys():
            self.assertIn(filename, stdout, f"Scanner missed local path in {filename}")

    # =========================================================================
    # 3. Sync Tool Edge Cases
    # =========================================================================

    def test_10_adversarial_sync_duplicate_session_ids_rejection(self):
        """Tier 5: sync_decisions.py detects and rejects duplicate session IDs with non-zero exit."""
        self._create_minimal_valid_project(self.temp_dir)
        sessions_file = os.path.join(self.temp_dir, "data", "sessions.json")

        payload = {
            "sessions": [
                {
                    "id": "SES-001",
                    "title": "Session One",
                    "start_time": "2026-11-03T10:00:00Z",
                    "end_time": "2026-11-03T11:00:00Z",
                    "step_count": 1,
                    "summary": "Session summary",
                    "decisions": ["DEC-001"]
                },
                {
                    "id": "SES-001",  # duplicate ID
                    "title": "Session One Duplicate",
                    "start_time": "2026-11-03T11:00:00Z",
                    "end_time": "2026-11-03T12:00:00Z",
                    "step_count": 2,
                    "summary": "Duplicate summary",
                    "decisions": []
                }
            ]
        }
        with open(sessions_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "Sync must reject duplicate session IDs")
        self.assertIn("Duplicate Session IDs found", stdout + stderr)

    def test_11_adversarial_sync_orphan_decisions_and_broken_edges(self):
        """Tier 5: sync_decisions.py detects unmapped decisions, invalid session refs, and broken edges."""
        self._create_minimal_valid_project(self.temp_dir)
        decisions_file = os.path.join(self.temp_dir, "data", "decisions.json")
        sessions_file = os.path.join(self.temp_dir, "data", "sessions.json")
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")

        # 1. Unmapped decision pointing to non-existent session
        bad_decision_payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Orphan Decision",
                    "category": "architecture",
                    "status": "implemented",
                    "significance": "foundational",
                    "summary": "Summary",
                    "choice": "Choice",
                    "context": "Context",
                    "provenance": {"source": "SRC-001"},
                    "session_id": "SES-NONEXISTENT",
                    "epoch": 1,
                    "relationships": []
                }
            ]
        }
        with open(decisions_file, "w", encoding="utf-8") as f:
            json.dump(bad_decision_payload, f, indent=2)

        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "Sync must fail when decision references non-existent session")
        self.assertIn("unmapped", stdout.lower() + stderr.lower())

        # 2. Session referencing non-existent decision
        self._create_minimal_valid_project(self.temp_dir)
        bad_sessions_payload = {
            "sessions": [
                {
                    "id": "SES-001",
                    "title": "Valid Session",
                    "start_time": "2026-11-03T10:00:00Z",
                    "end_time": "2026-11-03T11:00:00Z",
                    "step_count": 1,
                    "summary": "Summary",
                    "decisions": ["DEC-001", "DEC-NONEXISTENT-TARGET"]
                }
            ]
        }
        with open(sessions_file, "w", encoding="utf-8") as f:
            json.dump(bad_sessions_payload, f, indent=2)

        ret2, stdout2, stderr2 = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret2, 0, "Sync must fail when session references non-existent decision")
        self.assertIn("non-existent decisions", stdout2 + stderr2)

    def test_12_adversarial_sync_missing_mandatory_schema_fields(self):
        """Tier 5: sync_decisions.py detects and warns/fails on missing mandatory schema fields."""
        self._create_minimal_valid_project(self.temp_dir)
        decisions_file = os.path.join(self.temp_dir, "data", "decisions.json")
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")

        # Missing 'epoch' field on decision
        incomplete_payload = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Incomplete Decision",
                    "category": "architecture",
                    "status": "implemented",
                    "significance": "foundational",
                    "summary": "Summary",
                    "choice": "Choice",
                    "context": "Context",
                    "provenance": {"source": "SRC-001"},
                    "session_id": "SES-001",
                    # 'epoch' is missing!
                    "relationships": []
                }
            ]
        }
        with open(decisions_file, "w", encoding="utf-8") as f:
            json.dump(incomplete_payload, f, indent=2)

        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertNotEqual(ret, 0, "Missing mandatory field 'epoch' must cause sync to fail")
        self.assertIn("missing field 'epoch'", stdout + stderr)

    def test_13_adversarial_sync_cyclic_graph_and_unknown_fields(self):
        """Tier 5: sync_decisions.py handles directed graph cycles and extra custom fields without crashing."""
        self._create_minimal_valid_project(self.temp_dir)
        decisions_file = os.path.join(self.temp_dir, "data", "decisions.json")
        sessions_file = os.path.join(self.temp_dir, "data", "sessions.json")
        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")

        # Cyclic dependency: DEC-001 -> DEC-002 -> DEC-003 -> DEC-001
        cyclic_decisions = {
            "decisions": [
                {
                    "id": "DEC-001",
                    "title": "Decision One",
                    "category": "architecture",
                    "status": "implemented",
                    "significance": "foundational",
                    "summary": "Summary 1",
                    "choice": "Choice 1",
                    "context": "Context 1",
                    "provenance": {"source": "SRC-001"},
                    "session_id": "SES-001",
                    "epoch": 1,
                    "custom_vendor_metadata": {"enterprise_tier": "gold"},
                    "relationships": [{"target": "DEC-002", "type": "depends_on"}]
                },
                {
                    "id": "DEC-002",
                    "title": "Decision Two",
                    "category": "infrastructure",
                    "status": "implemented",
                    "significance": "high",
                    "summary": "Summary 2",
                    "choice": "Choice 2",
                    "context": "Context 2",
                    "provenance": {"source": "SRC-001"},
                    "session_id": "SES-001",
                    "epoch": 2,
                    "custom_vendor_metadata": {"enterprise_tier": "silver"},
                    "relationships": [{"target": "DEC-003", "type": "depends_on"}]
                },
                {
                    "id": "DEC-003",
                    "title": "Decision Three",
                    "category": "security",
                    "status": "implemented",
                    "significance": "medium",
                    "summary": "Summary 3",
                    "choice": "Choice 3",
                    "context": "Context 3",
                    "provenance": {"source": "SRC-001"},
                    "session_id": "SES-001",
                    "epoch": 3,
                    "relationships": [{"target": "DEC-001", "type": "depends_on"}]  # cycle back
                }
            ]
        }
        with open(decisions_file, "w", encoding="utf-8") as f:
            json.dump(cyclic_decisions, f, indent=2)

        sessions_payload = {
            "sessions": [
                {
                    "id": "SES-001",
                    "title": "Session for Cyclic Graph",
                    "start_time": "2026-11-03T10:00:00Z",
                    "end_time": "2026-11-03T11:00:00Z",
                    "step_count": 3,
                    "summary": "Cyclic session",
                    "decisions": ["DEC-001", "DEC-002", "DEC-003"],
                    "custom_session_annotation": "valid extra property"
                }
            ]
        }
        with open(sessions_file, "w", encoding="utf-8") as f:
            json.dump(sessions_payload, f, indent=2)

        ret, stdout, stderr = run_cmd([sys.executable, sync_script], cwd=self.temp_dir)
        self.assertEqual(ret, 0, f"Sync should succeed with cyclic valid edges and extra fields: {stderr}\n{stdout}")

        # Verify data.js contains the compiled output and custom properties
        data_js = read_text_file(os.path.join(self.temp_dir, "data", "data.js"))
        self.assertIn("window.DECISN3_DATA =", data_js)
        self.assertIn("enterprise_tier", data_js)
        self.assertIn("custom_session_annotation", data_js)

    def test_14_adversarial_sync_dry_run_validate_only_mode(self):
        """Tier 5: sync_decisions.py --validate-only validates data without generating data/data.js."""
        self._create_minimal_valid_project(self.temp_dir)
        data_js = os.path.join(self.temp_dir, "data", "data.js")
        if os.path.exists(data_js):
            os.remove(data_js)

        sync_script = os.path.join(self.temp_dir, "sync_decisions.py")
        ret, stdout, stderr = run_cmd([
            sys.executable, sync_script,
            "--validate-only"
        ], cwd=self.temp_dir)

        self.assertEqual(ret, 0, f"Validate-only mode should exit 0 on valid data: {stderr}\n{stdout}")
        self.assertIn("--validate-only specified", stdout)
        self.assertFalse(os.path.exists(data_js), "data/data.js must NOT be generated when --validate-only is passed")

    # =========================================================================
    # 4. Security Sanitization Edge Cases
    # =========================================================================

    def test_15_adversarial_security_sanitization_comprehensive_matrix(self):
        """Tier 5: sanitize_path cleanses all drive casing, URL encoding, escaped slashes, and Unix paths."""
        try:
            from sync_decisions import sanitize_path
        except ImportError:
            sys.path.insert(0, REPO_ROOT)
            from sync_decisions import sanitize_path

        test_cases = [
            ("C:" + "\\Users\\" + "developer\\documents\\secret.txt", "~/workspace/documents\\secret.txt"),
            ("c%3A" + "/Users/" + "developer/project/file.js", "~/workspace/project/file.js"),
            ("C%3a" + "\\Users\\" + "developer\\data", "~/workspace/data"),
            ("c:" + "\\\\\\\\Users\\\\\\\\" + "developer\\\\\\\\app", "~/workspace"),
            ("/" + "home/" + "dev_user/project/README.md", "~/workspace/project/README.md"),
            ("/" + "Users/" + "mac_user/Documents/notes.txt", "~/workspace/Documents/notes.txt"),
            ("", ""),
            (None, ""),
        ]

        for input_text, expected_fragment in test_cases:
            result = sanitize_path(input_text)
            self.assertNotIn("developer", result, f"Username leaked in sanitized output: {result}")
            self.assertNotIn("dev_user", result, f"Username leaked in sanitized output: {result}")
            self.assertNotIn("mac_user", result, f"Username leaked in sanitized output: {result}")
            if input_text:
                self.assertIn("~/workspace", result, f"Expected ~/workspace replacement for: {input_text}")
            else:
                self.assertEqual(result, "")

    # =========================================================================
    # 5. Web UI Application & Layout Contracts
    # =========================================================================

    def test_16_adversarial_app_js_and_html_resilience_contracts(self):
        """Tier 5: app.js contains robust fallbacks for unknown categories, empty sessions, and themes."""
        app_js_content = read_text_file(APP_JS)
        index_html_content = read_text_file(INDEX_HTML)

        # 1. Category fallback check: Y coordinate and color fallbacks exist
        self.assertIn("categoryYMap[d.category] !== undefined ? categoryYMap[d.category] : 0", app_js_content)
        self.assertIn("CATEGORY_COLORS[d.category] ||", app_js_content)

        # 2. Automation category explicitly supported
        self.assertIn("automation:", app_js_content)

        # 3. Empty sessions guard in populateSessionFilters
        self.assertIn("sessions.length > 0", app_js_content)

        # 4. Theme switching contract in HTML and app.js
        self.assertIn('id="theme-toggle"', index_html_content)
        self.assertIn("data-theme", app_js_content)
        self.assertIn("decisn3_theme", app_js_content)


if __name__ == "__main__":
    unittest.main()
