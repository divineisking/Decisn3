# Test Infrastructure & Specification (`TEST_INFRA.md`)

This document defines the architecture, philosophy, feature mappings, and execution guidelines for the **End-to-End (E2E) Test Suite** of the Decisn3 standalone open-source release.

---

## 1. Test Philosophy

The E2E Test Suite adheres to four core testing tenets:

### 1.1 Opaque-Box & Requirement-Driven
- **External Contract Verification**: Tests treat the Decisn3 and its CLI tooling as black boxes. They validate public interfaces:
  - CLI commands, options, and exit codes (`sync_decisions.py`, `init_decision_graph.py`, `audit_secrets.py`).
  - Standard output and standard error feedback (`[PASS]`, `[ERROR]`, `[WARN]`, `[SUCCESS]`).
  - Generated persistent artifacts (`data/data.js`, `data/sessions.json`, `data/decisions.json`, `data/sources.json`).
  - File format validation (strict JSON parsing, valid JavaScript object evaluation).
  - Web UI and DOM contracts (`index.html`, `app.js`, session filter controls, drawer context, Three.js canvas mount).
- **Direct Requirement Mapping**: Every test is directly traced to the 5 primary user requirements:
  - **R1**: Session-Based Decision Discovery & Exploration
  - **R2**: Cross-Project Initialization Strategy
  - **R3**: Open-Source README & How-To Guide
  - **R4**: Security, Privacy & Secret Sanitization Audit
  - **R5**: Git Initialization & GitHub Release

### 1.2 Independence of Implementation Internals
- Tests do not rely on or mock internal private Python or JavaScript functions.
- If internal implementation details change (such as how a loop is structured or how a helper function is named), tests continue to pass as long as the external observable contract holds true.

### 1.3 Progressive Testability & Dual Track Execution
- In accordance with the Project Pattern Dual Track methodology, the E2E test suite is authored in parallel with milestone development.
- **Progressive Mode (Default)**: During milestone execution, tests gracefully detect milestone availability. If a milestone component (such as `init_decision_graph.py` from M2 or `audit_secrets.py` from M3) is not yet implemented, the test skips cleanly with an informative message (e.g. `M2 pending: init_decision_graph.py does not exist yet`). The test suite finishes with exit code `0`.
- **Strict Mode (`--strict`)**: In milestone M6 (Final Verification & Hardening), running the runner with `--strict` or `TEST_STRICT=1` disables skipping for pending milestones; every expected artifact must exist and pass 100%.

### 1.4 Self-Containment & Zero Repository Contamination
- Tests that create, modify, or delete files (such as bootstrapping target repositories or testing corrupted schemas) always operate inside isolated temporary directories (`tempfile.TemporaryDirectory`).
- No test pollutes or alters the production `data/` or root files of the repository.

---

## 2. Feature Inventory Mapping

