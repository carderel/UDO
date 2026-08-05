# .tools/

## What It Is

This folder is retained for backward compatibility. It is not the active tools registry.

## Where Tools Actually Live

The project's real tool and skill registry is the root `TOOLS/` folder, not this one. See:

- `TOOLS/README.md` - registry overview and how installing a skill works
- `TOOLS/SKILLS_INDEX.md` - installed skills, one row each
- `TOOLS/CATALOG.md` - cached catalog of skills available to install
- `TOOLS/CATALOG-AGENTS.md` - cached catalog of agents available to install
- `TOOLS/skills/` - the installed skill folders themselves

Installed agents are tracked separately in `UDO Project/.agents/`.

## Why This Folder Still Exists

An earlier design proposed an adapters/installed/templates structure inside `UDO Framework/.tools/` (search adapters, storage adapters, per-project tool configs, and a tool-config template). That design was superseded by the simpler root `TOOLS/` registry described above and was never built out. This README previously documented that superseded design as if it existed; it did not. Nothing under this path should be relied on.

## Never Auto-Install

A skill or agent is never installed without explicit user confirmation first. See the Capability Discovery section in `UDO Framework/ORCHESTRATOR.md` for the check-and-ask sequence that governs this.
