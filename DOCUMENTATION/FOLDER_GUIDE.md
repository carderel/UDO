# Folder Guide: What Each Folder Does

This document explains **what lives where** and **when to look in each folder**.

---

## The 5 Folders

```
your-project/
├── DOCUMENTATION/          ← you are here (learning and reference)
├── TOOLS/                  ← installed skills and agents registry
├── UDO Framework/          ← the protocol itself (replaced wholesale on upgrade)
├── UDO Project/            ← your working context (upgrades preserve everything in it)
├── User Provided Files/    ← external references and handoffs
└── [your project files]
```

Two of these folders carry the real architectural weight: `UDO Framework/` and `UDO Project/`. The split exists so an AI cannot accidentally modify shared protocol rules while doing project work.

- `UDO Framework/` is read-only reference. When you upgrade UDO, this folder is replaced wholesale. You never edit it.
- `UDO Project/` is yours. It holds state, sessions, agents, and memory. Upgrades preserve it: existing files are never overwritten; only missing structural pieces get added. The one exception is four files (`PROJECT_STATE.json`, `CAPABILITIES.json`, `HARD_STOPS.md`, `PROJECT_META.json`) that get value-preserving updates: existing values are kept, only missing pieces are added.

`TOOLS/`, `DOCUMENTATION/`, and `User Provided Files/` are supporting folders around that core split.

---

## DOCUMENTATION/ (Learning)

**Purpose:** understand how UDO works. Not a working directory.

**When to look here:**
- First time using UDO? Start with `README.md`.
- Need to install? Go to `QUICK_START.md`.
- Confused about folders? This guide.
- Need to understand concepts before diving in.

**Don't edit these files** unless you're correcting the documentation itself.

**Files:**
- `README.md`, overview of UDO and the 5 folders
- `QUICK_START.md`, installation and first session
- `FOLDER_GUIDE.md`, this file; explains all folders

---

## TOOLS/ (Skills and Agents Registry)

**Purpose:** the project's local registry of installed skills, and the cached catalog of skills and agents available to install.

**When to look here:**
- User asks "what skills are available?"
- Need to install a new skill or agent.
- Want to see what's already installed.

**Files:**
- `README.md`, how skills are installed and where the boundary with `.agents/` sits
- `SKILLS_INDEX.md`, installed skills, one row each
- `CATALOG.md`, cached catalog of skills available to install (source: VoltAgent/awesome-agent-skills)
- `CATALOG-AGENTS.md`, cached catalog of agents available to install (source: VoltAgent/awesome-claude-code-subagents)
- `skills/`, the installed skill folders themselves, one `SKILL.md` folder per skill

**Never auto-install.** A skill or agent is never installed without explicit user confirmation. See the Capability Discovery section in `UDO Framework/ORCHESTRATOR.md` for the check-and-ask sequence.

**Note:** installed *agents* live in `UDO Project/.agents/`, not here. `TOOLS/CATALOG-AGENTS.md` is only the catalog of what's available to install.

---

## UDO Framework/ (The Protocol, Read-Only)

**Purpose:** the actual orchestration protocol: rules, standards, and infrastructure. **Immutable.** Replaced wholesale by the upgrade tool; you never hand-edit it.

### When to enter UDO Framework/

- Starting a session: the AI reads `UDO Framework/START_HERE.md` first.
- Need the full protocol: `UDO Framework/ORCHESTRATOR.md`.
- Need the absolute rules: `UDO Framework/HARD_STOPS.md`.

### What AI agents read at session start

**The entry point is `UDO Framework/START_HERE.md`.** It tells the AI to read the protocols, declare its delegation capability, check project state, and begin work.

### Core files in UDO Framework/

| File | Purpose |
|------|---------|
| `START_HERE.md` | Onboarding and orientation; the entry point every session |
| `ORCHESTRATOR.md` | Full protocol specification |
| `HARD_STOPS.md` | Absolute rules (HS-UDO-xxx, HS-OUT-xxx, HS-EXEC-xxx, and more), including HS-OUT-001: never use em dashes in any output, deliverable, or committed file |
| `COMMANDS.md` | Session commands and shortcuts |
| `REASONING_CONTRACT.md` | How to think during analysis (RC mode) |
| `EVIDENCE_PROTOCOL.md` | Standards for evidence-based claims |
| `DEVILS_ADVOCATE.md` | Critical challenge protocol |
| `AUDIENCE_ANTICIPATION.md` | Communication standards |
| `TEACH_BACK_PROTOCOL.md` | Knowledge transfer standards |
| `OVERSIGHT_DASHBOARD.md` | Monitoring and visibility standards |
| `HANDOFF_PROMPT.md` | Template for agent handoff prompts |
| `VERSION` | Framework version |

Subfolders (`.templates/`, `.takeover/`, `.tools/`) hold reusable templates and infrastructure the framework provides to every project.

---

## UDO Project/ (Your Working Context)