| Req ID | Feature Area | Milestone | Primary Observable Contracts | Corresponding Tests |
| :--- | :--- | :---: | :--- | :--- |
| **R1** | Session Schema & Storage | M1 | `data/sessions.json` ships clean (`[]`) and scaffolded sessions contain `id`, `title`, `start_time`, `end_time`, `step_count`, `summary`, `decisions`, `conversation_logs`. | Tier 1: `test_r1_01_sessions_json_structure_and_mandatory_fields`<br>Tier 4: `test_workload_scenario_d_session_based_exploration_data_navigation` |
| **R1** | Decision Session Enrichment | M1 | `data/decisions.json` ships clean (`[]`) and scaffolded decisions contain `session_id`, `session_title`, explicit `epoch`. | Tier 1: `test_r1_02_decisions_json_session_enrichment_and_epochs`<br>Tier 1: `test_r1_03_referential_integrity_between_decisions_and_sessions` |
| **R1** | Session Sync & Bundling | M1 | `python sync_decisions.py` validates sessions, generates zero-CORS `data/data.js` containing `sessions`, `decisions`, `sources`. | Tier 1: `test_r1_04_sync_tool_bundles_sessions_into_data_js`<br>Tier 2: `test_sync_dangling_session_id` |
| **R1** | 'automation' Category Support | M1 | `automation` category is recognized in sync tool, CSS (`.badge-cat-automation`), and HTML filters. | Tier 1: `test_r1_05_automation_category_support_and_dec32` |
| **R1** | Interactive Session UI Navigation | M1 | `index.html` has `#graph-session-filter`, `#explorer-session-filter`, session toggle. `app.js` groups timeline by session and renders drawer logs. | Tier 1: `test_r1_06_ui_html_session_filter_and_toggle_elements`<br>Tier 1: `test_r1_07_app_js_session_filtering_and_drawer_context`<br>Tier 3: `test_pairwise_browser_dom_integration` |
| **R2** | Cross-Project Init CLI | M2 | `python init_decision_graph.py --target <path> --project-name <name>` exits 0, scaffolds full tree, valid seed data. | Tier 1: `test_r2_01_init_script_exists_and_help_flag`<br>Tier 1: `test_r2_02_init_scaffolds_complete_directory_tree`<br>Tier 1: `test_r2_03_init_generates_valid_seed_schemas` |
| **R2** | Scaffolding Validation Guarantee | M2 | Newly scaffolded project runs `sync_decisions.py` with exit code 0 and 0 errors. | Tier 1: `test_r2_04_scaffolded_project_passes_sync_with_zero_errors`<br>Tier 3: `test_pairwise_init_sync_audit_pipeline` |
| **R2** | Sync CLI `--init` Support | M2 | `python sync_decisions.py --init` bootstraps current or target directory. | Tier 1: `test_r2_05_sync_cli_init_flag_behavior`<br>Tier 3: `test_pairwise_sync_cli_init_matches_standalone_init` |
| **R2** | Collision Prevention & Force Overwrite | M2 | Refuses to overwrite non-empty target directory without `--force`; succeeds with `--force`. | Tier 1: `test_r2_06_init_force_flag_and_collision_prevention`<br>Tier 2: `test_init_existing_nonempty_directory_without_force_fails` |
| **R3** | Open-Source README Overhaul | M4 | `README.md` exists (>4KB), covers all 10 standard open-source sections, zero local file URI leaks. | Tier 1: `test_r3_01_readme_exists_and_non_empty`<br>Tier 1: `test_r3_02_readme_contains_ten_required_sections`<br>Tier 1: `test_r3_03_readme_zero_local_filesystem_leaks` |
| **R3** | Schema & Visualization Docs | M4 | Documents schema fields, enums, 3D WebGL vs 2D SVG modes, camera navigation, and local launch instructions. | Tier 1: `test_r3_04_readme_documents_data_schemas_and_enums`<br>Tier 1: `test_r3_05_readme_documents_dual_mode_3d_2d_visualization` |
| **R4** | Automated Secret Scanner | M3 | `python audit_secrets.py [--dir <path>]` exits 0 on clean repository; exits 1 with line numbers on detected secrets. | Tier 1: `test_r4_01_audit_secrets_script_exists_and_help`<br>Tier 1: `test_r4_02_audit_secrets_clean_repo_passes`<br>Tier 1: `test_r4_03_audit_secrets_detects_api_tokens` |
| **R4** | Private Keys & Local Path Detection | M3 | Scanner flags multiline private keys and unredacted `[C-Z]:\Users\` local file paths. | Tier 1: `test_r4_04_audit_secrets_detects_private_keys`<br>Tier 1: `test_r4_05_audit_secrets_detects_local_user_paths`<br>Tier 2: `test_audit_secrets_multiline_private_key` |
| **R4** | Repository Path Sanitization | M3 | `data/sources.json`, `data/sessions.json`, `data/data.js` have zero local user paths remaining. | Tier 1: `test_r4_06_repo_files_free_of_hardcoded_user_paths` |
| **R5** | Git Ignore Configuration | M5 | `.gitignore` exists and excludes caches, OS files, IDE configs, logs, `.env`. | Tier 1: `test_r5_01_gitignore_exists_and_covers_sensitive_patterns` |
| **R5** | Git Initialization & Clean Tree | M5 | `.git` initialized on `main` branch, working tree is clean or initial commit recorded. | Tier 1: `test_r5_02_git_repo_is_initialized`<br>Tier 1: `test_r5_03_git_working_tree_clean_or_valid_initial_commit` |
| **R5** | Git Secret Scrubbing & Remote Publishing | M5 | Zero sensitive files tracked; GitHub publishing guide or remote repository configured. | Tier 1: `test_r5_04_no_secrets_or_env_files_tracked_in_git`<br>Tier 1: `test_r5_05_github_publishing_metadata_or_remote_ready` |

---

## 3. Test Architecture & Tier Taxonomy

```
tests/
├── TEST_INFRA.md            # Test philosophy, feature mapping, runner invocation guide
├── __init__.py              # Python package marker
├── test_runner.py           # Unified multi-tier test runner with CLI flags & summary table
├── tier1_feature_tests.py   # Tier 1: Comprehensive feature coverage (>=5 tests per R1-R5)
├── tier2_boundary_tests.py  # Tier 2: Boundary, corner case, and stress tests
├── tier3_pairwise_tests.py  # Tier 3: Pairwise & cross-feature interaction tests
└── tier4_workload_tests.py  # Tier 4: Real-world end-to-end user application scenarios
```

### Tier 1: Feature Coverage Tests
- **Scope**: Direct validation of requirements R1, R2, R3, R4, R5.
- **Coverage**: 29 distinct test cases (at least 5 per requirement).
- **Execution Speed**: < 5 seconds.

### Tier 2: Boundary & Corner Cases
- **Scope**: Resilience under abnormal or extreme conditions:
  - Empty or missing `decisions.json` files.
  - Corrupted, malformed JSON structures.
  - Duplicate decision IDs.
  - Broken or dangling relationship target IDs.
  - Missing mandatory fields.
  - Deeply nested or non-existent target directories.
  - Directory collision handling without `--force`.
  - Non-UTF-8 binary files in secret scanning.
  - Multi-line PEM certificate and key scanning.

### Tier 3: Pairwise & Cross-Feature Combinations
- **Scope**: Interactions across multiple components:
  - Init -> Sync -> Secret Audit complete pipeline.
  - Scaffolding a project, adding decisions with sessions, and syncing.
  - Validating that `data/data.js` executes as valid JavaScript and populates `window.DECISN3_DATA`.
  - Reconciling session IDs and epochs across decisions and sessions.
  - Parity between `init_decision_graph.py` and `sync_decisions.py --init`.
  - Optional headless browser DOM validation via Playwright (Microsoft Edge).

### Tier 4: Real-World Workloads
- **Scope**: End-to-end lifecycle simulations:
  - **Scenario A**: Developer onboarding — bootstrapping a new project, adding ADRs, syncing data, verifying offline launch readiness.
  - **Scenario B**: Decision evolution — tracking superseded and reversed decisions with graph integrity.
  - **Scenario C**: CI/CD pre-release gate — running full sync, security audit, git verification, and documentation checks.
  - **Scenario D**: Architect session exploration — traversing historical sessions, timestamps, dialogue logs, and decision provenance.

---

## 4. Runner Invocation & CLI Usage

The unified runner `tests/test_runner.py` executes all tiers, handles summary formatting, and exits with code `0` on success.

### 4.1 Basic Execution (Progressive Mode)
Runs all test tiers in progressive mode (skips features from upcoming milestones that are not yet created):
```bash
python tests/test_runner.py
```

### 4.2 Run Specific Tier
```bash
python tests/test_runner.py --tier 1
python tests/test_runner.py --tier 2
python tests/test_runner.py --tier 3
python tests/test_runner.py --tier 4
```

### 4.3 Strict Mode (For Milestone M6 Verification)
Enforces that 100% of milestones M1-M5 are present; any missing artifact triggers an immediate failure:
```bash
python tests/test_runner.py --strict
```
*(Or set environment variable `TEST_STRICT=1`)*

### 4.4 Verbose Output
```bash
python tests/test_runner.py -v
```

### 4.5 Fail Fast
Stop execution on first failure:
```bash
python tests/test_runner.py -f
```

### 4.6 Include Headless Browser DOM Tests
If Playwright is installed, activates browser tests in headless mode:
```bash
python tests/test_runner.py --browser
```

---

## 5. Verification Gate & Acceptance Criteria

A test run is considered successful and release-ready when:
1. All four tiers execute to completion.
2. Zero failures (`failures == 0`) and zero unhandled errors (`errors == 0`).
3. Exit code is strictly `0`.
4. In Milestone M6 strict mode, zero tests are skipped (`skipped == 0`).
