# Agents

Agent definitions for this project. `.agents/` is the source of truth. Nothing here is optional decoration: every file in this directory is an active persona the orchestrator can delegate to under PROJECT_HS_002.

## Format

Each agent is a single markdown file, `{agent-name}.md`, with YAML frontmatter followed by a body:

```markdown
---
name: agent-name
description: What this agent does and when to invoke it.
tools: [file_read, web_search]
model: sonnet   # optional; omit to use the harness default
---
You are a [specialization] operating under UDO protocol.
- Bullet point instructions specific to this agent's job.
- 4-6 bullets total, plus mode framing (RC-mode or Persona mode).

## Learned Rules
<!-- corrections to this agent accumulate here; this file is the source of truth, harness copies are regenerated -->
```

`name`, `description`, and `tools` are required. `model` is optional. The `tools:` list is a permission list, not a suggestion: display it whenever an agent is proposed for install (see ORCHESTRATOR "Capability Discovery").

## Source of truth, harness copies are generated

`.agents/*.md` is authoritative. If the active harness supports custom agent files (for example Claude Code's `.claude/agents/`), those harness copies are generated artifacts, regenerated from `.agents/` by the resume protocol's Agent sync step.

- Never hand-edit a harness copy. Edit the `.agents/` file and re-sync.
- `validate.py` compares `.agents/` against the harness directory and flags drift: an agent missing from the harness (not yet synced) or a harness agent with no `.agents/` source (orphaned).
- `AGENTS_INDEX.md` and this `README.md` are registry/reference files, not agents; they are excluded from the sync and drift checks.

## Install flow (Capability Discovery)

New agents are only added through the Capability Discovery order in `UDO Framework/ORCHESTRATOR.md`:

1. An installed agent in `.agents/` already fits -> delegate to it.
2. Nothing installed fits -> check `TOOLS/CATALOG-AGENTS.md`. On a match, show the agent's `tools:` permission list and ask before installing.
3. No match, or the user declines -> proceed without an agent and note the gap in the session log.

An install never happens without explicit user confirmation. A skill is instructions; an agent is instructions plus tool permissions, which is a bigger grant.

## Learned Rules accumulate here only

Corrections to an agent's behavior are written into that agent's own `## Learned Rules` section in `.agents/{agent-name}.md`, never into a harness copy. The next Agent sync carries the correction into the harness automatically.

## Seed agents

- `researcher.md` - deep research and evidence collection (RC-mode)
- `data-auditor.md` - validates datasets and claims against live sources (RC-mode)
- `strategist.md` - builds recommendations from RC-mode evidence packets
- `technical-writer.md` - produces deliverables from reasoning handoffs (Persona mode)

## See Also

- `AGENTS_INDEX.md` - registry table of installed agents and their sync status
- `TOOLS/CATALOG-AGENTS.md` - cached catalog of installable agents
- `.templates/agent.md` - long-form fallback template PROJECT_HS_002 points to when nothing installed or cataloged fits; it already carries the frontmatter header above, so filling in its placeholders and saving the file to `.agents/{agent-name}.md` is enough to register it
