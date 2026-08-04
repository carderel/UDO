# UDO Documentation

Welcome. This folder explains the **UDO (Universal Dynamic Orchestrator) framework** and how to use it.

## New to UDO?

**Start here, in order:**

1. **[QUICK_START.md](QUICK_START.md)**, install UDO and run your first session (a few minutes)
2. **[FOLDER_GUIDE.md](FOLDER_GUIDE.md)**, understand what each folder does and when to use it
3. **[UDO Framework/START_HERE.md](../UDO Framework/START_HERE.md)**, begin actual work (read by the AI agent at session start)

## What is UDO?

UDO gives AI assistants persistent memory, structure, and accountability across sessions.

**Without UDO:** every AI session starts fresh. Context is lost, decisions are forgotten, handoffs are chaos.

**With UDO:** sessions are connected. The AI reads previous work, maintains state, logs decisions, and hands off cleanly to the next session.

## The 5 Folders

UDO splits a project into 5 root folders, each with one job:

| Folder | Purpose |
|--------|---------|
| `DOCUMENTATION/` | Learn how UDO works (you are here) |
| `TOOLS/` | The skills and agent registry: what capabilities are installed or available to install |
| `UDO Framework/` | The protocol itself. Replaced wholesale on upgrade. You never edit it. |
| `UDO Project/` | Your working context: state, sessions, agents, memory. Upgrades never touch it. |
| `User Provided Files/` | External reference material you bring in from outside the project |

The Framework/Project split exists so an AI cannot accidentally modify shared protocol rules while doing project work. `UDO Framework/` is read-only reference; `UDO Project/` is where the AI actually reads and writes as it works.

When you're ready to work, the AI operates mostly inside `UDO Project/`, guided by the rules in `UDO Framework/`. When you're confused about setup or structure, come back to `DOCUMENTATION/`.

## Key Concepts

- **Sessions**, discrete AI work periods that are logged and tracked in `UDO Project/.project-catalog/sessions/`
- **State**, the current goal, phase, todos, and blockers, tracked in `UDO Project/PROJECT_STATE.json`
- **Checkpoints**, snapshots of progress for recovery if context is lost
- **Agents**, specialized AI personas for specific task types, defined in `UDO Project/.agents/`
- **Memory**, persistent facts, working notes, and temporary scratchpad, in `UDO Project/.memory/`
- **Topics**, the registry of parallel workstreams in `UDO Project/TOPICS.md`
- **Hard Stops**, absolute rules that govern protocol compliance, defined in `UDO Framework/HARD_STOPS.md` and extended in `UDO Project/HARD_STOPS.md`
- **Skills and Agents (TOOLS/)**, reusable capabilities tracked in `TOOLS/SKILLS_INDEX.md` and `TOOLS/CATALOG-AGENTS.md`

See [FOLDER_GUIDE.md](FOLDER_GUIDE.md) for details on each folder and what it manages.

## Where Answers Live

| Question | Answer is in |
|----------|---------------|
| How do I install UDO? | [QUICK_START.md](QUICK_START.md) |
| What does each folder do? | [FOLDER_GUIDE.md](FOLDER_GUIDE.md) |
| What does the AI read at session start? | `UDO Framework/START_HERE.md` |
| What are the absolute rules? | `UDO Framework/HARD_STOPS.md` (plus project-specific additions in `UDO Project/HARD_STOPS.md`) |
| What is the full protocol? | `UDO Framework/ORCHESTRATOR.md` |
| Where are my session logs? | `UDO Project/.project-catalog/sessions/` |
| What is the current project state? | `UDO Project/PROJECT_STATE.json` |
| What skills or agents are available? | `TOOLS/SKILLS_INDEX.md` and `TOOLS/CATALOG-AGENTS.md` |
| Is compliance machine-checkable? | Yes, run `python3 validate.py` from the project root |

## Troubleshooting

**"Where do I read START_HERE?"**
- If you're new to UDO: read `QUICK_START.md` first (this folder).
- If you're resuming work: tell your AI to read `UDO Framework/START_HERE.md` (the framework entry point).

**"Which folder should I edit?"**
- See [FOLDER_GUIDE.md](FOLDER_GUIDE.md) for the detailed role of each folder. Short version: never edit `UDO Framework/`; everything you and the AI change lives in `UDO Project/`.

**"What does the AI read at session start?"**
- `UDO Framework/START_HERE.md`. This is the entry point for AI agents.

**"Where do my session logs go?"**
- `UDO Project/.project-catalog/sessions/`. All session logs are stored here.

## Quick Links

- **[QUICK_START.md](QUICK_START.md)**, setup and first session
- **[FOLDER_GUIDE.md](FOLDER_GUIDE.md)**, complete folder reference
- **[UDO Framework/ORCHESTRATOR.md](../UDO Framework/ORCHESTRATOR.md)**, full UDO protocol (advanced)
- **[UDO Framework/HARD_STOPS.md](../UDO Framework/HARD_STOPS.md)**, absolute rules
- **[UDO Project/PROJECT_STATE.json](../UDO Project/PROJECT_STATE.json)**, current project state

---

**Ready to get started?** Open [QUICK_START.md](QUICK_START.md).
