#!/usr/bin/env python3
"""
Decisn3 — Ingestion, Validation & Sync Tool

Validates decision graph schema, referential integrity of directed graph edges,
session-to-decision mappings, and bundles all data (decisions, sources, sessions)
into data/data.js for zero-CORS offline dashboard viewing.
"""

import os
import json
import sys
import argparse
import glob
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DECISIONS_FILE = os.path.join(DATA_DIR, "decisions.json")
SOURCES_FILE = os.path.join(DATA_DIR, "sources.json")
SESSIONS_FILE = os.path.join(DATA_DIR, "sessions.json")
DATA_JS_FILE = os.path.join(DATA_DIR, "data.js")

DEFAULT_BRAIN_DIR = os.environ.get(
    "ANTIGRAVITY_BRAIN_DIR",
    os.path.join(os.path.expanduser("~"), ".gemini", "antigravity", "brain")
)

def sanitize_path(text):
    if not text:
        return ""
    # Strip Windows paths with literal colon, URL-encoded colon (%3A / %3a), or escaped backslashes
    text = re.sub(r'[A-Za-z](?::|%3[Aa])(?:[\\\/]+|\\\\+)Users(?:[\\\/]+|\\\\+)[A-Za-z0-9_\-\.]+(?:[\\\/]+|\\\\+|$)', '~/workspace/', text, flags=re.IGNORECASE)
    text = re.sub(r'[A-Za-z](?::|%3[Aa])(?:[\\\/]+|\\\\+)Users(?:[\\\/]+|\\\\+)[A-Za-z0-9_\-\.]+', '~/workspace', text, flags=re.IGNORECASE)
    # Strip Unix user paths
    text = re.sub(r'/(?:home|Users)/[A-Za-z0-9_\-\.]+(?:[\\\/]+|$)', '~/workspace/', text, flags=re.IGNORECASE)
    text = re.sub(r'/(?:home|Users)/[A-Za-z0-9_\-\.]+', '~/workspace', text, flags=re.IGNORECASE)
    return text.strip()

def sync_brain_sessions(brain_dir, decisions, sessions_file):
    """
    Live brain indexing mode: Parses transcript logs in brain_dir for referenced decisions.
    """
    if not os.path.isdir(brain_dir):
        print(f"[WARN] Brain directory not found at: {brain_dir}. Preserving existing sessions.json.")
        return

    print(f"[INFO] Scanning live brain logs from: {brain_dir}")
    unique_cids = sorted(list(set(
        d.get("provenance", {}).get("conversation_id")
        for d in decisions
        if d.get("provenance", {}).get("conversation_id")
    )))

    existing_sessions = []
    if os.path.exists(sessions_file):
        try:
            with open(sessions_file, "r", encoding="utf-8") as f:
                existing_sessions = json.load(f).get("sessions", [])
        except Exception:
            existing_sessions = []

    existing_by_cid = {s.get("conversation_id"): s for s in existing_sessions}

    updated_sessions = []
    for idx, cid in enumerate(unique_cids, 1):
        s_dir = os.path.join(brain_dir, cid)
        t_path = os.path.join(s_dir, ".system_generated", "logs", "transcript.jsonl")
        
        existing = existing_by_cid.get(cid, {})
        session_id = existing.get("id", f"SES-{idx:03d}")
        title = existing.get("title", f"Session {session_id}")
        summary = existing.get("summary", "Conversation transcript session.")
        epoch = existing.get("epoch", 1)
        epoch_title = existing.get("epoch_title", f"Epoch {epoch}")
        date_val = existing.get("date", "2026-09-01")
        participants = existing.get("participants", ["Developer", "Agentic Assistant"])

        start_time = date_val + "T00:00:00Z"
        end_time = date_val + "T23:59:59Z"
        step_count = existing.get("step_count", 0)
        dialogue = existing.get("conversation_logs", [])

        if os.path.exists(t_path):
            steps = 0
            extracted_dialogue = []
            turn_idx = 1
            try:
                with open(t_path, "r", encoding="utf-8-sig") as tf:
                    for line in tf:
                        if not line.strip():
                            continue
                        steps += 1
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        if steps == 1:
                            start_time = obj.get("created_at", start_time)
                        end_time = obj.get("created_at", end_time)

                        t_type = obj.get("type")
                        content = obj.get("content", "")
                        if t_type == "USER_INPUT" and content and len(content.strip()) > 10:
                            clean_c = sanitize_path(content)
                            if clean_c.startswith("<USER_REQUEST>"):
                                clean_c = clean_c.replace("<USER_REQUEST>", "").strip()
                            if len(extracted_dialogue) < 6:
                                extracted_dialogue.append({
                                    "turn": turn_idx,
                                    "role": "user",
                                    "timestamp": obj.get("created_at", start_time),
                                    "content": clean_c[:400].strip()
                                })
                                turn_idx += 1
                        elif t_type in ("PLANNER_RESPONSE", "GENERIC") and content and obj.get("source") == "MODEL" and len(content.strip()) > 40:
                            clean_c = sanitize_path(content)
                            if len(extracted_dialogue) < 6 and extracted_dialogue and extracted_dialogue[-1]["role"] == "user":
                                extracted_dialogue.append({
                                    "turn": turn_idx,
                                    "role": "assistant",
                                    "timestamp": obj.get("created_at", end_time),
                                    "content": clean_c[:400].strip()
                                })
                                turn_idx += 1
                if steps > 0:
                    step_count = steps
                if extracted_dialogue:
                    dialogue = extracted_dialogue
            except Exception as e:
                print(f"[WARN] Error reading transcript for {cid}: {e}")

        # Artifacts
        artifacts = [os.path.basename(p) for p in glob.glob(os.path.join(s_dir, "*.md"))]
        if not artifacts and existing.get("artifacts"):
            artifacts = existing["artifacts"]

        # Decisions belonging to this session
        child_decs = [
            d["id"] for d in decisions
            if d.get("provenance", {}).get("conversation_id") == cid
        ]

        m_dir = os.path.join(s_dir, ".system_generated", "messages")
        msg_count = len(glob.glob(os.path.join(m_dir, "*.json"))) if os.path.exists(m_dir) else existing.get("message_count", 0)

        record = {
            "id": session_id,
            "conversation_id": cid,
            "title": title,
            "date": date_val,
            "start_time": start_time,
            "end_time": end_time,
            "epoch": epoch,
            "epoch_title": epoch_title,
            "step_count": step_count,
            "message_count": msg_count,
            "nesting_depth": existing.get("nesting_depth", 0),
            "parent_session_id": existing.get("parent_session_id"),
            "agent_name": existing.get("agent_name", "main_assistant"),
            "summary": summary,
            "decisions": child_decs or existing.get("decisions", []),
            "decision_ids": child_decs or existing.get("decision_ids", []),
            "participants": participants,
            "artifacts": artifacts,
            "conversation_logs": dialogue
        }
        updated_sessions.append(record)

    with open(sessions_file, "w", encoding="utf-8") as f:
        json.dump({"sessions": updated_sessions}, f, indent=2)
    print(f"[PASS] Synchronized {len(updated_sessions)} sessions from live brain directory.")


