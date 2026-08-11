# Boot sequence

This project runs on UDO. Do this before answering the first prompt, including a prompt that only asks a question.

## 1. Check where you are

Your working directory must be the folder containing `UDO Framework/` and `UDO Project/`. Run `pwd` and confirm both are present.

If they are one level down (you see a folder like `UDO/` or `UDO-v2.0/` holding them), **stop and say so.** Every path below is relative, so nothing will resolve, and the enforcement hooks in `.claude/settings.json` resolve against the session's project directory, which means they are silently not running. Ask to reopen the session in that folder rather than prefixing paths, because the hooks cannot be fixed by prefixing.

## 2. Read, in this order

1. `UDO Framework/START_HERE.md`
2. `UDO Framework/ORCHESTRATOR.md` in full, and adopt it
3. `UDO Framework/HARD_STOPS.md` and `UDO Project/HARD_STOPS.md`
4. `UDO Framework/REASONING_CONTRACT.md`
5. `UDO Project/PROJECT_STATE.json`
6. `UDO Project/LESSONS_LEARNED.md`
7. `UDO Project/CAPABILITIES.json`
8. The most recent file in `UDO Project/.project-catalog/sessions/`

## 3. Create the session transcript before answering

`UDO Project/.project-catalog/history/YYYY-MM-DD-HHMM-session-transcript.md`, appended after every response. This is HS-UDO-013 and it is not optional. If the file cannot be written, halt and report it.

## 4. Give the orientation report

Goal, phase, delegation capability, last session, next steps. Then ask what to work on.

## Before the session ends

Write a session log to `UDO Project/.project-catalog/sessions/`, update `UDO Project/PROJECT_STATE.json`, and append the archive marker to the transcript. A session that ends without these has failed regardless of what else it produced.

## Two standing rules

- Never edit anything in `UDO Framework/`. It is replaced wholesale on upgrade, so changes there are lost and affect nothing. Project rules go in `UDO Project/HARD_STOPS.md` or `UDO Project/.rules/`.
- Everything you write goes in its designated place under `UDO Project/`. A file elsewhere is invisible to the next session, which defeats the point of writing it.

---

This file is safe to edit. The upgrader adds it only when absent and never overwrites it, so anything you add here about this specific project survives upgrades.
