#!/usr/bin/env python3
"""UDO protocol enforcement hook (Claude Code).
Usage: udo_hook.py <event>   event in {session_start, user_prompt_submit, stop}
Reads hook JSON on stdin (drained); emits hook-control JSON on stdout.
Scope: this project's UDO Project (script lives in <UDO Project>/.udo/).

Behavior (hybrid enforcement, this-project-only):
- session_start      : inject current PROJECT_STATE summary + latest session log (seamless pickup for ANY model).
- user_prompt_submit : inject a one-line UDO compliance status (drift counters).
- stop               : HARD-BLOCK if PROJECT_STATE stale > STATE_BLOCK_THRESHOLD prompts (HS-UDO-008)
                       or no session log exists for today past turn 3;
                       soft on-screen reminder if the transcript is stale; otherwise silent.
"""
import sys, os, json, glob, datetime
from pathlib import Path

EVENT = sys.argv[1] if len(sys.argv) > 1 else ""
SELF = Path(__file__).resolve()
PROJ = SELF.parent.parent                       # <UDO Project>
STATE_FILE = PROJ / "PROJECT_STATE.json"
HIST_DIR = PROJ / ".project-catalog" / "history"
SESS_DIR = PROJ / ".project-catalog" / "sessions"
HOOK_STATE = SELF.parent / "hook-state.json"

STATE_BLOCK_THRESHOLD = 5       # HS-UDO-008: PROJECT_STATE must update within 5 prompts
TRANSCRIPT_WARN_THRESHOLD = 2   # soft reminder if transcript untouched this many prompts

def _mtime(p):
    try: return os.path.getmtime(p)
    except OSError: return 0.0

def newest_transcript_mtime():
    return max((_mtime(f) for f in glob.glob(str(HIST_DIR / "*-session-transcript.md"))), default=0.0)

def load_hook_state():
    try: return json.loads(HOOK_STATE.read_text())
    except Exception: return None

def save_hook_state(s):
    try:
        HOOK_STATE.parent.mkdir(parents=True, exist_ok=True)
        HOOK_STATE.write_text(json.dumps(s))
    except Exception: pass

def sync(hs, advance):
    sm, tm = _mtime(STATE_FILE), newest_transcript_mtime()
    if hs is None:
        hs = {"turn": 1, "state_mtime": sm, "state_turn": 1, "tx_mtime": tm, "tx_turn": 1}
    if advance:
        hs["turn"] = hs.get("turn", 1) + 1
    if sm != hs.get("state_mtime"): hs["state_mtime"] = sm; hs["state_turn"] = hs["turn"]
    if tm != hs.get("tx_mtime"):    hs["tx_mtime"] = tm;    hs["tx_turn"] = hs["turn"]
    return hs

def emit(obj):
    sys.stdout.write(json.dumps(obj)); sys.exit(0)

# drain stdin so the caller never sees a broken pipe
try: sys.stdin.read()
except Exception: pass

if EVENT == "session_start":
    try:
        d = json.loads(STATE_FILE.read_text(encoding="utf-8")).get("project_state", {})
    except Exception:
        emit({"hookSpecificOutput": {"hookEventName": "SessionStart",
              "additionalContext": "[UDO] PROJECT_STATE.json not found/parseable - verify UDO Project location before working."}})
    todos = [t for t in d.get("todos", []) if t.get("status") in ("in_progress", "pending") and t.get("priority") == "high"]
    todo_lines = "; ".join(f"#{t.get('id')} {str(t.get('task',''))[:90]}" for t in todos[:4]) or "(none high-priority)"
    sess = sorted(glob.glob(str(SESS_DIR / "*.md")))
    latest = os.path.basename(sess[-1]) if sess else "(none)"
    ctx = ("[UDO RESUME - auto-injected by hook]\n"
           f"Goal: {d.get('goal','?')}\n"
           f"Phase: {d.get('current_phase','?')}\n"
           f"Active high-priority todos: {todo_lines}\n"
           f"Most recent session log: .project-catalog/sessions/{latest}\n"
           "Follow UDO protocol: keep PROJECT_STATE.json current (Stop hook hard-blocks if >5 prompts stale), "
           "append to today's transcript each cycle, delegate specialized work per PROJECT_HS_002, "
           "log decisions/checkpoints as you go.")
    emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}})

elif EVENT == "user_prompt_submit":
    hs = sync(load_hook_state(), advance=True); save_hook_state(hs)
    ss = hs["turn"] - hs["state_turn"]; st = hs["turn"] - hs["tx_turn"]
    line = (f"[UDO] turn {hs['turn']} · {ss} prompt(s) since PROJECT_STATE update "
            f"(hard-block at >{STATE_BLOCK_THRESHOLD}) · transcript "
            f"{'current' if st == 0 else f'{st} prompt(s) stale'}.")
    emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": line}})

elif EVENT == "stop":
    hs = sync(load_hook_state(), advance=False); save_hook_state(hs)
    ss = hs["turn"] - hs["state_turn"]; st = hs["turn"] - hs["tx_turn"]
    today = datetime.date.today().strftime("%Y-%m-%d")
    has_log = bool(glob.glob(str(SESS_DIR / f"{today}*.md")))
    if ss > STATE_BLOCK_THRESHOLD or (hs["turn"] > 3 and not has_log):
        why = []
        if ss > STATE_BLOCK_THRESHOLD:
            why.append(f"PROJECT_STATE.json stale {ss} prompts (limit {STATE_BLOCK_THRESHOLD})")
        if hs["turn"] > 3 and not has_log:
            why.append(f"no session log for {today} in .project-catalog/sessions/")
        emit({"decision": "block",
              "reason": "UDO COMPLIANCE: " + "; ".join(why) +
                        ". Before ending: update PROJECT_STATE.json, create/append today's session log, "
                        "and append this cycle's work to today's transcript."})
    if st >= TRANSCRIPT_WARN_THRESHOLD:
        emit({"systemMessage": f"[UDO reminder] Session transcript {st} prompt(s) stale - append this cycle's "
                               "work to .project-catalog/history/ to keep the cross-LLM handoff current."})
    emit({"suppressOutput": True})

else:
    emit({"suppressOutput": True})
