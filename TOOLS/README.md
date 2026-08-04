# TOOLS/ (skills registry)

This folder is the project's local registry of installed skills.

## What a skill is

A skill is a `SKILL.md` folder living at `TOOLS/skills/<name>/`. The folder holds the skill's instructions and any supporting files it needs.

## Installing a skill

Installing a skill is two steps, always done together:

1. Copy the skill's folder into `TOOLS/skills/<name>/`.
2. Append a row for it to `SKILLS_INDEX.md`.

## Never auto-install

A skill is never installed without explicit user confirmation first. See the Capability Discovery section in `UDO Framework/ORCHESTRATOR.md` for the check-and-ask sequence that governs this.

## Files in this folder

- `README.md` (this file)
- `SKILLS_INDEX.md`: installed skills, one row each
- `CATALOG.md`: cached list of skills available to install (source: VoltAgent/awesome-agent-skills)
- `skills/`: the installed skill folders themselves

## Agents

Installed agents are a separate registry, kept in `.agents/` (project side), not here. `TOOLS/CATALOG-AGENTS.md` is the cached catalog of agents available to install, added by a later task.
