#!/usr/bin/env python3
"""UDO validate: machine-verifiable compliance check (LLM-agnostic floor).
Usage: python3 validate.py [path-to-'UDO Project']   (default: ./UDO Project)
Exit 0 = pass, 1 = violations."""
import sys, json, glob, datetime
from pathlib import Path

proj = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("UDO Project")
errs, warns = [], []

def need(p, kind="file"):
    ok = p.is_dir() if kind == "dir" else p.is_file()
    if not ok: errs.append(f"missing {kind}: {p}")
    return ok

# 1. Required artifacts exist
for d in [".project-catalog/sessions", ".project-catalog/history",
          ".project-catalog/decisions", ".project-catalog/handoffs",
          ".memory/canonical", ".memory/working", ".agents", ".outputs"]:
    need(proj / d, "dir")
for f in ["PROJECT_STATE.json", "PROJECT_META.json", "CAPABILITIES.json",
          "HARD_STOPS.md", "LESSONS_LEARNED.md"]:
    need(proj / f)

# 2. State parses and matches schema basics
state = {}
sp = proj / "PROJECT_STATE.json"
if sp.is_file():
    try:
        state = json.loads(sp.read_text(encoding="utf-8")).get("project_state", {})
        if not state: errs.append("PROJECT_STATE.json: missing 'project_state' wrapper")
        for k in ["goal", "current_phase", "todos", "deferred_debt",
                  "scope_locked", "auto_checkpoint", "circuit_breaker"]:
            if k not in state: errs.append(f"PROJECT_STATE.json: missing field '{k}'")
        for t in state.get("todos", []):
            if not isinstance(t, dict) or not {"id", "task", "status"} <= set(t):
                errs.append(f"todo not structured: {t}")
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        errs.append(f"PROJECT_STATE.json INVALID JSON: {e}")

# 3. Session record for today (warn only: may be mid-first-turn)
today = datetime.date.today().strftime("%Y-%m-%d")
if not glob.glob(str(proj / ".project-catalog" / "history" / f"{today}*.md")):
    warns.append(f"no transcript for {today} (HS-UDO-013)")
if not glob.glob(str(proj / ".project-catalog" / "sessions" / f"{today}*.md")):
    warns.append(f"no session log for {today} yet (HS-UDO-001: required before session end)")

# 4. Deferred debt overdue
for d in state.get("deferred_debt", []):
    if d.get("status") == "open" and d.get("resolve_by", "") not in ("", "next-session") \
       and d["resolve_by"] < today:
        errs.append(f"deferred_debt {d.get('id')} overdue ({d['resolve_by']}): {d.get('item')}")

# 5. Agent drift: .agents/ vs harness copies
canon = {p.name for p in (proj / ".agents").glob("*.md")} - {"README.md"}
hdir = proj / ".claude" / "agents"
if hdir.is_dir():
    gen = {p.name for p in hdir.glob("*.md")}
    if canon - gen: warns.append(f"agents not synced to harness: {sorted(canon - gen)}")
    if gen - canon: errs.append(f"harness agents with no .agents/ source (drift): {sorted(gen - canon)}")

for w in warns: print(f"WARN  {w}")
for e in errs: print(f"ERROR {e}")
print(f"validate: {len(errs)} error(s), {len(warns)} warning(s)")
sys.exit(1 if errs else 0)
