# Folder Guide: What Each Folder Does

This document explains **what lives where** and **when to look in each folder**.

---

## The 3-Level Structure

```
your-project/
├── DOCUMENTATION/          ← YOU ARE HERE (learning/reference)
├── TOOLS/                  ← Skills & capabilities (coming)
├── UDO/                    ← The framework itself (working space)
├── User Provided Files/    ← External references & handoffs
└── [your project files]
```

Each layer has a specific purpose. Understanding this prevents confusion about which START_HERE to read or where to find things.

---

## Layer 1: DOCUMENTATION/ (Learning)

**Purpose:** Understand how UDO works. **Not a working directory.**

**When to look here:**
- First time using UDO? Start with `README.md`
- Need to install? Go to `QUICK_START.md`
- Confused about folders? This guide
- Need to understand concepts before diving in

**Don't edit these files** unless you're clarifying documentation.

**Files:**
- `README.md` — Overview of UDO and the 3-layer structure
- `QUICK_START.md` — Installation and first session (10 minutes)
- `FOLDER_GUIDE.md` — This file; explains all folders

---

## Layer 2: TOOLS/ (Capabilities - TBD)

**Purpose:** Reusable skills and capabilities (architecture TBD).

**When to look here:**
- User explicitly asks: "What skills are available?"
- Need to create a new skill
- Want to understand how skills work across LLM platforms

**Status:** Folder exists, structure being designed for LLM-agnostic skills.

---

## Layer 3: UDO/ (The Framework - Working Space)

**Purpose:** The actual orchestration engine. **This is where work happens.**

### When to enter UDO/

- Starting a session: Read `UDO/START_HERE.md` first
- Resuming work: Read `UDO/START_HERE.md` (orientation)
- In active session: Work flows through various UDO subfolders (see below)

### What AI agents read at session start

**ONLY THIS FILE:** `UDO/START_HERE.md`

This is the entry point. It tells AI to read protocols, check state, and begin work.

### Inside UDO/ — Key Subfolders

| Subfolder | What It Is | Who Uses It | When |
|-----------|-----------|------------|------|
| `UDO/` root | Core protocols | AI agent | Every session start |
| `.project-catalog/` | Session logs, state, decisions | AI agent + human | Session start (read), session end (write) |
| `.project-catalog/sessions/` | Session history | AI agent | Resume to load context |
| `.project-catalog/history/` | Live session transcripts | AI agent | Real-time during session |
| `.memory/` | Persistent facts | AI agent | When learning/remembering |
| `.agents/` | Specialized AI personas | AI orchestrator | When delegating work |
| `.outputs/` | Deliverables & drafts | AI + human | When creating/reviewing work |
| `.checkpoints/` | Progress snapshots | AI agent | If context is lost, resume from checkpoint |
| `.rules/` | Project constraints | AI agent | Session start (compliance check) |
| `.templates/` | Reusable templates | AI agent | When creating standard documents |

### Core Files in UDO/

| File | Purpose | Read By | When |
|------|---------|---------|------|
| `START_HERE.md` | Onboarding & orientation | AI at session start | Every session |
| `ORCHESTRATOR.md` | Full protocol & rules | AI during work | When unclear about process |
| `PROJECT_STATE.json` | Current goal, phase, todos | AI at session start | Every session |
| `HARD_STOPS.md` | Absolute rules | AI at session start | Every session (non-negotiable) |
| `REASONING_CONTRACT.md` | How to think during analysis | AI when analyzing | When doing research/evaluation |
| `CAPABILITIES.json` | Available tools in this environment | AI during work | When choosing how to execute |
| `VERSION` | Framework version | Upgrade script | When upgrading UDO |

---

## Layer 4: User Provided Files/

**Purpose:** External references, research, handoffs from other sessions.

**When to look here:**
- Need external context that doesn't belong in UDO/
- Reviewing a handoff from a previous session
- Adding research materials

**Don't let important files pile up here** — move them into appropriate UDO subfolders when work begins.

---

## Common Questions

### "Which START_HERE should I read?"

| Situation | Read This |
|-----------|-----------|
| New to UDO, installing for first time | `DOCUMENTATION/QUICK_START.md` |
| Already have UDO, starting a new session | `UDO/START_HERE.md` |
| Confused about structure/folders | `DOCUMENTATION/FOLDER_GUIDE.md` (this file) |
| Already in a session, need help | `UDO/COMMANDS.md` or `UDO/ORCHESTRATOR.md` |

### "Where do I put my work?"

- **Project files** → Your normal project directory (not in UDO/)
- **Research notes** → `UDO/.memory/working/` (temporary) or `.memory/canonical/` (persistent facts)
- **Drafts** → `UDO/.outputs/_drafts/`
- **Final deliverables** → `UDO/.outputs/`
- **Session context I need next time** → `UDO/.project-catalog/sessions/` (auto-created)

### "Where are my session logs?"

`UDO/.project-catalog/sessions/` — One file per session, named `YYYY-MM-DD-HH-MM-session.md`

### "How do I upgrade UDO?"

Stay in main project folder and run:

**Mac/Linux:**
```bash
curl -O https://raw.githubusercontent.com/carderel/UDO-Upgrade-Kit/main/upgrade.sh
chmod +x upgrade.sh
./upgrade.sh
```

**Windows:**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/carderel/UDO-Upgrade-Kit/main/upgrade.ps1" -OutFile upgrade.ps1
.\upgrade.ps1
```

This automatically preserves your `UDO/.project-catalog/` (all session logs and state).

### "I'm confused — what folder do I actually edit?"

Most of the time: **Don't edit UDO framework files directly.**

The framework updates itself. What you DO edit:
- `UDO/PROJECT_STATE.json` — Update your goal/phase/todos (AI helps)
- `UDO/HARD_STOPS.md` — Add project-specific constraints (user editing, rare)
- `UDO/.rules/*.md` — Add project standards (user editing, as needed)
- Files in `.outputs/`, `.memory/`, `.agents/` — AI agent writing as part of work

### "Where do skills go?"

**When implemented:** `TOOLS/` folder (structure TBD)

For now: Skills exist as parts of the protocol in `UDO/COMMANDS.md`

---

## The Mental Model

Think of it this way:

- **DOCUMENTATION/** = "Teach me how UDO works"
- **TOOLS/** = "Show me what I can do" (coming soon)
- **UDO/** = "Let me do the work"
- **User Provided Files/** = "Reference materials I collected"

When you open the project:
1. **First time?** → Start in DOCUMENTATION/
2. **Starting work?** → Enter UDO/, read START_HERE.md
3. **Resuming work?** → Enter UDO/, tell AI "Resume"
4. **Confused?** → Come back to DOCUMENTATION/

---

## See Also

- [QUICK_START.md](QUICK_START.md) — Install and first session
- [UDO/START_HERE.md](../UDO/START_HERE.md) — What AI reads at session start
- [UDO/ORCHESTRATOR.md](../UDO/ORCHESTRATOR.md) — Full protocol reference