**Purpose:** everything that makes this project *this* project. Upgrades preserve it: existing files are never overwritten; only missing structural pieces get added. The exception is four files (`PROJECT_STATE.json`, `CAPABILITIES.json`, `HARD_STOPS.md`, `PROJECT_META.json`) that get value-preserving updates instead: existing values are kept, only missing pieces are added.

### When to enter UDO Project/

- Every session: the AI checks `PROJECT_STATE.json`, `TOPICS.md`, and recent files in `.project-catalog/`.
- During work: the AI reads and writes across the subfolders below as it goes.

### Key subfolders

| Subfolder | What it is | When it's used |
|-----------|-----------|-----------------|
| `.project-catalog/sessions/` | Session logs, one per session | Written at session end, read on resume |
| `.project-catalog/history/` | Live, append-only session transcripts | Written in real time during a session |
| `.project-catalog/decisions/` | Decision records with rationale | Written when a major decision is made |
| `.project-catalog/handoffs/` | Handoff packets between RC mode and Persona mode, or between sessions | Written at mode or session boundaries |
| `.project-catalog/checkpoints/` and `.checkpoints/` | Progress snapshots | Written on auto-checkpoint triggers, read to recover from lost context |
| `.memory/canonical/` | Permanent, authoritative facts | Read and written whenever established facts change |
| `.memory/working/` | Session-scoped working notes | Read and written during active work |
| `.memory/disposable/` | Ephemeral, prompt-level scratch | Written and discarded within a session |
| `.agents/` | Agent persona definitions (source of truth) | Read by the orchestrator when delegating |
| `.rules/` | Project-specific constraints | Checked at session start |
| `.outputs/` | Deliverables and drafts | Written when creating or reviewing work |
| `.inputs/` | Source materials and requirements | Read when starting new work |
| `.udo/` | The enforcement hook (`udo_hook.py`) and its runtime state | Runs automatically if you're on Claude Code |
| `.claude/agents/` | Synced Claude Code agent copies (Claude Code settings that wire up the hook live at the repo root `.claude/settings.json`, not here) | Read by Claude Code, not by other LLM CLIs |

### Core files in UDO Project/

| File | Purpose |
|------|---------|
| `PROJECT_STATE.json` | Current goal, phase, todos, deferred debt |
| `PROJECT_META.json` | Project identity |
| `CAPABILITIES.json` | Feature matrix, including the delegation-capability declaration the AI makes at session start |
| `TOPICS.md` | Registry of parallel workstreams: one row per topic, with status, owner, and authoritative sources |
| `HARD_STOPS.md` | Project-specific rules that extend `UDO Framework/HARD_STOPS.md` |
| `LESSONS_LEARNED.md` | Insights and mistakes to avoid |
| `NON_GOALS.md` | What this project explicitly does not do |
| `PROJECT-README.md` | Project-level navigation, similar in spirit to this guide but scoped to one project |

### Agents (`.agents/`)

Four seed personas ship with every new project:

| Agent | Role |
|-------|------|
| `researcher` | Gathers and verifies information |
| `data-auditor` | Checks data quality and consistency |
| `strategist` | Reasons about approach and tradeoffs |
| `technical-writer` | Writes deliverables; enforces HS-OUT-001 (no em dashes) on every output |

`.agents/AGENTS_INDEX.md` is the registry of what's installed. `.agents/*.md` is the source of truth; any harness-specific copy (for example `.claude/agents/`) is a generated artifact, kept in sync by the resume protocol's agent sync step, and flagged by `validate.py` if it drifts.

### The Enforcement Hook (Claude Code only)

`UDO Project/.udo/udo_hook.py`, wired through the repo root `.claude/settings.json`, is an optional but recommended enforcement layer for Claude Code. It:
- injects `PROJECT_STATE.json` context at session start,
- shows a drift status line on each prompt,
- hard-blocks session end (the Stop event) if `PROJECT_STATE.json` or today's session log is stale.

It only runs in Claude Code. If you're on a different LLM CLI, use `python3 validate.py` (see below) instead.

---

## User Provided Files/

**Purpose:** external references, research, and handoffs from outside the project.

**When to look here:**
- Need external context that doesn't belong inside `UDO Project/` yet.
- Reviewing a handoff from a previous session or a different project.
- Adding research materials.

**Don't let important files pile up here.** Move them into the right `UDO Project/` subfolder once work begins.

---

## Common Questions

### "Which START_HERE should I read?"

| Situation | Read this |
|-----------|-----------|
| New to UDO, installing for the first time | `DOCUMENTATION/QUICK_START.md` |
| Already have UDO, starting a new session | `UDO Framework/START_HERE.md` |
| Confused about structure or folders | `DOCUMENTATION/FOLDER_GUIDE.md` (this file) |
| Already in a session, need a command reference | `UDO Framework/COMMANDS.md` or `UDO Framework/ORCHESTRATOR.md` |

