# UDO v2.0: Universal Dynamic Orchestrator

**Current version: 2.2**

**Multi-LLM Safe Session Orchestration Framework**

UDO v2.0 solves a critical problem: **AIs accidentally working in framework code instead of project code**.

This release introduces architectural separation with `/UDO Framework/` (immutable reference) and `/UDO Project/` (isolated working context) to make scope unambiguous at the filesystem level.

## What's New in v2.0

- ✅ **Framework/Project Separation**: Dual-folder architecture prevents scope confusion
- ✅ **Multi-LLM Safety**: Concurrent AI coordination with conflict detection (HS-UDO-015)
- ✅ **Session Transcripts**: Write-once, append-only raw session exchanges for data recovery
- ✅ **Conflict Detection**: Automatic detection of simultaneous modifications across AIs
- ✅ **Framework Immutability**: Hard stops prevent Framework contamination (HS-UDO-014)
- ✅ **Real-time Persistence**: Transcripts written after each response (guarantees max data loss is current in-progress response)

## Quick Start

There is a single source for UDO: `https://github.com/carderel/UDO-v2.0` (clone it, or download the zip). See `DOCUMENTATION/QUICK_START.md` for full install steps for a brand new project versus adding UDO to an existing one, on Mac, Linux, and Windows.

### Fastest path, new project

```bash
git clone https://github.com/carderel/UDO-v2.0.git my-project
cd my-project
```

Then start your LLM CLI from that folder and say: Read 'UDO Framework/START_HERE.md' and begin.

### Upgrading an existing UDO project

The bundled `upgrade.sh` / `upgrade.ps1` scripts predate the v2 two-folder layout and are being redesigned in a separate workstream. Until they ship, upgrade manually: back up your project, replace the `UDO Framework/` folder with the one from a fresh clone of `https://github.com/carderel/UDO-v2.0`, and leave `UDO Project/` untouched.

## Directory Structure

Cloning (or unzipping) the repo gives you 5 folders at your project root:

```
your-project/
├── UDO Framework/              ← Read-only, replaced wholesale on upgrade
│   ├── ORCHESTRATOR.md        (main specification)
│   ├── START_HERE.md          (entry point for new AIs)
│   ├── HARD_STOPS.md          (mandatory protocol rules)
│   ├── COMMANDS.md            (session commands and shortcuts)
│   └── [other framework files]
│
├── UDO Project/                ← Your isolated working context, upgrades never touch this
│   ├── PROJECT_STATE.json     (current goal, phase, todos)
│   ├── PROJECT_META.json      (project identity)
│   ├── TOPICS.md              (parallel workstreams)
│   ├── .agents/               (agent personas)
│   ├── .project-catalog/      (sessions, decisions, history)
│   ├── .memory/               (canonical, working, disposable)
│   ├── .outputs/               (deliverables)
│   ├── .udo/                  (Claude Code enforcement hook, optional)
│   └── [other project files]
│
├── TOOLS/                       ← Installed skills and agents registry
├── DOCUMENTATION/                ← Onboarding guides (start here if you're new)
└── User Provided Files/          ← External references and handoffs
```

See `DOCUMENTATION/FOLDER_GUIDE.md` for what lives in each folder and when to use it.

## The Problem v2.0 Solves

**Before v2.0:** AIs would accidentally work in the framework repo (modifying shared rules) instead of their isolated project folder. This broke other projects using the same framework.

**Solution:** Filesystem-level scope enforcement. `/UDO Framework/` is visually distinct from `/UDO Project/`, making it obvious where work belongs. Hard stops (HS-UDO-014, HS-UDO-015, HS-UDO-016) prevent violations.

## Documentation

- **New to UDO?** Start with `DOCUMENTATION/QUICK_START.md`
- **Want the folder-by-folder tour?** Read `DOCUMENTATION/FOLDER_GUIDE.md`
- **New AI, starting a session?** It should read `UDO Framework/START_HERE.md`
- **Architecture overview?** Read `UDO Framework/README.md`
- **Protocol specification?** Read `UDO Framework/ORCHESTRATOR.md`
- **Mandatory rules?** Check `UDO Framework/HARD_STOPS.md`

## For Framework Developers

The Framework is intentionally immutable. All customizations belong in `/UDO Project/HARD_STOPS.md` or `/UDO Project/.rules/`.

To extend the framework for your project:
1. Read `/UDO Framework/ORCHESTRATOR.md` (immutability section)
2. Add project-specific rules to `/UDO Project/HARD_STOPS.md` (HS-UDO-014 and beyond)
3. Never modify Framework files directly

## Upgrade Scripts

The repository ships `upgrade.sh` (Linux/macOS) and `upgrade.ps1` (Windows), but both still target the pre-v2 layout and repos and are not yet a working upgrade path for this release. A v2-aware rewrite is planned as a separate workstream. Until then, use the manual upgrade steps above: replace `UDO Framework/` with a fresh clone of `https://github.com/carderel/UDO-v2.0` and leave `UDO Project/` untouched.

## Multi-LLM Coordination

When multiple AIs work on the same project:

1. **Framework is shared** (all AIs read the same immutable rules)
2. **Project is isolated** (each AI works in Project context)
3. **Conflict detection is built-in** (HS-UDO-015: read PROJECT_STATE.json before updating)
4. **Session logs are separate** (no cross-AI contamination)

See `/UDO Framework/ORCHESTRATOR.md` "Concurrent AI Safety" section for details.

## Version History

| Version | Release | Major Features |
|---------|---------|---|
| v2.2    | 2026-08-04 | Bridge removed, enforcement hooks, TOOLS/ skills and agents registry, documentation rewrite for the real v2 architecture |
| v2.1    | 2026-03-10 | Session transcripts, conflict detection refinements |
| v2.0    | 2026-03-10 | Framework/Project separation, multi-LLM safety |

The legacy v4.x series (v4.9, v4.10, and earlier) was superseded by the v2.0 rewrite above; it is not compatible with this repository and is not maintained.

## Changelog

### v2.2 (2026-08-04)

- Bridge module removed
- Enforcement hooks + `validate.py`
- Schema v2.2
- Boundary fix (Framework/Project scope enforcement)
- Capability declaration
- Unified records
- Event checkpoints
- Lessons split
- UDO-Lite
- TOPICS registry
- Skills + agents registries
- HS-OUT-001
- Documentation rewrite

## Contributing

Found a bug or want to improve the framework? Please open an issue or submit a pull request.

## License

MIT License - See LICENSE file for details.

---

**Last Updated:** 2026-03-10
**Status:** PRODUCTION READY
**Build:** Bulletproof (100% red-team validated)
