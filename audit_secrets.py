#!/usr/bin/env python3
"""
Decisn3 — Security & Privacy Scanner (audit_secrets.py)

Standalone automated scanner for auditing the repository prior to open-source
release. Verifies:
1. API keys & access tokens: OpenAI, GitHub, Google, AWS, Slack.
2. Cryptographic private keys: RSA, OpenSSH, EC, DSA PEM blocks.
3. Absolute local user filesystem paths (Windows [C-Z]:\\Users\\ and Unix /(home|Users)/).
4. Unredacted international phone numbers.
5. Private personal email addresses outside test fixtures.

CLI Usage:
    python audit_secrets.py [--dir <path>] [--verbose]

Exit Codes:
    0: Repository is clean (0 violations).
    1: Security or privacy violations detected with file locations and line numbers.
"""

import os
import sys
import re
import argparse

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "node_modules",
    "tests",
    ".agents",
    ".gemini"
}

SKIP_FILES = {
    "audit_secrets.py",
    "package-lock.json"
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svgz",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".pdf", ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".pyd", ".db", ".sqlite", ".dat"
}

# 1. Cryptographic Private Keys
RE_PRIVATE_KEY = re.compile(
    r'-----BEGIN\s+(?:[A-Z0-9_-]+\s+)?PRIVATE\s+KEY-----',
    re.IGNORECASE
)

# 2. API Keys
RE_API_OPENAI = re.compile(r'\bsk-[a-zA-Z0-9_-]{20,}\b')
RE_API_GITHUB = re.compile(r'\b(?:ghp_[a-zA-Z0-9]{36,}|github_pat_[a-zA-Z0-9_]{50,}|gh[ours]_[a-zA-Z0-9]{36,})\b')
RE_API_GOOGLE = re.compile(r'\bAIza[0-9A-Za-z-_]{35}\b')
RE_API_AWS = re.compile(r'\bAKIA[0-9A-Z]{16}\b')
RE_API_SLACK = re.compile(r'\bxox[baprs]-[0-9a-zA-Z]{10,48}\b')

# 3. Absolute Local User Filesystem Paths
RE_PATH_WINDOWS = re.compile(r'(?:[A-Za-z]:|[A-Za-z]%3[Aa])[\\/]+Users[\\/]+[a-zA-Z0-9_.-]+', re.IGNORECASE)
RE_PATH_UNIX = re.compile(r'(?<![A-Za-z0-9])/(?:home|Users)/[a-zA-Z0-9_.-]+', re.IGNORECASE)

# 4. Personal Webmail Domains
RE_PERSONAL_EMAIL = re.compile(
    r'\b[A-Za-z0-9._%+-]+@(?:gmail|yahoo|hotmail|outlook|icloud|protonmail|live|aol)\.[A-Za-z]{2,}\b',
    re.IGNORECASE
)

# 5. International Phone Numbers
RE_PHONE_CANDIDATE = re.compile(r'(?:\+|00)[1-9]\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{3,9}')


def is_binary_file(filepath: str) -> bool:
    """Check if file is binary by extension or null byte presence."""
    _, ext = os.path.splitext(filepath)
    if ext.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


def is_sanitizer_or_pattern_def(line: str, filepath: str = "") -> bool:
    """Ignore regex replacement logic or pattern definition lines in Python source code."""
    if filepath and not filepath.endswith(".py"):
        return False
    stripped = line.strip()
    if stripped.startswith("#"):
        return False
    if "re.sub(" in line or "re.compile(" in line:
        return True
    return False


def check_unredacted_phone(line: str):
    """Detect unredacted phone numbers while ignoring redacted '+234...' patterns."""
    for m in RE_PHONE_CANDIDATE.findall(line):
        if "..." in m or "xxx" in m.lower() or "***" in m:
            continue
        digits = re.sub(r'\D', '', m)
        if len(digits) >= 9:
            return m
    return None


def mask_secret(secret: str) -> str:
    """Mask secret value for safe console logging."""
    if len(secret) <= 8:
        return secret[:2] + "****"
    return secret[:4] + "...." + secret[-4:]


