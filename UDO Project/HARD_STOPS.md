# Project Hard Stops

This document extends the UDO Framework hard stops with project-specific constraints.

## Framework Hard Stops

The project inherits all framework hard stops from `UDO Framework/HARD_STOPS.md`:

- See `UDO Framework/HARD_STOPS.md` for the authoritative list (some IDs are retired tombstones). All listed items are mandatory.

## Active Project Hard Stops

### PROJECT_HS_001: Mandatory Session Transcript Updates (Hardened v2.1)

**Description:** Session transcript MUST be updated after every user prompt/response cycle with verified file writes and explicit reporting.

**PRE-FLIGHT CHECK (before response creation):**
- Verify `.project-catalog/history/YYYY-MM-DD-HHMM-session-transcript.md` exists and is writable
- If file does not exist or is locked: HALT immediately, report to user, do not proceed with response

**ENFORCEMENT (during response):**
- Append work summary to transcript file after each response completes
- Timestamp each entry: `## Response [N] - [HH:MM:SS UTC]`
- Include: task completed, agents invoked (with skills), decisions made, files changed

**POST-RESPONSE VERIFICATION (mandatory):**
- Verify file write succeeded by checking file modification timestamp
- Report in response ONLY ONE OF:
  - ✅ `Agents used: [AgentName] (Skill: [SkillName])`
    `History Updated [file path] [timestamp from actual file write]`
  - OR ✅ `No agents needed (meta-work: [reason])`
    `History Updated [file path] [timestamp from actual file write]`
  - OR ✗ `VIOLATION: History file write failed - [specific reason]. Escalating to user.`
- If none of above appears in response -> response is incomplete, HALT before next prompt

**Verification Requirements:**
- Agent names must exist in `.agents/` directory (not generic names like "Claude", "Orchestrator")
- Skills must be listed in that agent's CAPABILITIES section (verifiable)
- File timestamp must be AFTER this response started (not old/backdated)
- Exact path must match: `.project-catalog/history/YYYY-MM-DD-HHMM-*.md` pattern

**VIOLATION CIRCUIT BREAKER:**
- If transcript write fails: HALT before accepting next user prompt
- Escalate to user: "Transcript write failed. Requires manual intervention. Unable to proceed."
- Do not resume until user confirms file is writable

**Exception process:** NONE. If file cannot be written, this blocks all work until user fixes it.

---

### PROJECT_HS_002: Delegation (v3, capability-aware)

**Step 0, CAPABILITY CHECK (once per session, at orientation):**
Read CAPABILITIES.json `delegation` block (written at session start per START_HERE).
- `available: true` -> this rule is ACTIVE.
- `available: false` -> this rule is SUSPENDED for the session. Log once in the transcript:
  "PROJECT_HS_002 suspended: no subagent capability in [harness]. Specialized work executes in main context; checkpoint cadence tightened per HS-EXEC-001."

**When ACTIVE:**
- Specialized work (analysis, research, planning, writing, code) MUST be delegated BEFORE execution begins.
- Valid delegates, in preference order:
  1. Installed project agents (`.agents/*.md`, synced to the harness)
  2. Harness-native agents (e.g. Explore, general-purpose, Plan) for search/read/plan work
  3. If neither fits: check the agents catalog (AGENTS_INDEX/CATALOG-AGENTS, see ORCHESTRATOR "Capability Discovery"), offer install; else create from `.templates/agent.md`
- Meta-work needs no agent: orchestration, status updates, direct factual answers, audit-trail writes.

**POST-RESPONSE VERIFICATION (when ACTIVE), report exactly one:**
- `Agents used: [name(s)] ([harness-native | .agents/])` plus one sentence of specific evidence
- `No agents needed (meta-work: [reason])`
- `VIOLATION: [task] executed without delegation` -> HALT before next prompt, escalate to user.

**Evidence rules:** named agents must be real (a `.agents/` file or a harness-native agent the harness actually ran); evidence must be specific ("read 14 files, found 3 candidates"), never "completed the work".

## Relationship to Framework

- All framework hard stops are **mandatory** (see `UDO Framework/HARD_STOPS.md` for the authoritative list; some IDs are retired tombstones)
- Project hard stops **extend** framework rules, not replace them
- When conflict exists, framework rules take precedence
- Project rules add domain-specific constraints

## Enforcement

Hard stops are enforced via:
- Pre-session review (agent reads before starting work)
- Mid-session checks (agent verifies during work)
- Post-session audit (session log references)
- Handoff protocol (constraints communicated to successor)

## Updates

When adding new hard stops:
1. Document clearly with rationale
2. Communicate to all agents
3. Update session logs
4. Note decision in .project-catalog/decisions/

## See Also

- `UDO Framework/HARD_STOPS.md` - Framework hard stops
- `UDO Framework/ORCHESTRATOR.md` - Full protocol