### "Where do I put my work?"

- **Project files** go in your normal project directory, not inside `UDO Framework/` or `UDO Project/`.
- **Research notes** go in `UDO Project/.memory/working/` (temporary) or `.memory/canonical/` (persistent facts).
- **Drafts** go in `UDO Project/.outputs/`.
- **Session context you need next time** goes in `UDO Project/.project-catalog/sessions/` (created automatically).
- **A new parallel workstream** gets a row in `UDO Project/TOPICS.md`.

### "Where are my session logs?"

`UDO Project/.project-catalog/sessions/`, one file per session.

### "How do I upgrade UDO?"

**Coming from an older version?** If your install does not have `upgrade.py` yet (any UDO v4.x, v2.0, or v2.1, since your install predates it), download the latest script first, then run it:

Mac/Linux:
```bash
curl -O https://raw.githubusercontent.com/carderel/UDO/main/upgrade.py
python3 upgrade.py --dry-run
```

Windows (PowerShell):
```powershell
Invoke-WebRequest https://raw.githubusercontent.com/carderel/UDO/main/upgrade.py -OutFile upgrade.py
py -3 upgrade.py --dry-run
```

The script always fetches the newest UDO release from the repo, so downloading the latest `upgrade.py` first is all the updating the updater ever needs.

If you already have `upgrade.py`, run `python3 upgrade.py --dry-run` first to see exactly what will change: a manifest tagged ADD, REPLACE, TRANSFORM, or PRESERVE for every affected path, printed without touching anything. Review it, then run `python3 upgrade.py` for real. It shows that same manifest, prompts for confirmation unless you pass `--yes`, then backs up the whole project to `.udo-backup-<timestamp>/`, applies the manifest, and finishes by running `validate.py` against the result, failing loudly with the backup path if self-validation does not pass.

`upgrade.py` auto-detects a fresh directory, an existing v2.x project, or a legacy single-folder v4.x `UDO/` install. A v4.x install is migrated in full: everything under `UDO/` is ported into the new `UDO Framework/` + `UDO Project/` layout, the old `UDO/` folder is renamed to `UDO-v4-LEGACY-DO-NOT-EDIT/` (kept for reference, never deleted), and a migration record is written under `UDO Project/.project-catalog/decisions/`.

Useful flags: `--source <path-or-url>` to install from a local checkout or zip instead of the default GitHub release; `--mode fresh|upgrade|migrate|refresh` to force a lane instead of auto-detecting, required if `UDO Framework/VERSION` is missing, empty, or unparseable. `upgrade.sh` (Linux/macOS) and `upgrade.ps1` (Windows) are equivalent wrappers around the same script.

### "How do I check I'm following protocol correctly?"

Run `python3 validate.py` from the project root, on any LLM CLI. It checks required files and folders exist, `PROJECT_STATE.json` parses and matches its schema, today's session has a log, deferred debt isn't overdue, and installed agents are in sync with any harness copies.

If you're on Claude Code, the enforcement hook in `UDO Project/.udo/` does a lighter version of this automatically on every prompt and blocks session end on drift. It's optional and only available on Claude Code; `validate.py` works everywhere.

### "I'm confused. What folder do I actually edit?"

Never edit `UDO Framework/`. It gets replaced on every upgrade, so anything you put there is lost anyway.

What you DO edit, inside `UDO Project/`:
- `PROJECT_STATE.json`, update your goal, phase, and todos (the AI helps with this)
- `HARD_STOPS.md`, add project-specific constraints
- `.rules/*.md`, add project standards
- `TOPICS.md`, register new workstreams
- Files in `.outputs/`, `.memory/`, `.agents/`, written by the AI as part of its work

### "Where do skills and agents go?"

- Installed skills live in `TOOLS/skills/`, tracked in `TOOLS/SKILLS_INDEX.md`.
- Installed agents live in `UDO Project/.agents/`, tracked in `.agents/AGENTS_INDEX.md`.
- Catalogs of what's available to install (not yet installed) live in `TOOLS/CATALOG.md` (skills) and `TOOLS/CATALOG-AGENTS.md` (agents).
- Nothing installs automatically; every install needs explicit user confirmation.

---

## The Mental Model

- **DOCUMENTATION/** = "teach me how UDO works"
- **TOOLS/** = "show me what I can install or already have"
- **UDO Framework/** = "these are the rules, read-only"
- **UDO Project/** = "this is my project, do the work here"
- **User Provided Files/** = "reference material I brought in"

When you open the project:
1. First time? Start in `DOCUMENTATION/`.
2. Starting work? Tell the AI to read `UDO Framework/START_HERE.md`.
3. Resuming work? Tell the AI `Resume`.
4. Confused? Come back to `DOCUMENTATION/`.

---

## See Also

- [QUICK_START.md](QUICK_START.md), install and first session
- [README.md](README.md), what UDO is and where answers live