def scan_file(filepath: str, base_dir: str):
    """Scan a single text file for security & privacy violations."""
    violations = []
    rel_path = os.path.relpath(filepath, base_dir)

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as exc:
        return [f"{rel_path}:0: [READ_ERROR] Unable to read file: {exc}"]

    for line_idx, line in enumerate(lines, start=1):
        # 1. Check Private Key
        pk_match = RE_PRIVATE_KEY.search(line)
        if pk_match:
            violations.append(
                f"{rel_path}:{line_idx}: [PRIVATE_KEY] Cryptographic private key header detected: '{pk_match.group(0)}'"
            )
            continue

        # 2. Check API Keys
        for api_re, label in [
            (RE_API_OPENAI, "OpenAI API Key"),
            (RE_API_GITHUB, "GitHub Token"),
            (RE_API_GOOGLE, "Google API Key"),
            (RE_API_AWS, "AWS Access Key"),
            (RE_API_SLACK, "Slack Token")
        ]:
            api_match = api_re.search(line)
            if api_match:
                masked = mask_secret(api_match.group(0))
                violations.append(
                    f"{rel_path}:{line_idx}: [API_KEY] {label} detected: {masked}"
                )
                break

        # Ignore lines that are internal regex definitions or replacements in Python source
        if is_sanitizer_or_pattern_def(line, filepath):
            continue

        # 3. Check Absolute Local User Paths
        win_path_match = RE_PATH_WINDOWS.search(line)
        if win_path_match:
            violations.append(
                f"{rel_path}:{line_idx}: [LOCAL_PATH] Windows user path detected: '{win_path_match.group(0)}'"
            )
            continue

        unix_path_match = RE_PATH_UNIX.search(line)
        if unix_path_match:
            violations.append(
                f"{rel_path}:{line_idx}: [LOCAL_PATH] Unix/macOS user path detected: '{unix_path_match.group(0)}'"
            )
            continue

        # 4. Check Unredacted Phone Numbers
        unredacted_phone = check_unredacted_phone(line)
        if unredacted_phone:
            violations.append(
                f"{rel_path}:{line_idx}: [PHONE_NUMBER] Unredacted phone number detected: '{mask_secret(unredacted_phone)}'"
            )
            continue

        # 5. Check Private Personal Emails
        email_match = RE_PERSONAL_EMAIL.search(line)
        if email_match:
            violations.append(
                f"{rel_path}:{line_idx}: [PERSONAL_EMAIL] Personal webmail address detected: '{mask_secret(email_match.group(0))}'"
            )

    return violations


def audit_directory(target_dir: str, verbose: bool = False):
    """Walk through target directory and audit all eligible files."""
    all_violations = []
    scanned_file_count = 0

    target_abs = os.path.abspath(target_dir)
    if not os.path.exists(target_abs):
        print(f"[ERROR] Target directory does not exist: {target_dir}")
        return 1

    for root, dirs, files in os.walk(target_abs):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if file in SKIP_FILES:
                continue

            filepath = os.path.join(root, file)
            if is_binary_file(filepath):
                continue

            scanned_file_count += 1
            if verbose:
                print(f"[SCAN] {os.path.relpath(filepath, target_abs)}")

            violations = scan_file(filepath, target_abs)
            all_violations.extend(violations)

    print("=" * 60)
    print("Decisn3 — Security & Privacy Audit Report")
    print("=" * 60)
    print(f"[INFO] Scanned {scanned_file_count} files in: {target_abs}")

    if all_violations:
        print(f"\n[FAIL] Found {len(all_violations)} violation(s):\n")
        for v in all_violations:
            print(f"  - {v}")
        print("\n" + "=" * 60)
        return 1
    else:
        print(f"[PASS] 0 violations detected. Repository is clean and safe for release.")
        print("=" * 60)
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Scan directory for secrets, API keys, private keys, local user paths, and sensitive PII."
    )
    parser.add_argument(
        "--dir",
        dest="target_dir",
        default=".",
        help="Target directory to scan (default: current working directory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output listing all scanned files"
    )

    args = parser.parse_args()
    exit_code = audit_directory(args.target_dir, args.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
