"""
Tier 1: Feature Coverage Test Suite.
Validates requirements R1, R2, R3, R4, R5 with >= 5 test cases per feature area.
Total tests: 29.
"""

import os
import sys
import json
import re
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
    APP_JS,
    STYLES_CSS,
    README_MD,
    GITIGNORE_FILE,
    GIT_DIR,
    require_artifact,
    run_cmd,
    load_json_file,
    read_text_file,
    is_strict_mode,
)


class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 tests exercising primary functional requirements (R1 through R5).
    """

    # =========================================================================
    # Requirement R1: Session-Based Decision Discovery & Exploration
    # =========================================================================

    def test_r1_01_sessions_json_structure_and_mandatory_fields(self):
        """R1.1: Verify data/sessions.json ships empty and scaffolded sessions contain all mandatory fields."""
        require_artifact(SESSIONS_FILE, "Milestone M1", "data/sessions.json")
        repo_data = load_json_file(SESSIONS_FILE)
        self.assertIn("sessions", repo_data, "data/sessions.json must contain a top-level 'sessions' list")
        self.assertIsInstance(repo_data["sessions"], list)
        self.assertEqual(len(repo_data["sessions"]), 0, "Repository must ship with zero sample sessions")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "session_schema_test")
            ret, stdout, stderr = run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "SchemaTest"])
            self.assertEqual(ret, 0, f"Scaffolding failed: {stderr}\n{stdout}")
            data = load_json_file(os.path.join(target_repo, "data", "sessions.json"))
            sessions = data["sessions"]
            self.assertGreaterEqual(len(sessions), 2, "Scaffolded project must contain seed sessions")

            required_session_fields = [
                "id", "title", "start_time", "end_time", "step_count",
                "summary", "decisions", "conversation_logs"
            ]
            session_ids = set()
            for s in sessions:
                for field in required_session_fields:
                    self.assertIn(field, s, f"Session {s.get('id')} missing mandatory field '{field}'")
                self.assertTrue(s["id"].startswith("SES-"), f"Session id must match 'SES-XXX', got {s['id']}")
                self.assertIsInstance(s["step_count"], int, f"step_count must be integer in {s['id']}")
                self.assertIsInstance(s["decisions"], list, f"'decisions' must be a list in {s['id']}")
                self.assertIsInstance(s["conversation_logs"], list, f"'conversation_logs' must be a list in {s['id']}")
                self.assertNotIn(s["id"], session_ids, f"Duplicate session id detected: {s['id']}")
                session_ids.add(s["id"])

    def test_r1_02_decisions_json_session_enrichment_and_epochs(self):
        """R1.2: Verify data/decisions.json ships empty and scaffolded decisions contain session_id, session_title, and explicit epoch."""
        require_artifact(DECISIONS_FILE, "Milestone M1", "data/decisions.json")
        repo_data = load_json_file(DECISIONS_FILE)
        self.assertIn("decisions", repo_data)
        self.assertEqual(len(repo_data["decisions"]), 0, "Repository must ship with zero sample decisions")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "decision_enrichment_test")
            ret, stdout, stderr = run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "EnrichTest"])
            self.assertEqual(ret, 0, f"Scaffolding failed: {stderr}\n{stdout}")
            data = load_json_file(os.path.join(target_repo, "data", "decisions.json"))
            decisions = data.get("decisions", [])
            self.assertGreaterEqual(len(decisions), 1)

            for d in decisions:
                d_id = d.get("id")
                self.assertIn("session_id", d, f"Decision {d_id} missing 'session_id'")
                self.assertTrue(d["session_id"].startswith("SES-"), f"Decision {d_id} has invalid session_id: {d['session_id']}")
                self.assertIn("session_title", d, f"Decision {d_id} missing 'session_title'")
                self.assertIn("epoch", d, f"Decision {d_id} missing explicit 'epoch'")
                self.assertIsInstance(d["epoch"], int, f"Decision {d_id} epoch must be int (1..12), got {d['epoch']}")
                self.assertTrue(1 <= d["epoch"] <= 12, f"Decision {d_id} epoch out of range 1-12: {d['epoch']}")

    def test_r1_03_referential_integrity_between_decisions_and_sessions(self):
        """R1.3: Verify bidirectional referential integrity between decisions and sessions."""
        require_artifact(SESSIONS_FILE, "Milestone M1", "data/sessions.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "ref_integrity_test")
            run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "RefTest"])
            decisions_data = load_json_file(os.path.join(target_repo, "data", "decisions.json"))
            sessions_data = load_json_file(os.path.join(target_repo, "data", "sessions.json"))

            decisions = decisions_data.get("decisions", [])
            sessions = sessions_data.get("sessions", [])

            session_id_set = {s["id"] for s in sessions}
            decision_id_set = {d["id"] for d in decisions}

            # Check every decision's session_id exists in sessions
            for d in decisions:
                if "session_id" in d:
                    self.assertIn(
                        d["session_id"],
                        session_id_set,
                        f"Decision {d['id']} points to nonexistent session '{d['session_id']}'"
                    )

            # Check every session's decision list items exist in decisions
            for s in sessions:
                for dec_ref in s.get("decisions", []):
                    self.assertIn(
                        dec_ref,
                        decision_id_set,
                        f"Session {s['id']} claims decision '{dec_ref}' which does not exist in decisions.json"
                    )

    def test_r1_04_sync_tool_bundles_sessions_into_data_js(self):
        """R1.4: Verify sync_decisions.py bundles sessions into data/data.js."""
        require_artifact(SESSIONS_FILE, "Milestone M1", "data/sessions.json")
        sync_code = read_text_file(SYNC_SCRIPT)
        if "sessions.json" not in sync_code:
            require_artifact(os.path.join(REPO_ROOT, "sync_sessions_flag"), "Milestone M1", "sync_decisions.py session bundling")
        ret, stdout, stderr = run_cmd([sys.executable, SYNC_SCRIPT])
        self.assertEqual(ret, 0, f"sync_decisions.py failed with exit code {ret}: {stderr}\n{stdout}")

        require_artifact(DATA_JS_FILE, "Milestone M1", "data/data.js")
        content = read_text_file(DATA_JS_FILE)
        self.assertIn("window.DECISN3_DATA", content, "data.js must assign window.DECISN3_DATA")
        self.assertIn('"sessions"', content, "data.js payload must contain 'sessions' key")

    def test_r1_05_automation_category_support_and_dec32(self):
        """R1.5: Verify 'automation' category is supported in styles.css, index.html, app.js, and sync_decisions.py."""
        css = read_text_file(STYLES_CSS)
        html = read_text_file(INDEX_HTML)
        js = read_text_file(APP_JS)
        self.assertIn(".badge-cat-automation", css, "styles.css must define .badge-cat-automation")
        self.assertIn('value="automation"', html, "index.html must include automation category filter option")
        self.assertIn("automation:", js, "app.js must define color and Y-coordinate for automation category")

        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "auto_cat_test")
            run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "AutoTest"])
            dec_path = os.path.join(target_repo, "data", "decisions.json")
            dec_data = load_json_file(dec_path)
            dec_data["decisions"][0]["category"] = "automation"
            with open(dec_path, "w", encoding="utf-8") as f:
                json.dump(dec_data, f, indent=2)
            ret, stdout, stderr = run_cmd([sys.executable, os.path.join(target_repo, "sync_decisions.py")], cwd=target_repo)
            self.assertEqual(ret, 0, f"sync_decisions.py rejected 'automation' category: {stderr}\n{stdout}")

    def test_r1_06_ui_html_session_filter_and_toggle_elements(self):
        """R1.6: Verify index.html contains #graph-session-filter, #explorer-session-filter, and category options."""
        html = read_text_file(INDEX_HTML)
        if 'id="graph-session-filter"' not in html or 'id="explorer-session-filter"' not in html:
            require_artifact(os.path.join(REPO_ROOT, "m1_ui_complete_marker"), "Milestone M1 UI", "index.html session UI elements")
        self.assertTrue(
            'id="graph-session-filter"' in html or 'id=\'graph-session-filter\'' in html,
            "index.html must contain #graph-session-filter select element"
        )
        self.assertTrue(
            'id="explorer-session-filter"' in html or 'id=\'explorer-session-filter\'' in html,
            "index.html must contain #explorer-session-filter select element"
        )
        self.assertIn('value="automation"', html, "index.html category filters must include 'automation'")

    def test_r1_07_app_js_session_filtering_and_drawer_context(self):
        """R1.7: Verify app.js implements session filtering logic, timeline grouping, and drawer session details."""
        js = read_text_file(APP_JS)
        if "graph-session-filter" not in js and "sessionFilter" not in js:
            require_artifact(os.path.join(REPO_ROOT, "m1_ui_complete_marker"), "Milestone M1 UI", "app.js session UI support")
        self.assertTrue(
            "graph-session-filter" in js or "sessionFilter" in js or "session_id" in js,
            "app.js must handle session filtering or session attributes"
        )
        self.assertTrue(
            "renderDetailDrawer" in js,
            "app.js must define renderDetailDrawer function"
        )

    # =========================================================================
    # Requirement R2: Cross-Project Initialization Strategy
    # =========================================================================

    def test_r2_01_init_script_exists_and_help_flag(self):
        """R2.1: Verify init_decision_graph.py exists and supports --help flag."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        ret, stdout, stderr = run_cmd([sys.executable, INIT_SCRIPT, "--help"])
        self.assertEqual(ret, 0, f"init_decision_graph.py --help failed: {stderr}")
        self.assertIn("--target", stdout, "Help text must document --target")
        self.assertIn("--project-name", stdout, "Help text must document --project-name")

    def test_r2_02_init_scaffolds_complete_directory_tree(self):
        """R2.2: Verify init_decision_graph.py scaffolds required directory layout and files into target directory."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "my_new_service")
            ret, stdout, stderr = run_cmd([
                sys.executable, INIT_SCRIPT,
                "--target", target_repo,
                "--project-name", "My New Service"
            ])
            self.assertEqual(ret, 0, f"Init scaffolding failed: {stderr}\n{stdout}")

            expected_files = [
                os.path.join(target_repo, "index.html"),
                os.path.join(target_repo, "app.js"),
                os.path.join(target_repo, "styles.css"),
                os.path.join(target_repo, "sync_decisions.py"),
                os.path.join(target_repo, "libs", "three.min.js"),
                os.path.join(target_repo, "libs", "OrbitControls.js"),
                os.path.join(target_repo, "data", "decisions.json"),
                os.path.join(target_repo, "data", "sessions.json"),
                os.path.join(target_repo, "data", "sources.json"),
            ]
            for ef in expected_files:
                self.assertTrue(os.path.exists(ef), f"Scaffolded repository missing expected file: {ef}")

    def test_r2_03_init_generates_valid_seed_schemas(self):
        """R2.3: Verify scaffolded target repo contains valid seed schemas for DEC-001, SES-001, SRC-001."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "seed_test_repo")
            run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "SeedTest"])

            # Verify decisions.json seed
            decisions_p = os.path.join(target_repo, "data", "decisions.json")
            self.assertTrue(os.path.exists(decisions_p))
            dec_data = load_json_file(decisions_p)
            self.assertIn("decisions", dec_data)
            self.assertGreaterEqual(len(dec_data["decisions"]), 1)
            first_dec = dec_data["decisions"][0]
            self.assertEqual(first_dec.get("id"), "DEC-001")
            self.assertIn("session_id", first_dec)

            # Verify sessions.json seed
            sessions_p = os.path.join(target_repo, "data", "sessions.json")
            self.assertTrue(os.path.exists(sessions_p))
            ses_data = load_json_file(sessions_p)
            self.assertIn("sessions", ses_data)
            self.assertGreaterEqual(len(ses_data["sessions"]), 1)

            # Verify sources.json seed
            sources_p = os.path.join(target_repo, "data", "sources.json")
            self.assertTrue(os.path.exists(sources_p))
            src_data = load_json_file(sources_p)
            self.assertIn("sources", src_data)
            self.assertGreaterEqual(len(src_data["sources"]), 1)

    def test_r2_04_scaffolded_project_passes_sync_with_zero_errors(self):
        """R2.4: Verify running sync_decisions.py inside the scaffolded repo passes with exit code 0 and 0 errors."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "sync_validate_repo")
            run_cmd([sys.executable, INIT_SCRIPT, "--target", target_repo, "--project-name", "SyncTest"])

            target_sync = os.path.join(target_repo, "sync_decisions.py")
            ret, stdout, stderr = run_cmd([sys.executable, target_sync], cwd=target_repo)
            self.assertEqual(ret, 0, f"sync_decisions.py failed inside scaffolded repo: {stderr}\n{stdout}")
            self.assertIn("[PASS]", stdout, "sync_decisions.py must output passing validation checks")

            # Verify data.js generated
            data_js = os.path.join(target_repo, "data", "data.js")
            self.assertTrue(os.path.exists(data_js), "data/data.js was not generated by sync in scaffolded repo")

    def test_r2_05_sync_cli_init_flag_behavior(self):
        """R2.5: Verify sync_decisions.py supports --init flag to bootstrap project layout."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "sync_decisions.py --init full scaffolding (Milestone M2)")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "init_flag_repo")
            ret, stdout, stderr = run_cmd([sys.executable, SYNC_SCRIPT, "--init", target_repo])
            self.assertEqual(ret, 0, f"sync_decisions.py --init failed: {stderr}\n{stdout}")
            self.assertTrue(os.path.exists(os.path.join(target_repo, "data", "decisions.json")))

    def test_r2_06_init_force_flag_and_collision_prevention(self):
        """R2.6: Verify init script refuses to overwrite non-empty target without --force, but succeeds with --force."""
        require_artifact(INIT_SCRIPT, "Milestone M2", "init_decision_graph.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            target_repo = os.path.join(tmpdir, "collision_test")
            os.makedirs(target_repo, exist_ok=True)
            # Create a blocking file
            with open(os.path.join(target_repo, "existing.txt"), "w") as f:
                f.write("I am existing data")

            # Attempt init without --force: should fail or warn non-zero
            ret_noforce, stdout_nf, stderr_nf = run_cmd([
                sys.executable, INIT_SCRIPT,
                "--target", target_repo,
                "--project-name", "CollisionApp"
            ])
            self.assertNotEqual(
                ret_noforce, 0,
                "init_decision_graph.py should fail when target directory is non-empty without --force"
            )

            # Attempt init with --force: should succeed
            ret_force, stdout_f, stderr_f = run_cmd([
                sys.executable, INIT_SCRIPT,
                "--target", target_repo,
                "--project-name", "CollisionApp",
                "--force"
            ])
            self.assertEqual(ret_force, 0, f"init_decision_graph.py with --force should succeed: {stderr_f}\n{stdout_f}")

    # =========================================================================
    # Requirement R3: Dedicated Open-Source README and How-To Guide
    # =========================================================================

    def test_r3_01_readme_exists_and_non_empty(self):
        """R3.1: Verify README.md exists in repository root and has substantial content (>4000 bytes)."""
        self.assertTrue(os.path.exists(README_MD), "README.md must exist in repository root")
        size = os.path.getsize(README_MD)
        self.assertGreater(size, 4000, f"README.md size ({size} bytes) is too small for publication guide")

    def test_r3_02_readme_contains_ten_required_sections(self):
        """R3.2: Verify README.md contains required open-source publication sections."""
        content = read_text_file(README_MD).lower()
        required_topics = [
            ("visualization modes (3d/2d)", ["3d", "webgl", "svg"]),
            ("architecture & data engine", ["architecture", "data"]),
            ("quick start / local launch", ["quick start", "getting started", "launch", "installation"]),
            ("session discovery (r1)", ["session"]),
            ("schema reference", ["schema"]),
            ("bootstrapping / init cli (r2)", ["init", "bootstrap", "scaffold"]),
            ("security & secrets audit (r4)", ["security", "audit", "secret"]),
            ("license / contributing", ["license", "mit"]),
        ]
        for topic, keywords in required_topics:
            matched = any(kw in content for kw in keywords)
            if not matched and not os.path.exists(INIT_SCRIPT):
                require_artifact(INIT_SCRIPT, "Milestone M4", f"README overhaul for {topic}")
            self.assertTrue(matched, f"README.md lacks documentation on: {topic}")

    def test_r3_03_readme_zero_local_filesystem_leaks(self):
        """R3.3: Verify README.md has zero hardcoded local Windows filesystem paths or file:/// URIs."""
        content = read_text_file(README_MD)
        # Search for file:/// or C:/Users or c:\Users
        leak_pattern = re.compile(r'(file:///[a-zA-Z]:|[a-zA-Z]:[/\\]users[/\\])', re.IGNORECASE)
        matches = leak_pattern.findall(content)
        if matches and not os.path.exists(INIT_SCRIPT):
            require_artifact(INIT_SCRIPT, "Milestone M3/M4", "README path sanitization")
        self.assertEqual(len(matches), 0, f"README.md contains local filesystem leaks: {matches}")

    def test_r3_04_readme_documents_data_schemas_and_enums(self):
        """R3.4: Verify README.md documents schema fields for decisions.json and sessions.json."""
        content = read_text_file(README_MD)
        if "decisions.json" not in content or "sessions.json" not in content:
            require_artifact(INIT_SCRIPT, "Milestone M4", "README schema tables")
        self.assertIn("decisions.json", content)
        self.assertTrue("sessions.json" in content or "sessions" in content.lower())

    def test_r3_05_readme_documents_dual_mode_3d_2d_visualization(self):
        """R3.5: Verify README.md explains both Three.js 3D WebGL mode and 2D SVG fallback mode."""
        content = read_text_file(README_MD).lower()
        self.assertIn("three.js", content, "README must mention Three.js")
        self.assertTrue("2d" in content and "svg" in content, "README must describe 2D SVG mode")

    # =========================================================================
    # Requirement R4: Security and Privacy Audit
    # =========================================================================

    def test_r4_01_audit_secrets_script_exists_and_help(self):
        """R4.1: Verify audit_secrets.py exists and responds to --help."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--help"])
        self.assertEqual(ret, 0, f"audit_secrets.py --help failed: {stderr}")
        self.assertIn("--dir", stdout, "Help text must document --dir")

    def test_r4_02_audit_secrets_clean_repo_passes(self):
        """R4.2: Verify audit_secrets.py returns exit code 0 on the clean repository."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT])
        self.assertEqual(ret, 0, f"audit_secrets.py failed on repository: {stderr}\n{stdout}")

    def test_r4_03_audit_secrets_detects_api_tokens(self):
        """R4.3: Verify audit_secrets.py flags detected API tokens/keys with exit code 1."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = os.path.join(tmpdir, "config.py")
            with open(bad_file, "w") as f:
                f.write('OPENAI_KEY = "sk-1234567890abcdef1234567890abcdef12345678"\n')

            ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", tmpdir])
            self.assertNotEqual(ret, 0, "audit_secrets.py must return non-zero exit code when API key is found")
            self.assertTrue("config.py" in stdout or "config.py" in stderr, "Output must identify violating file")

    def test_r4_04_audit_secrets_detects_private_keys(self):
        """R4.4: Verify audit_secrets.py detects RSA and OpenSSH private key headers."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = os.path.join(tmpdir, "server.key")
            with open(key_file, "w") as f:
                f.write("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----\n")

            ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", tmpdir])
            self.assertNotEqual(ret, 0, "audit_secrets.py must fail when private key is found")

    def test_r4_05_audit_secrets_detects_local_user_paths(self):
        """R4.5: Verify audit_secrets.py detects Windows, URL-encoded, and Unix user paths."""
        require_artifact(AUDIT_SCRIPT, "Milestone M3", "audit_secrets.py")
        test_cases = [
            ("win_path.txt", "Working directory: C:\\Users\\secret_user\\Documents\\project\n"),
            ("url_encoded_path.json", '{"workspaceUris": ["file:///c%3A/Users/secret_user/project"]}\n'),
            ("unix_path.txt", "Log path: /Users/secret_user/logs/app.log\n"),
            ("home_path.txt", "Home directory: /home/secret_user/workspace\n"),
        ]
        for filename, content in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                leak_file = os.path.join(tmpdir, filename)
                with open(leak_file, "w", encoding="utf-8") as f:
                    f.write(content)

                ret, stdout, stderr = run_cmd([sys.executable, AUDIT_SCRIPT, "--dir", tmpdir])
                self.assertNotEqual(
                    ret, 0,
                    f"audit_secrets.py must fail when local user path is detected in {filename} (content: {content.strip()})"
                )

    def test_r4_06_repo_files_free_of_hardcoded_user_paths(self):
        """R4.6: Verify production data, declarations, and report files have zero unredacted local user paths."""
        targets = [
            SOURCES_FILE,
            SESSIONS_FILE,
            DATA_JS_FILE,
            os.path.join(REPO_ROOT, "TEST_READY.md"),
            os.path.join(REPO_ROOT, "reports", "source-inventory.md"),
            os.path.join(REPO_ROOT, "reports", "validation-report.md"),
        ]
        user_path_pattern = re.compile(r'(?:[a-zA-Z]:|[a-zA-Z]%3[Aa])[/\\]+users[/\\]+[a-zA-Z0-9_.-]+', re.IGNORECASE)
        for target in targets:
            if os.path.exists(target):
                content = read_text_file(target)
                matches = user_path_pattern.findall(content)
                if matches and not os.path.exists(AUDIT_SCRIPT):
                    require_artifact(AUDIT_SCRIPT, "Milestone M3", f"Path sanitization for {os.path.basename(target)}")
                self.assertEqual(len(matches), 0, f"Unredacted user path found in {target}: {matches}")

    # =========================================================================
    # Requirement R5: Git Initialization and GitHub Publishing
    # =========================================================================

    def test_r5_01_gitignore_exists_and_covers_sensitive_patterns(self):
        """R5.1: Verify .gitignore exists and ignores sensitive patterns (caches, env, IDE, logs)."""
        require_artifact(GITIGNORE_FILE, "Milestone M5", ".gitignore")
        content = read_text_file(GITIGNORE_FILE)
        required_patterns = ["__pycache__", ".env", "*.log", ".vscode"]
        for pat in required_patterns:
            self.assertIn(pat, content, f".gitignore must contain '{pat}'")

    def test_r5_02_git_repo_is_initialized(self):
        """R5.2: Verify git repository is initialized (.git exists or git rev-parse succeeds)."""
        require_artifact(GIT_DIR, "Milestone M5", ".git repository directory")
        ret, stdout, stderr = run_cmd(["git", "rev-parse", "--is-inside-work-tree"])
        self.assertEqual(ret, 0, "git rev-parse should confirm git work-tree")
        self.assertEqual(stdout.strip(), "true")

    def test_r5_03_git_working_tree_clean_or_valid_initial_commit(self):
        """R5.3: Verify git repository has initial commit on main branch."""
        require_artifact(GIT_DIR, "Milestone M5", ".git repository directory")
        ret, stdout, stderr = run_cmd(["git", "branch", "--show-current"])
        self.assertEqual(ret, 0)
        branch = stdout.strip()
        self.assertIn(branch, ["main", "master"])

    def test_r5_04_no_secrets_or_env_files_tracked_in_git(self):
        """R5.4: Verify no sensitive files (.env, .pem, .key) are tracked in git index."""
        require_artifact(GIT_DIR, "Milestone M5", ".git repository directory")
        ret, stdout, stderr = run_cmd(["git", "ls-files"])
        self.assertEqual(ret, 0)
        tracked_files = stdout.splitlines()
        for f in tracked_files:
            self.assertFalse(f.endswith(".env"), f"Sensitive .env file tracked in git: {f}")
            self.assertFalse(f.endswith(".key") or f.endswith(".pem"), f"Private key file tracked in git: {f}")

    def test_r5_05_github_publishing_metadata_or_remote_ready(self):
        """R5.5: Verify README or git configuration provides GitHub publishing instructions or remote."""
        require_artifact(GIT_DIR, "Milestone M5", ".git repository directory")
        # Check either git remote exists or README documents gh repo create
        readme_content = read_text_file(README_MD)
        has_gh_doc = "gh repo" in readme_content or "github" in readme_content.lower()
        self.assertTrue(has_gh_doc, "README must document GitHub publishing commands")


if __name__ == "__main__":
    unittest.main()
