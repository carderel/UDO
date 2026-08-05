# UDO Hook

This directory holds `udo_hook.py`, the Claude Code enforcement hook wired via the repo root `.claude/settings.json`: it injects PROJECT_STATE context at session start, shows a drift status line on each prompt, and hard-blocks Stop if PROJECT_STATE.json or today's session log is stale.

Windows note: if `python3` is not on PATH, change the `command` value in the root `.claude/settings.json` to `py -3` or the full path to your Python interpreter.

`hook-state.json` in this folder is runtime state written by the hook itself; it is not part of the tracked protocol and is gitignored.
