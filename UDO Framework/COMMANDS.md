# UDO Commands Reference

## Session Start

| Command | What It Does |
|---------|--------------|
| `Resume` | Quick resume - read essentials, oversight report, ready to work |
| `Resume this project` | Same as Resume |
| `Deep resume` | Full context - read last 3 sessions, detailed history |
| `What's the status?` | Oversight report only (assumes already oriented) |
| `Re-sync` | Re-read all system files after updates |

## Session End

| Command | What It Does |
|---------|--------------|
| `Handoff` | Full session handoff - log session, update state, checkpoint |
| `End session` | Same as Handoff |
| `Quick handoff` | Minimal - summary, next steps, files changed |

## Mid-Session Save

| Command | What It Does |
|---------|--------------|
| `Backup` | Run ALL backup/documentation protocols now (see checklist below) |
| `Back it up` | Same as Backup |
| `Save state` | Same as Backup |

### What `Backup` Does (in order)

1. **Update `PROJECT_STATE.json`** — current goal, phase, todos, in_progress, completed, blockers, session actions
2. **Create/update session log** — write or append to `.project-catalog/sessions/` for this session
3. **Archive session transcript** — append archive marker to `.project-catalog/history/YYYY-MM-DD-HHMM-session-transcript.md`
4. **Create checkpoint** — save progress snapshot to `.checkpoints/`
5. **Reset prompt counter** — `prompt_counter.count_since_last_state_update` → 0
6. **Log decisions** — any undocumented decisions get written to `.project-catalog/decisions/`
7. **Flush working memory** — anything in conversation that should be in `.memory/working/` gets written
8. **Confirm** — report: "Backup complete. State updated. Session logged. Checkpoint created."

## Mode Control

| Command | What It Does |
|---------|--------------|
| `RC mode` | Engage Reasoning Contract mode for analysis |
| `Reasoning contract mode` | Same as above |
| `Analyze [topic]` | RC mode focused on specific topic |
| `Persona: [name]` | Switch to specified persona for delivery |
| `Write [deliverable]` | Triggers persona mode (requires prior RC handoff) |
| `Create handoff` | Generate reasoning-to-persona handoff packet |
| `What mode?` | Report current operating mode |

## Checkpoints

| Command | What It Does |
|---------|--------------|
| `Checkpoint this` | Create manual checkpoint now |
| `List checkpoints` | Show all available checkpoints |
| `Rollback to [name]` | Restore project state from checkpoint |

## Recovery & Compliance

| Command | What It Does |
|---------|--------------|
| `Backfill sessions` | Reconstruct missing session logs from conversation history |
| `Compliance check` | Run self-check, report any gaps in logging/checkpoints/memory/mode |
| `Catch up logging` | Create any missing logs, checkpoints, decision records |

## Status & Oversight

| Command | What It Does |
|---------|--------------|
| `Status` | Give oversight report |
| `Show blockers` | List all current blockers |
| `Show todos` | List current todo items |
| `Show completed` | List completed items |

## Learning

| Command | What It Does |
|---------|--------------|
| `Add to lessons` | Capture a correction as a lesson learned |
| `Remember this` | Add a rule or fact |
| `Review lessons` | Audit lessons for graduation/archival |

## Agents

| Command | What It Does |
|---------|--------------|
| `List agents` | Show active agents |
| `Create agent [name]` | Manually create a specialist agent |
| `Archive agent [name]` | Move agent to archive |

## Memory

| Command | What It Does |
|---------|--------------|
| `Show memory` | List contents of memory system |
| `Add to canonical` | Store verified fact permanently |
| `Clear working memory` | Empty working memory (end of session) |
| `Clear disposable` | Delete speculative/resolved items |

## Context Management

| Command | What It Does |
|---------|--------------|
| `Archive phase [name]` | Compress completed phase to reduce context |
| `Context health` | Show estimated context usage |
| `Compress history` | Summarize and archive old items |

## Emergency

| Command | What It Does |
|---------|--------------|
| `Pause all work` | Stop immediately |
| `Circuit breaker` | Trigger manual circuit breaker |
| `Reset state` | Clear current session, start fresh |

---

## Command Shortcuts

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
| `rc` | RC mode |
| `st` | Session transcript (verify exists, view current, required before work starts per HS-UDO-013) |
| `bu` | Backup |

---

## Mode Quick Reference

### When to Use RC Mode
- Researching information
- Analyzing data
- Evaluating options
- Making recommendations
- Verifying facts
- Strategic planning

### When to Use Persona Mode
- Writing reports (from RC handoff)
- Creating content (from RC handoff)
- Formatting deliverables
- Explaining verified information
- Presenting findings

### The Rule
**RC Mode → Handoff Packet → Persona Mode → Deliverable**

Never skip the handoff. Never analyze in persona mode. Never deliver without prior analysis.

---

## Devil's Advocate Review

| Command | What It Does |
|---------|--------------|
| `Devil's advocate` | Run critical review on current/recent output |
| `DA review` | Same as above |
| `Challenge this` | Same as above |
| `Red team` | Same as above |
| `Skip DA` | Bypass DA review (user accepts risk) |

### What DA Checks
- Evidence gaps
- Logic gaps  
- Assumption gaps
- Perspective gaps
- Completeness gaps
- Actionability gaps
- Temporal gaps

### DA Outputs
Structured critique with severity ratings (High/Medium/Low) and questions for user consideration.

**Full protocol:** See `DEVILS_ADVOCATE.md`

---

## Audience Anticipation

| Command | What It Does |
|---------|--------------|
| `Audience check` | Run standard audience anticipation |
| `AA review` | Same as above |
| `Who will ask what?` | Same as above |
| `Define audience` | Add specific audience profile for targeted questions |
| `Add audience: [role]` | Quick add specific audience |
| `Full review` | DA + Standard AA + any defined specific audiences |
| `Skip AA` | Bypass audience anticipation (user accepts risk) |

### Audience Anticipation Tiers

**Tier 1 - Standard:** Generic stakeholder questions (strategic, financial, risk, implementation, evidence, political)

**Tier 2 - Specific:** Define audience profiles for targeted questions from their perspective

Option 2 always includes Option 1. Specific audiences are additive.

**Full protocol:** See `AUDIENCE_ANTICIPATION.md`
