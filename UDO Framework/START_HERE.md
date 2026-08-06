# 🚀 New AI? Start Here.

## Framework vs Project Structure in v2.0

**New in v2.0:** UDO is now split into two separate folder hierarchies for multi-LLM safety.

### Why This Matters

When multiple AI assistants work on the same project, isolation is critical. v2.0 separates:

- **`/UDO Framework/`**: the immutable reference files (read-only for your project)
- **`/UDO Project/`**: your working context (where you read and write)

This prevents AI agents from accidentally modifying framework rules while still allowing project-specific customization.

### Architecture Diagram

```
Your Project Root
├── /UDO Framework/                 ← Immutable reference
│   ├── START_HERE.md               (DO NOT EDIT)
│   ├── ORCHESTRATOR.md             (DO NOT EDIT)
│   ├── HARD_STOPS.md               (DO NOT EDIT)
│   ├── REASONING_CONTRACT.md       (DO NOT EDIT)
│   └── [all other protocol files]
│
└── /UDO Project/                   ← Your working context
    ├── HARD_STOPS.md               (Extend Framework rules here)
    ├── PROJECT_STATE.json
    ├── .project-catalog/           (sessions, decisions, history)
    ├── .memory/                    (your facts and working notes)
    ├── .outputs/                   (your deliverables)
    └── [all your project data]
```

### Path Reference Table

| Item | In Framework | In Project |
|------|--------------|-----------|
| Core orchestration rules | `/UDO Framework/ORCHESTRATOR.md` | Read-only reference |
| Hard stops (immutable) | `/UDO Framework/HARD_STOPS.md` | Reference in `/UDO Project/HARD_STOPS.md` |
| Hard stops (project-specific) | N/A | Add project-specific hard stops in `/UDO Project/HARD_STOPS.md` (see that file for current numbering) |
| Session logs | N/A | `/UDO Project/.project-catalog/sessions/` |
| Decisions | N/A | `/UDO Project/.project-catalog/decisions/` |
| Memory (canonical) | N/A | `/UDO Project/.memory/canonical/` |
| Memory (working) | N/A | `/UDO Project/.memory/working/` |
| Deliverables | N/A | `/UDO Project/.outputs/` |

### Key Rule: HS-UDO-014 (New in v2.0)

**NEVER modify files in `/UDO Framework/`.**

The Framework is the reference copy. It will be updated by the upgrade tool. Your customizations go in `/UDO Project/`.

---

## ⚠️ Important: Do NOT Use Symlinks

The UDO Framework MUST be a real directory structure, not a symlink.

**Bad:**
```bash
ln -s /actual/location/UDO\ Framework ./UDO\ Framework  # ❌ WRONG
```

**Why:** Framework immutability (HS-UDO-014) requires isolated folder structure. Symlinks break isolation and can cause:
- Multiple projects accidentally sharing Framework modifications
- Loss of Framework immutability guarantees
- Data corruption across projects

**Good:**
```bash
cp -r /template/UDO\ Framework ./UDO\ Framework  # ✓ CORRECT
```

---

## ⚠️ MANDATORY FIRST STEP

**STOP. Read `ORCHESTRATOR.md` NOW and adopt its protocols before doing anything else.**

Do not proceed until you have:
1. Read ORCHESTRATOR.md completely
2. Understood the SESSION LOGGING requirement (you MUST log every session)
3. Understood CHECKPOINT triggers (checkpoint at phase completion, before risky operations, and at session end)
4. Understood when to CREATE AGENTS (2+ distinct personas needed)
5. Understood the MEMORY SYSTEM (canonical/working/disposable)
6. Understood the DUAL-MODE SYSTEM (RC mode for analysis, Persona mode for delivery)

**Say this before starting work:**
> "I have read ORCHESTRATOR.md and will follow UDO protocol. I understand I must: log sessions, checkpoint progress, create agents when needed, use the memory system, and operate in the correct mode (RC for analysis, Persona for delivery)."

---

## After Reading Orchestrator

Complete these orientation steps:

0. **Check for framework updates (non-blocking):** compare the local `UDO Framework/VERSION`
   against the canonical repo:
   `curl -fsSL --max-time 5 "https://raw.githubusercontent.com/carderel/UDO/main/UDO%20Framework/VERSION"`
   - If the remote version is newer, add one line to your orientation report:
     "Framework update available: local X → latest Y (upgrade is user-gated; run `upgrade.py` from the canonical repo)."
   - NEVER auto-upgrade and NEVER modify `UDO Framework/` yourself (HS-UDO-014).
     Upgrading is the user's decision, executed via the upgrade tool.
   - If the request fails (offline, timeout, no curl): skip silently and continue.
