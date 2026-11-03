#!/usr/bin/env python3
"""
Decisn3 — Cross-Project Scaffolding CLI (init_decision_graph.py)

Bootstraps the Decision Graph framework into any target repository:
- Scaffolds required directory structure (data/, libs/)
- Copies UI assets (index.html, app.js, styles.css, Three.js & OrbitControls)
- Copies sync_decisions.py to target root
- Injects custom project title and subtitle into index.html
- Generates valid seed decisions.json (DEC-001), sources.json (SRC-001), sessions.json (SES-001)
- Validates and compiles data/data.js for immediate zero-CORS launch
"""

import os
import sys
import json
import shutil
import argparse
import html
import re
import subprocess


def create_seed_decisions(project_name: str) -> dict:
    """Generate seed decisions.json containing valid DEC-001 with all mandatory fields."""
    return {
        "decisions": [
            {
                "id": "DEC-001",
                "title": "Adopt Interactive Decision Graph Framework",
                "category": "architecture",
                "status": "implemented",
                "significance": "foundational",
                "summary": "Adopt interactive decision graph framework to track architectural decisions, rationale, and causal dependencies.",
                "choice": "Scaffold standalone offline Decisn3 with dual 3D WebGL and 2D SVG engines.",
                "context": f"Need transparent, auditable, and interconnected tracking of architectural choices for {project_name} without relying on disconnected static ADR files.",
                "provenance": {
                    "source": "SRC-001",
                    "timestamp": "2026-11-03T10:00:00Z",
                    "author": "Architecture Team"
                },
                "session_id": "SES-001",
                "session_title": "Decision Graph Inception",
                "epoch": 1,
                "relationships": []
            }
        ]
    }


def create_seed_sources(project_name: str) -> dict:
    """Generate seed sources.json containing valid SRC-001."""
    return {
        "sources": [
            {
                "id": "SRC-001",
                "name": f"{project_name} Architecture Kickoff",
                "path": "README.md",
                "type": "documentation",
                "accessible": True,
                "date": "2026-11-03",
                "description": f"Foundational specification and decision log initiating the {project_name} decision graph."
            }
        ]
    }


def create_seed_sessions(project_name: str) -> dict:
    """Generate seed sessions.json containing valid SES-001 and SES-002 with all mandatory fields."""
    return {
        "sessions": [
            {
                "id": "SES-001",
                "title": "Decision Graph Inception",
                "date": "2026-11-03",
                "start_time": "2026-11-03T10:00:00Z",
                "end_time": "2026-11-03T11:00:00Z",
                "epoch": 1,
                "epoch_title": "Epoch 1: Inception & Scaffolding",
                "step_count": 1,
                "summary": f"Initial scaffolding and adoption of interactive decision graph framework for {project_name}.",
                "decisions": [
                    "DEC-001"
                ],
                "decision_ids": [
                    "DEC-001"
                ],
                "participants": [
                    "Lead Architect",
                    "Agentic Assistant"
                ],
                "artifacts": [
                    "data/decisions.json"
                ],
                "conversation_logs": [
                    {
                        "turn": 1,
                        "role": "user",
                        "timestamp": "2026-11-03T10:00:00Z",
                        "content": f"Initialize interactive decision graph for {project_name} architectural tracking."
                    },
                    {
                        "turn": 2,
                        "role": "assistant",
                        "timestamp": "2026-11-03T10:05:00Z",
                        "content": f"Scaffolding decision graph dashboard and seed DEC-001 record for {project_name}."
                    }
                ]
            },
            {
                "id": "SES-002",
                "title": "Architecture Evolution & Review",
                "date": "2026-11-03",
                "start_time": "2026-11-03T11:00:00Z",
                "end_time": "2026-11-03T12:00:00Z",
                "epoch": 2,
                "epoch_title": "Epoch 2: Architecture Evolution",
                "step_count": 1,
                "summary": f"Architecture evolution and lifecycle deliberation session for {project_name}.",
                "decisions": [],
                "decision_ids": [],
                "participants": [
                    "Lead Architect",
                    "Agentic Assistant"
                ],
                "artifacts": [
                    "data/decisions.json"
                ],
                "conversation_logs": [
                    {
                        "turn": 1,
                        "role": "user",
                        "timestamp": "2026-11-03T11:00:00Z",
                        "content": f"Review architectural evolution and decision lifecycle for {project_name}."
                    },
                    {
                        "turn": 2,
                        "role": "assistant",
                        "timestamp": "2026-11-03T11:05:00Z",
                        "content": "Ready to document subsequent decisions, reversals, and dependencies."
                    }
                ]
            }
        ]
    }


