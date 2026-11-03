# Decisn3

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![Visualization: 3D WebGL](https://img.shields.io/badge/3D%20Engine-Three.js%20r128-orange.svg)](https://threejs.org/)
[![Fallback: 2D SVG](https://img.shields.io/badge/2D%20Engine-Interactive%20SVG-informational.svg)](#dual-engine-visualization-3d-webgl--2d-svg)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero%20External-success.svg)](#quick-start-guide)
[![Security & Secrets](https://img.shields.io/badge/Secret%20Audit-Zero%20Violations-green.svg)](#security-privacy--secret-scanner)

An evidence-driven, interactive decision intelligence platform and causal graph visualization system for software engineering architectures.

---

## Table of Contents
1. [Project Overview: Why Decision Graphs?](#1-project-overview-why-decision-graphs)
2. [Dual-Engine Visualization (3D WebGL & 2D SVG)](#2-dual-engine-visualization-3d-webgl--2d-svg)
3. [Session-Based Decision Discovery](#3-session-based-decision-discovery)
4. [Quick-Start Guide](#4-quick-start-guide)
5. [Cross-Project Initialization & Daily Workflow](#5-cross-project-initialization--daily-workflow)
6. [Formal Data Schema Reference](#6-formal-data-schema-reference)
7. [Security, Privacy & Secret Scanner](#7-security-privacy--secret-scanner)
8. [Repository Structure](#8-repository-structure)
9. [Verification & Testing Suite](#9-verification--testing-suite)
10. [Contributing & License](#10-contributing--license)

---

## 1. Project Overview: Why Decision Graphs?

### The Failure of Traditional Flat ADRs
Traditional Architecture Decision Records (ADRs) are usually recorded as static, disconnected markdown files placed inside a `/docs/adr` or `/decisions` directory. While well-intentioned, flat ADR approaches suffer from fundamental limitations in complex, rapidly evolving software systems:
- **Loss of Causal Context**: Flat files capture a decision in isolation at a single moment in time. They cannot show which prior technical debt prompted the choice, or which downstream architectural constraints it imposed.
- **No Lineage or Impact Traversal**: When an architect asks *"If we replace SQLite with PostgreSQL, what else breaks?"* or *"Why did we choose soft deletes over hard deletes?"*, flat ADRs require manual text searches across dozens of disparate files.
- **Reversals and Conflicts Remain Hidden**: Architectural reversals, contradictory decisions, and risk-introducing compromises get buried in folder hierarchies without explicit, traversable relationships.
- **Staleness**: Disconnected documentation easily drifts out of sync with real-world code implementation and developer dialogue logs.

### The Decision Graph Solution
The **Decisn3** transforms architectural records into a living, navigable **directed causal knowledge graph**. Decisions are treated as first-class graph entities connected by typed, directional causal edges (`motivated_by`, `depends_on`, `supersedes`, `reverses`, `introduces_risk`, `validated_by`). 

By pairing graph data structures with an interactive dual-engine visualization (3D WebGL and 2D SVG) and developer conversation session indexing, the dashboard enables teams to:
- Instantly trace the ancestral root cause of any architectural choice.
- Identify the complete cascade of downstream consequences before modifying core components.
- Inspect verbatim developer-agent dialogue transcripts and implementation source files alongside decision rationale.
- Run completely offline with zero compilation, zero package managers, and zero external runtime dependencies.

### Clean Slate by Default & Reusable Framework
This repository is designed as a clean, zero-sample open-source platform:
1. **Ships Empty by Default**: The [`data/`](data/) directory (`decisions.json`, `sessions.json`, `sources.json`, and `data.js`) ships with empty arrays (`[]`) and zero sample or proprietary records, so you can adopt the repository directly without cleaning out demo data.
2. **Reusable Cross-Project Scaffolding**: A modular, portable toolchain that any engineering team can bootstrap into their own repository in seconds via `init_decision_graph.py` or `sync_decisions.py --init` to manage their software architectural lineage.

---

## 2. Dual-Engine Visualization (3D WebGL & 2D SVG)

The dashboard provides a versatile dual-engine visualization architecture designed to handle complex decision graphs without visual clutter or planar crowding.

```
                      ┌──────────────────────────────────────┐
                      │      Dashboard Viewport Controller   │
                      └──────────────────┬───────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
  ┌─────────────────────────────┐                 ┌─────────────────────────────┐
  │   Three.js r128 3D Engine   │                 │     Interactive 2D SVG      │
  │ • True Spatial Coordinates  │  ◄──Toggle──►   │ • Clean Planar Projection   │
  │ • OrbitControls & Gizmo     │                 │ • Low-Power / Fallback      │
  │ • 3 Graph Traversal Modes   │                 │ • Responsive ViewBox Pan    │
  └─────────────────────────────┘                 └─────────────────────────────┘
```

### 3D WebGL Visualization Engine
Powered by locally vendored **Three.js r128** and **OrbitControls**, the 3D mode distributes decision nodes across three meaningful physical dimensions rather than an arbitrary 2D force simulation:
- **X-Axis (Evolutionary Time)**: Chronological progression structured across development epochs.
- **Y-Axis (Architectural Layer)**: Vertical separation by system tier (e.g., Core Engine, Data Storage, Security/Auth, Frontend UI, DevOps/Automation).
- **Z-Axis (Causal Depth & Branching)**: Depth displacement illustrating ancestral distance and causal branch lineage.

#### Camera Navigation & Viewport Controls
- **Orbit Rotation**: Left-click and drag anywhere on the 3D canvas to rotate the camera perspective around the graph center.
- **Smooth Panning**: Right-click and drag (or two-finger drag on trackpads) to pan horizontally and vertically.
- **Perspective Zoom**: Mouse scroll wheel or the `+` / `−` toolbar buttons with smooth damping.
- **Focus Selected Node (`🎯`)**: Automatically animates the camera along an interpolated vector to frame the active decision node.
- **Frame Entire Graph (`⤢`)**: Restores a wide camera frustum centering all nodes across the timeline.
- **Reset Orbit (`↺`)**: Instantly resets camera rotation and elevation to the default isometric view.
- **Interactive 3D Orientation Gizmo**: A real-time RGB coordinate indicator rendered in the bottom-right corner (Red = X/Time, Green = Y/Layer, Blue = Z/Causal Depth).

#### Tripartite Graph Traversal Modes
The 3D toolbar allows switching between three distinct causal projection modes:
1. **🌌 Entire Graph**: Global topological overview rendering all nodes, category hulls, and directed relationship splines in full 3D space.
2. **🔍 Focus Neighbourhood**: Isolates the currently selected decision node and its immediate upstream and downstream adjacent neighbours. Distant, non-adjacent nodes and edges are smoothly dimmed to 6% opacity.
3. **⚡ Trace Ancestors & Descendants (Trace Decision History)**: Recursively traverses the directed graph in both directions along causal edges. It illuminates every ancestral motivation that led to the selected decision, as well as every downstream consequence or reversal that flowed from it, dimming all unrelated branches.

### 2D SVG Fallback Engine & Mode Toggle
For lightweight devices, battery-saving environments, or systems without hardware WebGL acceleration, the dashboard provides a seamless **2D Planar SVG Fallback**. 
- Click the **`🌐 3D / 📄 2D`** toggle button in the main navigation bar at any time.
- Node selection, active filters, search queries, and open detail drawer states are 100% synchronized and preserved between 2D and 3D views.
- The 2D mode renders clean SVG vectors with interactive drag-panning, node hover tooltips, and directional arrow markers.

---

## 3. Session-Based Decision Discovery

Architecture decisions do not occur in a vacuum; they happen during focused engineering sessions, pairing discussions, and problem-solving dialogues. The dashboard implements deep session integration (Requirement R1) linking high-level sessions down to granular decisions and conversation logs.

### Session Indexing & Mapping
- **Session Registry**: Development sessions and dialogue turns are stored in [`data/sessions.json`](data/sessions.json).
- Every decision in [`data/decisions.json`](data/decisions.json) includes explicit `session_id`, `session_title`, and `epoch` bindings.
- Bidirectional referential integrity is strictly verified by [`sync_decisions.py`](sync_decisions.py): every decision belongs to a valid session, and every session references valid decision nodes.

### Interactive Session Navigation Features
1. **Interactive Session Filtering**: Dedicated `#graph-session-filter` dropdown in the graph view and `#explorer-session-filter` dropdown in the explorer view. Selecting a session filters the visible landscape to highlight decisions produced during that specific engagement.
2. **Evolutionary Timeline Session Grouping**: The Timeline view organizes the project narrative chronologically, grouping decision milestones by session headers with start/end timestamps and step counts.
3. **Dual-Mode Explorer (`[ Decisions | Sessions ]` Toggle)**: The Explorer interface provides a toggle switch allowing architects to browse either:
   - **Decisions Mode**: Multi-facet filterable cards displaying categories, status, significance, choices, and lessons.
   - **Sessions Mode**: High-level development session overviews displaying objectives, participants, duration, step counts, and linked decision pills.
4. **Detail Drawer Conversation Excerpts**: Clicking any decision opens the slide-over detail drawer. In addition to architectural choices, context, trade-offs, and implementation files, the drawer displays the parent session metadata and an expandable **Conversation Dialogue Log** capturing the exact developer exchange and prompt context.

---

## 4. Quick-Start Guide

The dashboard is completely standalone and requires **no compilation, no node_modules, no npm build step, and no backend database**.

### Method 1: Zero-CORS Direct Browser Launch (Offline)
Thanks to the pre-compiled standalone data bundle in [`data/data.js`](data/data.js), the dashboard runs directly from the local filesystem with zero Cross-Origin Request Block (CORS) issues:
1. Navigate to the repository root directory in your file manager.
2. Double-click `index.html` (or right-click and choose **Open With Google Chrome / Firefox / Edge / Safari**).
3. The dashboard loads instantly with full 3D WebGL and 2D SVG functionality.

### Method 2: Local Static HTTP Server
If you prefer running a local development server:
```bash
# Clone the repository
git clone https://github.com/divineisking/Decisn3.git
cd Decisn3

# Start Python's built-in HTTP server:
python -m http.server 8000
```
Then open [http://localhost:8000](http://localhost:8000) in your web browser.

---

## 5. Cross-Project Initialization & Daily Workflow

You can adopt the Decision Graph framework into any new or existing software repository with a single command.

### Bootstrapping a New Repository

#### Option A: Standalone Scaffolding CLI (`init_decision_graph.py`)
```bash
python init_decision_graph.py --target /path/to/my-new-project --project-name "Billing Microservice"
```

#### Option B: Sync Tool Scaffolding Flag (`sync_decisions.py --init`)
```bash
python sync_decisions.py --init /path/to/my-new-project --project-name "Billing Microservice"
```

#### Scaffolding CLI Arguments
| Flag | Type | Description | Default |
|---|---|---|---|
| `--target` | String | Target directory to scaffold the decision graph into | Current Working Directory |
| `--project-name` | String | Human-readable title injected into `index.html` header | Directory name |
| `--force` | Boolean | Overwrite existing files if target directory is non-empty | `False` |

#### What Scaffolding Creates
When executed, the scaffolding tool automatically generates a self-contained, operational decision graph:
- **Presentation Assets**: Copies `index.html` (customized with project branding), `app.js`, `styles.css`, and vendored Three.js libraries (`libs/three.min.js`, `libs/OrbitControls.js`).
- **Data Engine**: Scaffolds `data/decisions.json` with seed decision `DEC-001`, `data/sessions.json` with seed session `SES-001`, and `data/sources.json` with seed source `SRC-001`.
- **Ingestion Utility**: Copies `sync_decisions.py` to the target root.
- **Immediate Compilation**: Automatically runs schema validation and compiles `data/data.js` so the scaffolded project opens immediately with zero errors.

### Day-to-Day Architectural Workflow
Once initialized, tracking architectural decisions in your project is a seamless 3-step routine:

```
   ┌──────────────────────────────────────────────────────────────┐
   │ 1. Formulate & Author Decision                               │
   │    Append new decision object to data/decisions.json         │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 2. Define Directed Relationships                             │
   │    Link causal edges: motivated_by, depends_on, reverses...  │
   └──────────────────────────────┬───────────────────────────────┘
                                  │
                                  ▼
   ┌──────────────────────────────────────────────────────────────┐
   │ 3. Run Validation & Synchronization                          │
   │    python sync_decisions.py                                  │
   │    Enforces ID uniqueness, referential integrity & compiles  │
   └──────────────────────────────────────────────────────────────┘
```

1. **Author the Decision**: Open `data/decisions.json` and append a new record with the next ID (e.g., `DEC-002`). Fill in title, category, status, significance, summary, choice, context, and provenance.
2. **Link Relationships**: Connect the decision to related nodes using any of the 10 supported directed relationship types (e.g., `{ "target": "DEC-001", "type": "depends_on", "explanation": "Requires initial graph architecture" }`).
3. **Synchronize & Validate**: Run the sync tool from the repository root:
   ```bash
   python sync_decisions.py
   ```
   The tool validates schema conformity, checks referential integrity of all directed edges, and recompiles `data/data.js`. Refresh your browser to inspect the updated live graph.

#### Optional Live Brain Session Sync
If your development environment generates AI agent conversation logs (e.g. Gemini Antigravity brain logs), you can parse and re-index sessions automatically:
```bash
python sync_decisions.py --sync-sessions --brain-dir ~/.gemini/antigravity/brain
```

---

## 6. Formal Data Schema Reference

The Decision Graph data model is fully decoupled from the UI and structured into portable JSON documents.

### Decisions Schema (`data/decisions.json`)
The root object contains a top-level `"decisions"` array. Each decision object adheres to the following specification:

| Field Name | Type | Mandatory? | Description & Constraints |
|---|---|:---:|---|
| `id` | String | **Yes** | Unique identifier matching pattern `^DEC-\d{3,}$` (e.g. `DEC-001`). |
| `title` | String | **Yes** | Concise, descriptive decision headline. |
| `category` | Enum | **Yes** | Architectural domain (see [Allowed Enums](#allowed-enums)). |
| `status` | Enum | **Yes** | Lifecycle state (see [Allowed Enums](#allowed-enums)). |
| `significance`| Enum | **Yes** | Architectural weight (see [Allowed Enums](#allowed-enums)). |
| `summary` | String | **Yes** | High-level summary of the decision. |
| `choice` | String | **Yes** | Explicit technical solution or implementation adopted. |
| `context` | String | **Yes** | Technical context, background, constraints, and problem statement. |
| `provenance` | Object | **Yes** | Audit evidence tracking author, source, timestamp, and excerpts. |
| `session_id` | String | **Yes** | Foreign key linking to parent session (e.g. `SES-001`). |
| `epoch` | Integer | **Yes** | Development epoch integer (1 to 12). |
| `session_title`| String | No | Display title of parent session. |
| `type` | String | No | Secondary categorization (e.g., `architecture`, `reversal`, `security`). |
| `alternatives` | Array | No | Evaluated options with trade-offs: `[{"option": "...", "trade_off": "..."}]`. |
| `dates` | Object | No | Key milestones: `{"proposed": "...", "approved": "...", "implemented": "..."}`. |
| `implementation`| Object | No | Affected components: `{"files": [...], "services": [...]}`. |
| `expected_effects`| String | No | Anticipated architectural benefits or performance impacts. |
| `observed_effects`| String | No | Empirical real-world outcomes after deployment. |
| `lessons` | Object | No | Takeaways: `{"documented": "...", "inferred": "..."}`. |
| `evidence_status`| Enum | No | Confidence tier: `corroborated`, `inferred`, or `unverified`. |
| `relationships`| Array | No | Directed graph edges: `[{"target": "DEC-XXX", "type": "...", "explanation": "..."}]`. |
| `open_questions`| String | No | Unresolved technical concerns or future research items. |

### Sessions Schema (`data/sessions.json`)
The root object contains a top-level `"sessions"` array. Each session object adheres to the following specification:

| Field Name | Type | Mandatory? | Description & Constraints |
|---|---|:---:|---|
| `id` | String | **Yes** | Unique identifier matching pattern `^SES-\d{3,}$` (e.g. `SES-001`). |
| `title` | String | **Yes** | Descriptive session title. |
| `start_time` | ISO 8601 | **Yes** | Session start timestamp (e.g. `2026-10-10T14:30:00Z`). |
| `end_time` | ISO 8601 | **Yes** | Session conclusion timestamp (must be `>= start_time`). |
| `step_count` | Integer | **Yes** | Number of execution turns or interaction steps. |
| `summary` | String | **Yes** | Narrative summary of session objectives and outcomes. |
| `decisions` | Array | **Yes** | List of decision ID strings produced in this session (e.g. `["DEC-001"]`). |
| `epoch` | Integer | No | Numerical epoch grouping. |
| `epoch_title` | String | No | Descriptive epoch name (e.g., `Epoch 1: Inception`). |
| `date` | String | No | Date string (`YYYY-MM-DD`). |
| `participants`| Array | No | List of contributors (engineers, agents). |
| `artifacts` | Array | No | Files modified or generated during the session. |
| `conversation_logs`| Array | No | Sanitized dialogue turns: `[{"turn": 1, "role": "user", "content": "..."}]`. |

### Allowed Enums

#### Categories (`category`)
- `architecture`: Core system structure, boundary definitions, and framework selections.
- `data`: Database schemas, storage engines, migration strategies, and data pipelines.
- `security`: Authentication, authorization, encryption, sanitization, and audit policies.
- `frontend`: User interfaces, visualization engines, styling, and design systems.
- `automation`: Background workers, scraping routines, cron scheduling, and agent tooling.
- `devops`: Deployment scripts, environment configurations, CI/CD, and process supervisors.
- `product`: Feature scope, UX paradigms, subscription models, and pricing pivots.
- `operations`: Operational playbooks, debugging runbooks, and recovery guardrails.

#### Lifecycle Status (`status`)
- `proposed`: Under active architectural review; not yet adopted.
- `approved`: Formally accepted by engineering team; awaiting implementation.
- `implemented`: Live and active in production code.
- `deprecated`: Phased out or superseded by a newer architectural pattern.
- `reversed`: Explicitly undone or reversed due to empirical findings or architectural trade-offs.
- `rejected`: Evaluated and discarded in favor of alternatives.

#### Significance Levels (`significance`)
- `foundational`: Mission-critical decision defining core system architecture; costly to reverse.
- `high`: Major subsystem choice with significant cross-module ramifications.
- `medium`: Standard component or feature decision within bounded domain scope.
- `low`: Minor optimization, utility choice, or styling adjustment.

### Directed Graph Relationship Types
The graph engine supports 10 strongly-typed directed relationship types. Directed edges represent causal semantics from `Source` to `Target`:

| Relationship Type | Directionality | Semantic Meaning & Usage |
|---|---|---|
| `motivated_by` | `A -> motivated_by -> B` | Decision A was initiated to solve a problem, bottleneck, or constraint identified in B. |
| `depends_on` | `A -> depends_on -> B` | Decision A requires technical or structural components established by Decision B. |
| `implements` | `A -> implements -> B` | Decision A provides the concrete software implementation for specification B. |
| `supersedes` | `A -> supersedes -> B` | Decision A replaces Decision B, rendering B deprecated or obsolete. |
| `introduces_risk`| `A -> introduces_risk -> B` | Decision A knowingly introduced an architectural risk, trade-off, or debt tracked in B. |
| `produces_outcome`| `A -> produces_outcome -> B` | Decision A empirically generated the measurable consequence or finding in B. |
| `validated_by` | `A -> validated_by -> B` | The hypothesis or reliability of Decision A was validated by test/audit B. |
| `contradicts` | `A -> contradicts -> B` | Decision A creates intentional or historical friction with Decision B. |
| `reverses` | `A -> reverses -> B` | Decision A completely revokes, rolls back, or reverses Decision B. |
| `influenced_by` | `A -> influenced_by -> B` | Decision A drew conceptual, strategic, or UX inspiration from Decision B. |

---

## 7. Security, Privacy & Secret Scanner

Open-source publishing requires strict assurance that private developer environments, tokens, and PII are never leaked. This repository includes an automated security scanner: [`audit_secrets.py`](audit_secrets.py).

### Running the Scanner
```bash
python audit_secrets.py
```
To scan an arbitrary directory with detailed verbose logs:
```bash
python audit_secrets.py --dir /path/to/project --verbose
```

### What the Scanner Validates
1. **API Keys & Access Tokens**: Scans for OpenAI (`sk-`), GitHub personal access tokens (`ghp_`, `github_pat_`), Google API keys (`AIza`), Amazon Web Services keys (`AKIA`), and Slack bot tokens (`xox`).
2. **Cryptographic Private Keys**: Scans for standard PEM headers (such as `BEGIN ... PRIVATE KEY` blocks, OpenSSH, EC, DSA).
3. **Absolute Local User Filesystem Paths**: Verifies zero hardcoded developer paths matching Windows drive user directories (e.g., `[drive]:\Users\<user>` patterns or URL-encoded equivalents) or Unix home paths. All links must be relative.
4. **Unredacted Phone Numbers**: Ensures international contact numbers are scrubbed or redacted.
5. **Private Email Addresses**: Flags personal webmail addresses (`@gmail.com`, `@yahoo.com`, etc.) outside allowable mock test fixtures.

### Security Guarantee
This repository has been audited with zero detected violations (Exit Code `0`), and ships with an empty `data/` directory free of any sample data, credentials, or local machine paths.

---

## 8. Repository Structure

```
Decisn3/
├── .gitignore                    # Clean git ignore configuration
├── LICENSE                       # MIT License
├── README.md                     # Comprehensive open-source documentation
├── TEST_READY.md                 # Test harness readiness declaration
├── index.html                    # Single-page dashboard application entry point
├── app.js                        # Unified application logic (Three.js 3D, 2D SVG, Timeline, Explorer)
├── styles.css                    # Responsive theme stylesheet (Dark & Light modes)
├── sync_decisions.py             # Validation, session indexing, bundling, and --init scaffolding
├── init_decision_graph.py        # Standalone cross-project scaffolding CLI
├── audit_secrets.py              # Automated security, PII, and filesystem path scanner
├── data/
│   ├── decisions.json            # Architectural decisions registry (ships empty by default)
│   ├── sessions.json             # Development sessions registry (ships empty by default)
│   ├── sources.json              # Primary sources registry (ships empty by default)
│   └── data.js                   # Zero-CORS pre-compiled JavaScript payload
├── libs/
│   ├── three.min.js              # Three.js r128 3D WebGL runtime
│   └── OrbitControls.js          # Interactive camera orbit controls
└── tests/
    ├── TEST_INFRA.md             # Test suite architecture specification
    ├── test_runner.py            # Unified 5-tier E2E test execution harness
    ├── test_helpers.py           # Shared test fixtures and subprocess runners
    ├── tier1_feature_tests.py    # Requirement feature coverage (R1-R5)
    ├── tier2_boundary_tests.py   # Boundary values and extreme input tests
    ├── tier3_pairwise_tests.py   # Cross-feature interaction and state preservation tests
    ├── tier4_workload_tests.py   # Real-world lifecycle workflows and release gate pipeline
    └── tier5_adversarial_tests.py# White-box adversarial hardening test suite
```

---

## 9. Verification & Testing Suite

The repository is guarded by an automated end-to-end test suite structured into 4 comprehensive tiers.

### Running the Test Suite
Execute tests using Python's standard `unittest` framework or the unified test runner:

```bash
# Run all test tiers:
python tests/test_runner.py

# Run specific test tiers:
python tests/test_runner.py --tier 1    # Feature Coverage (R1 to R5)
python tests/test_runner.py --tier 2    # Boundary & Corner Cases
python tests/test_runner.py --tier 3    # Pairwise & Cross-Feature Interactions
python tests/test_runner.py --tier 4    # Real-World Workload Scenarios
```

### Running Dedicated Verification Checks
```bash
# 1. Run Data Ingestion & Graph Schema Verification:
python sync_decisions.py

# 2. Run Validation-Only Check (dry-run without modifying data.js):
python sync_decisions.py --validate-only

# 3. Run Automated Security & Secret Audit:
python audit_secrets.py
```

---

## 10. Contributing & License

We welcome contributions, bug reports, and enhancements from the open-source community!

### How to Contribute
1. **Fork & Branch**: Fork the repository on GitHub and create a feature branch (`git checkout -b feature/my-new-feature`).
2. **Make Changes**: Follow the minimal change principle and keep presentation decoupled from data schemas.
3. **Verify Integrity**: Before committing, ensure all tests, sync routines, and security scanners pass cleanly:
   ```bash
   python sync_decisions.py --validate-only
   python audit_secrets.py
   python tests/test_runner.py
   ```
4. **Submit Pull Request**: Push your branch and open a Pull Request with a clear summary of your changes.

### Publishing to GitHub
To publish this repository under your own GitHub account:
```bash
# Initialize git repository
git init -b main

# Stage and commit all files
git add .
git commit -m "feat: initial open-source release of Decisn3"

# Create and push public repository using GitHub CLI (gh):
gh repo create Decisn3 --public --source=. --remote=origin --push \
  --description "Interactive 3D WebGL and 2D SVG decision graph dashboard for tracking software architectural decisions and causal lineage"

# Or configure remote origin manually:
git remote add origin https://github.com/divineisking/Decisn3.git
git push -u origin main
```

### License
This project is open-source software licensed under the **MIT License**. See the full license text in the [`LICENSE`](LICENSE) file.

```
Copyright (c) 2026 divineisking
```