1. **Check hard stops:** `HARD_STOPS.md` (rules you must NEVER violate)
2. **Declare your delegation capability (MANDATORY).** Determine whether this harness can spawn subagents. Write the result to CAPABILITIES.json (`delegation` block) and include ONE of these lines in your orientation report:
   - "Delegation: AVAILABLE via [mechanism]. Custom agents sync from .agents/."
   - "Delegation: NOT AVAILABLE in [harness]. All specialized work will execute in this context window. PROJECT_HS_002 suspended (logged). Checkpoint cadence tightened."
   If the stored value differs from what you detect (LLM switch), say so explicitly: "Previous session had [X]; this session has [Y]. Planned delegated work will run [accordingly]."
3. **Check reasoning contract:** `REASONING_CONTRACT.md` (how to think during analysis)
4. **Check current status:** `PROJECT_STATE.json`
5. **Check lessons:** `LESSONS_LEARNED.md` (mistakes to avoid)
6. **Know your environment:** `CAPABILITIES.json`
7. **Check recent sessions:** `.project-catalog/sessions/` (most recent file)

## Then Give Your Orientation Report:

> "I've read ORCHESTRATOR.md and REASONING_CONTRACT.md and reviewed the project.
> - **Goal:** [from PROJECT_STATE.json]
> - **Phase:** [current phase]
> - **Delegation:** [AVAILABLE via ... | NOT AVAILABLE, single-context mode]
> - **Last session:** [summary from most recent session log]
> - **Transcript:** [path if exists, or "none"]; offer to review if user wants additional context
> - **Next steps:** [from PROJECT_STATE.json or last session]
> Ready to continue."

---

## Quick Reference

### Dual-Mode System

| Mode | Use For | Key Rule |
|------|---------|----------|
| **RC Mode** | Analysis, research, decisions | Every claim needs evidence |
| **Persona Mode** | Writing, creating, delivering | Only use facts from RC handoff |

**Flow:** RC Mode → Handoff Packet → Persona Mode → Deliverable

### Session Commands

| Command | What AI Does |
|---------|--------------| 
| `Resume` | Quick resume with oversight report |
| `Deep resume` | Full context with recent sessions |
| `Handoff` | Create session log, update state, end session |
| `Quick handoff` | Minimal session log |
| `Backup` | Run ALL backup/documentation protocols mid-session |
| `Status` | Oversight report only |
| `Backfill sessions` | Reconstruct missing session logs |

### Mode Commands

| Command | What AI Does |
|---------|--------------|
| `RC mode` | Engage Reasoning Contract mode |
| `Analyze [topic]` | RC mode for specific analysis |
| `Persona: [name]` | Switch to persona for delivery |
| `Write [deliverable]` | Persona mode (needs RC handoff first) |

### Command Shortcuts

| Short | Full Command |
|-------|--------------|
| `r` | Resume |
| `dr` | Deep resume |
| `h` | Handoff |
| `qh` | Quick handoff |
| `s` | Status |
| `cp` | Checkpoint this |
| `bf` | Backfill sessions |
| `cc` | Compliance check |
| `bu` | Backup (full mid-session save) |

---

## Rule Hierarchy

| Layer | Location | Override? |
|-------|----------|-----------|
| 0 | `HARD_STOPS.md` | NEVER |
| 0.5 | `REASONING_CONTRACT.md` | NEVER (during analysis) |
| 1 | `.rules/*.md` | With justification |
| 2 | `.agents/*.md` | By orchestrator |
| 3 | `LESSONS_LEARNED.md` | Easily |

---

## Compliance Checklist

Before starting ANY work, confirm you will:

- [ ] **MANDATORY:** Create session transcript at `/UDO Project/.project-catalog/history/YYYY-MM-DD-HHMM-session-transcript.md` BEFORE accepting first user prompt (see HS-UDO-013)
- [ ] Write/append to transcript in real-time after each response (before accepting next prompt)
- [ ] Log this session to `/UDO Project/.project-catalog/sessions/` before ending
- [ ] Append archive marker to transcript when ending session
- [ ] Checkpoint at phase completion, before risky operations, and at session end
- [ ] Create agents if task requires 2+ distinct personas
- [ ] Document major decisions in `/UDO Project/.project-catalog/decisions/`
- [ ] Use memory system for facts discovered during work in `/UDO Project/.memory/`
- [ ] Update `/UDO Project/PROJECT_STATE.json` after completing work
- [ ] Use RC mode for analysis, Persona mode for delivery
- [ ] Create handoff packet before switching from RC to Persona mode
- [ ] **New in v2.0:** NEVER modify files in `/UDO Framework/`; extend rules in `/UDO Project/HARD_STOPS.md` instead
- [ ] **New in v2.0:** When multiple AIs work the same project, read `/UDO Project/PROJECT_STATE.json` before updating (HS-UDO-015)

**If you find yourself working without logging, STOP and catch up.**
**If you find yourself making claims without evidence, STOP and engage RC mode.**
**If you find yourself modifying framework files, STOP: your changes go in `/UDO Project/` instead.**