def scaffold_project(target_dir: str, project_name: str = None, force: bool = False, source_dir: str = None) -> bool:
    """
    Scaffold Decisn3 into target_dir.
    Returns True on success, False on failure.
    """
    target_dir = os.path.abspath(target_dir)
    if not source_dir:
        source_dir = os.path.dirname(os.path.abspath(__file__))

    # Check collision: if directory exists and has files, require force
    if os.path.exists(target_dir) and os.path.isdir(target_dir):
        existing_items = os.listdir(target_dir)
        if existing_items and not force:
            print(
                f"[ERROR] Target directory '{target_dir}' is not empty ({len(existing_items)} items found). "
                f"Use --force to overwrite.",
                file=sys.stderr
            )
            return False

    # Derive default project name
    if not project_name:
        base = os.path.basename(target_dir)
        project_name = base if base and base not in (".", "/", "\\") else "My Project"

    # Create target directories
    data_dir = os.path.join(target_dir, "data")
    libs_dir = os.path.join(target_dir, "libs")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(libs_dir, exist_ok=True)

    # 1. Copy presentation root assets and sync script
    root_assets = ["app.js", "styles.css", "sync_decisions.py"]
    for asset in root_assets:
        src = os.path.join(source_dir, asset)
        dst = os.path.join(target_dir, asset)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            print(f"[ERROR] Required asset '{asset}' missing from source '{source_dir}'", file=sys.stderr)
            return False

    # 2. Copy libs assets (three.min.js, OrbitControls.js)
    libs_assets = ["three.min.js", "OrbitControls.js"]
    for lib in libs_assets:
        src = os.path.join(source_dir, "libs", lib)
        dst = os.path.join(libs_dir, lib)
        if os.path.exists(src):
            shutil.copy2(src, dst)
        else:
            print(f"[ERROR] Required library '{lib}' missing from '{os.path.join(source_dir, 'libs')}'", file=sys.stderr)
            return False

    # 3. Inject project title and subtitle into index.html
    src_html = os.path.join(source_dir, "index.html")
    if not os.path.exists(src_html):
        print(f"[ERROR] index.html missing from source '{source_dir}'", file=sys.stderr)
        return False

    with open(src_html, "r", encoding="utf-8") as f:
        html_content = f.read()

    escaped_name = html.escape(project_name)
    # Inject title
    html_content = re.sub(
        r'<title>.*?</title>',
        lambda m: f'<title>{escaped_name} — Decisn3</title>',
        html_content,
        flags=re.DOTALL
    )
    # Inject brand subtitle
    html_content = re.sub(
        r'<div class="brand-subtitle">.*?</div>',
        lambda m: f'<div class="brand-subtitle">{escaped_name}</div>',
        html_content,
        flags=re.DOTALL
    )

    dst_html = os.path.join(target_dir, "index.html")
    with open(dst_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    # 4. Write seed data
    decisions_seed = create_seed_decisions(project_name)
    with open(os.path.join(data_dir, "decisions.json"), "w", encoding="utf-8") as f:
        json.dump(decisions_seed, f, indent=2)

    sources_seed = create_seed_sources(project_name)
    with open(os.path.join(data_dir, "sources.json"), "w", encoding="utf-8") as f:
        json.dump(sources_seed, f, indent=2)

    sessions_seed = create_seed_sessions(project_name)
    with open(os.path.join(data_dir, "sessions.json"), "w", encoding="utf-8") as f:
        json.dump(sessions_seed, f, indent=2)

    # 5. Run sync in target directory to compile data/data.js immediately
    target_sync = os.path.join(target_dir, "sync_decisions.py")
    res = subprocess.run([sys.executable, target_sync], cwd=target_dir)
    if res.returncode != 0:
        print("[ERROR] Initial data synchronization failed in target directory.", file=sys.stderr)
        return False

    print(f"[SUCCESS] Initialized Decision Graph in: {target_dir}")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Bootstrap the Interactive Decisn3 into any target repository."
    )
    parser.add_argument(
        "--target",
        type=str,
        default=".",
        help="Target directory path to scaffold (defaults to current working directory)"
    )
    parser.add_argument(
        "--project-name",
        type=str,
        default=None,
        help="Display title and subtitle for initialized decision graph (defaults to directory name or 'My Project')"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force scaffolding and overwrite existing files if target directory is non-empty"
    )
    parser.add_argument(
        "positional_target",
        nargs="?",
        default=None,
        help=argparse.SUPPRESS
    )

    args = parser.parse_args()

    # Determine target directory
    target_path = args.target
    if target_path == "." and args.positional_target:
        target_path = args.positional_target

    success = scaffold_project(
        target_dir=target_path,
        project_name=args.project_name,
        force=args.force
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
