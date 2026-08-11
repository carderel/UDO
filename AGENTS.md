# Boot sequence

This project runs on UDO. Do all four steps before answering the first prompt, including a prompt that only asks a question.

This file is the canonical boot document, and it is deliberately not named for any one tool. `CLAUDE.md`, `GEMINI.md` and any other harness file in this folder are one-line pointers here. If your harness reads a file that does not exist yet, create it as a pointer to this one and say that you did.

## 1. Create the session transcript, before anything else

`UDO Project/.project-catalog/history/YYYY-MM-DD-HHMM-session-transcript.md`

Append to it after every response, including this one. This is HS-UDO-013. If the file cannot be written, halt and report it.

Why this is step 1 and not step 4: the rule used to live in a compliance checklist part-way through `UDO Framework/START_HERE.md`, which meant it could only be discovered by reading files, which takes responses, which means the rule was already broken by the time anyone learned it existed. A session that reported exactly that is why the order changed. Do this first and the rule is satisfiable.

## 2. Check where you are

Your working directory must be the folder holding `UDO Framework/` and `UDO Project/`. Confirm both are present.

If they are one level down, inside a folder like `UDO/` or `UDO-v2.0/`, **stop and say so.** Two things are broken, and only one is visible. The protocol's paths are relative, so nothing resolves. Less visibly, harness configuration in this folder (hooks, permissions, agent definitions) is only read when this folder is the session's root, so any enforcement it provides is silently absent. Prefixing paths hides the first problem and does nothing about the second. Ask to reopen the session in the right folder.

## 3. Read, in this order

1. `UDO Framework/START_HERE.md`
2. `UDO Framework/ORCHESTRATOR.md` in full, and adopt it
3. `UDO Framework/HARD_STOPS.md` and `UDO Project/HARD_STOPS.md`
4. `UDO Framework/REASONING_CONTRACT.md`
5. `UDO Project/PROJECT_STATE.json`
6. `UDO Project/LESSONS_LEARNED.md`
7. `UDO Project/CAPABILITIES.json`
8. `UDO Project/TOPICS.md`
9. The most recent file in `UDO Project/.project-catalog/sessions/`

## 4. Give the orientation report, then stop

Goal, phase, delegation capability, last session, next steps. If `PROJECT_STATE.json` still carries `placeholder-project-id`, this is an uninitialized install: say so, and ask for the goal rather than inventing one.

## Before the session ends

Write a session log to `UDO Project/.project-catalog/sessions/`, update `UDO Project/PROJECT_STATE.json`, and append the archive marker to the transcript. A session that ends without these has failed, whatever else it produced.

## Two standing rules

- Never edit anything in `UDO Framework/`. It is replaced wholesale on upgrade, so changes there are lost and affect nothing. Project rules belong in `UDO Project/HARD_STOPS.md` or `UDO Project/.rules/`.
- Everything you write goes in its designated place under `UDO Project/`. A file written elsewhere is invisible to the next session, which defeats the point of writing it.

---

This file is safe to edit and the upgrader never overwrites it, so anything you add about this specific project survives upgrades.
