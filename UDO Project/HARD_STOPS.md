# Project Hard Stops

This document extends the UDO Framework hard stops with project-specific constraints.

## Framework Hard Stops

The project inherits all framework hard stops from `UDO Framework/HARD_STOPS.md`:

- HS-UDO-001 through HS-UDO-009 (mandatory)
- See framework documentation for full details

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

> NOTE: rewritten in v2.2, see this file after Task 6.

### PROJECT_HS_002: Mandatory Agent Delegation (Hardened v2.1)

**Description:** All specialized tasks MUST be delegated to appropriate agents. Agent MUST be invoked BEFORE execution begins.

**PRE-FLIGHT CHECK (before task execution):**
- Classify task:
  - Specialized work (data analysis, planning, writing, research) -> **REQUIRES AGENT**
  - Meta-work (orchestration, status updates, direct Q&A responses) -> **NO AGENT**
  - Unclear -> Treat as specialized, must create/invoke agent
- If specialized and no agent exists: CREATE agent from `.templates/agent.md` FIRST, then invoke
- Post intent to transcript: "Task classification: [type]. Agent required: [yes/no]. Agent: [name] if applicable."

**ENFORCEMENT (during task execution):**
- If specialized work: Agent MUST be invoked and MUST execute the task
- Orchestrator coordinates, does NOT execute
- If execution begins without agent invocation on specialized work -> **VIOLATION**

**POST-RESPONSE VERIFICATION (mandatory):**
- Report in response ONLY ONE OF:
  - ✅ `Agents used: [AgentName] (Skill: [SkillName])`
    `- Evidence: [specific work product, 1 sentence]`
    `- Verified: Agent file exists, skill in CAPABILITIES, work matches skill`
  - OR ✅ `No agents needed (meta-work: [description])`
  - OR ✗ `VIOLATION: Specialized work executed without agent delegation - [task name]`
- If none of above appears in response -> response is incomplete, HALT before next prompt

**Verification Requirements (for agent claims):**
- Agent name must exist: `.agents/[AgentName].md` must be a real file
- Skill must exist: Listed in that agent's CAPABILITIES section
- Evidence must be specific: "analyzed 5 documents and found 3 patterns" ✅ / "completed the work" ✗
- Evidence must match claimed skill: Don't claim strategist wrote copy (copywriter's skill)

**Multi-Agent Completeness:**
- If 3+ agents executed work, ALL must be reported
- Missing agents from report -> agent underreporting -> escalate to user
- Use format: `Agents used: [Agent1] (Skill: X), [Agent2] (Skill: Y), [Agent3] (Skill: Z)`

**VIOLATION CIRCUIT BREAKER:**
- If specialized task was executed without agent -> HALT before next prompt
- Escalate to user: "Agent delegation violation. Task must be redone by appropriate agent."
- Do not resume until user confirms correction approach
- If agent doesn't exist or skill not in CAPABILITIES -> HALT, report which one, escalate

**What requires agent delegation (strict interpretation):**
- Any data analysis or document review -> data-auditor
- Strategic planning or roadmapping -> strategist
- Content creation (copy, code, docs) -> copywriter / technical-writer
- Research (keywords, market, competitive) -> researcher-specialist
- Anything plausibly assignable to a named specialist persona

**Exception process:** NONE for specialized tasks. Always delegate.
- Single-sentence clarifications of user intent do not require agents
- Direct answers to factual user questions (no analysis) do not require agents
- Everything else: delegate

## Relationship to Framework

- All framework hard stops (HS-UDO-001 through HS-UDO-009) are **mandatory**
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