def validate_and_sync(base_dir=None, brain_dir=None, sync_sessions=False, validate_only=False, exit_on_error=True):
    target_base = os.path.abspath(base_dir) if base_dir else BASE_DIR
    target_data_dir = os.path.join(target_base, "data")
    decisions_file = os.path.join(target_data_dir, "decisions.json")
    sources_file = os.path.join(target_data_dir, "sources.json")
    sessions_file = os.path.join(target_data_dir, "sessions.json")
    data_js_file = os.path.join(target_data_dir, "data.js")

    def handle_error(msg):
        print(msg)
        if exit_on_error:
            sys.exit(1)
        return False

    print("=" * 60)
    print("Decisn3 — Ingestion, Validation & Sync Tool")
    print("=" * 60)

    if not os.path.exists(decisions_file):
        return handle_error(f"[ERROR] Missing {decisions_file}")

    with open(decisions_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    decisions = data.get("decisions", [])
    print(f"[INFO] Loaded {len(decisions)} decisions from decisions.json")

    sources = []
    if os.path.exists(sources_file):
        with open(sources_file, "r", encoding="utf-8") as f:
            sources_data = json.load(f)
            sources = sources_data.get("sources", [])
        print(f"[INFO] Loaded {len(sources)} sources from sources.json")

    # Optional Live Brain Sync
    if sync_sessions:
        active_brain = brain_dir or DEFAULT_BRAIN_DIR
        sync_brain_sessions(active_brain, decisions, sessions_file)

    # 1. Validate Decision ID Uniqueness
    ids = [d["id"] for d in decisions]
    duplicates = [x for x in ids if ids.count(x) > 1]
    if duplicates:
        return handle_error(f"[ERROR] Duplicate Decision IDs found: {set(duplicates)}")
    print(f"[PASS] All {len(ids)} decision IDs are strictly unique.")

    # 2. Validate Graph Referential Integrity
    id_set = set(ids)
    missing_targets = []
    edge_count = 0
    for d in decisions:
        for rel in d.get("relationships", []):
            edge_count += 1
            target = rel.get("target")
            if target not in id_set:
                missing_targets.append((d["id"], target, rel.get("type")))

    if missing_targets:
        print("[ERROR] Broken relationship edges detected:")
        for src, tgt, rel_type in missing_targets:
            print(f"  - {src} -> '{tgt}' ({rel_type}) does not exist!")
        return handle_error("[ERROR] Referential integrity validation failed.")
    print(f"[PASS] All {edge_count} directed relationships resolve to valid node IDs.")

    # 3. Validate Mandatory Schema Fields on Decisions
    required_fields = [
        "id", "title", "category", "status", "significance",
        "summary", "choice", "context", "provenance", "session_id", "epoch"
    ]
    schema_errors = 0
    for d in decisions:
        for field in required_fields:
            if field not in d:
                print(f"[WARN] Decision {d.get('id')} is missing field '{field}'")
                schema_errors += 1

    if schema_errors == 0:
        print(f"[PASS] Decision schema verification passed ({len(required_fields)} mandatory fields per record).")
    else:
        return handle_error(f"[FAIL] Decision schema verification had {schema_errors} missing fields.")

    # 4. Load & Validate Sessions Schema
    sessions = []
    if os.path.exists(sessions_file):
        with open(sessions_file, "r", encoding="utf-8") as f:
            sessions_data = json.load(f)
            sessions = sessions_data.get("sessions", [])
        print(f"[INFO] Loaded {len(sessions)} sessions from sessions.json (portable offline mode)")
    else:
        return handle_error(f"[ERROR] Missing sessions file: {sessions_file}")

    session_ids = [s["id"] for s in sessions]
    session_duplicates = [x for x in session_ids if session_ids.count(x) > 1]
    if session_duplicates:
        return handle_error(f"[ERROR] Duplicate Session IDs found: {set(session_duplicates)}")

    required_session_fields = [
        "id", "title", "start_time", "end_time", "step_count", "summary", "decisions"
    ]
    session_schema_errors = 0
    for s in sessions:
        for field in required_session_fields:
            if field not in s:
                print(f"[WARN] Session {s.get('id')} is missing field '{field}'")
                session_schema_errors += 1

    if session_schema_errors == 0:
        print(f"[PASS] Sessions schema verification passed ({len(required_session_fields)} mandatory fields per session).")
    else:
        return handle_error(f"[FAIL] Sessions schema verification had {session_schema_errors} missing fields.")

    # 5. Validate Decision-to-Session Referential Integrity
    session_id_set = set(session_ids)
    session_cid_set = set(s.get("conversation_id") for s in sessions if s.get("conversation_id"))

    unmapped_decisions = []
    for d in decisions:
        sid = d.get("session_id")
        cid = d.get("provenance", {}).get("conversation_id")
        if sid not in session_id_set and cid not in session_cid_set:
            unmapped_decisions.append((d["id"], sid, cid))

    if unmapped_decisions:
        return handle_error(f"[ERROR] Decisions unmapped to valid sessions: {unmapped_decisions}")
    print(f"[PASS] All {len(decisions)} decisions successfully map to valid session entities.")

    # Validate that decisions referenced in session['decisions'] exist
    invalid_session_refs = []
    for s in sessions:
        for did in s.get("decisions", []):
            if did not in id_set:
                invalid_session_refs.append((s["id"], did))

    if invalid_session_refs:
        return handle_error(f"[ERROR] Sessions reference non-existent decisions: {invalid_session_refs}")
    print("[PASS] All session decision references resolve to valid decision nodes.")

    # 6. Generate data/data.js (Zero-CORS bundle for offline file:/// launch)
    if validate_only:
        print("[INFO] --validate-only specified. Skipping data.js generation.")
        print("=" * 60)
        return True

    payload = {
        "decisions": decisions,
        "sources": sources,
        "sessions": sessions
    }
    js_content = f"window.DECISN3_DATA = {json.dumps(payload, indent=2)};\n"
    with open(data_js_file, "w", encoding="utf-8") as f:
        f.write(js_content)
    print(f"[PASS] Successfully synchronized data/data.js ({os.path.getsize(data_js_file):,} bytes).")
    print("[SUCCESS] Dashboard data bundle is fully synchronized and validated!")
    print("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(description="Decisn3 Synchronization and Scaffolding CLI")
    parser.add_argument("--brain-dir", type=str, default=None, help="Path to Antigravity brain logs directory")
    parser.add_argument("--sync-sessions", action="store_true", help="Parse live brain logs and re-index sessions")
    parser.add_argument("--validate-only", action="store_true", help="Validate schema and integrity without writing data.js")
    parser.add_argument("--init", type=str, nargs="?", const=".", default=None, help="Initialize decision graph scaffolding into target directory")
    parser.add_argument("--target", type=str, default=None, help="Target directory for initialization (defaults to current working directory)")
    parser.add_argument("--project-name", type=str, default=None, help="Display title for initialized decision graph")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files in target directory if already present")

    args = parser.parse_args()

    if args.init is not None:
        target_path = args.target if args.target else (args.init if args.init != "." else ".")
        try:
            from init_decision_graph import scaffold_project
        except ImportError:
            import importlib.util
            init_script_path = os.path.join(BASE_DIR, "init_decision_graph.py")
            if os.path.exists(init_script_path):
                spec = importlib.util.spec_from_file_location("init_decision_graph", init_script_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                scaffold_project = mod.scaffold_project
            else:
                print("[ERROR] Scaffolding tool init_decision_graph.py not found.", file=sys.stderr)
                sys.exit(1)

        success = scaffold_project(
            target_dir=target_path,
            project_name=args.project_name,
            force=args.force,
            source_dir=BASE_DIR
        )
        sys.exit(0 if success else 1)

    validate_and_sync(
        base_dir=args.target,
        brain_dir=args.brain_dir,
        sync_sessions=args.sync_sessions,
        validate_only=args.validate_only
    )


if __name__ == "__main__":
    main()
