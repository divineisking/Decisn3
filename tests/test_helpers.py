"""
Test Helpers and Fixture Utilities for Decisn3 E2E Test Suite.
"""

import os
import sys
import json
import subprocess
import unittest

# Canonical Path Constants
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)

DATA_DIR = os.path.join(REPO_ROOT, "data")
DECISIONS_FILE = os.path.join(DATA_DIR, "decisions.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
SOURCES_FILE = os.path.join(DATA_DIR, "sources.json")
DATA_JS_FILE = os.path.join(DATA_DIR, "data.js")

SYNC_SCRIPT = os.path.join(REPO_ROOT, "sync_decisions.py")
INIT_SCRIPT = os.path.join(REPO_ROOT, "init_decision_graph.py")
AUDIT_SCRIPT = os.path.join(REPO_ROOT, "audit_secrets.py")

INDEX_HTML = os.path.join(REPO_ROOT, "index.html")
APP_JS = os.path.join(REPO_ROOT, "app.js")
STYLES_CSS = os.path.join(REPO_ROOT, "styles.css")
README_MD = os.path.join(REPO_ROOT, "README.md")
GITIGNORE_FILE = os.path.join(REPO_ROOT, ".gitignore")
GIT_DIR = os.path.join(REPO_ROOT, ".git")


def is_strict_mode() -> bool:
    """Check if tests are running in strict mode (all milestones required)."""
    return os.environ.get("TEST_STRICT", "0").lower() in ("1", "true", "yes", "strict")


def require_artifact(path: str, milestone: str, description: str):
    """
    Assert existence of a required file/directory.
    In progressive mode, skips with explanation if missing.
    In strict mode, raises AssertionError.
    """
    if not os.path.exists(path):
        msg = f"{milestone} requirement missing: {description} (path: {path})"
        if is_strict_mode():
            raise AssertionError(f"Strict mode failure: {msg}")
        raise unittest.SkipTest(f"Pending {milestone}: {description} not yet available")


def run_cmd(args, cwd=None, env=None, timeout=30):
    """
    Execute a command synchronously, capturing stdout, stderr, and returncode.
    Uses UTF-8 encoding with fallback.
    """
    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    try:
        proc = subprocess.run(
            args,
            cwd=cwd or REPO_ROOT,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        return -1, "", f"Command timed out after {timeout} seconds: {exc}"
    except Exception as exc:
        return -1, "", str(exc)


def load_json_file(path: str):
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_text_file(path: str) -> str:
    """Read full text of a file."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
