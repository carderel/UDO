# UDO: Universal Dynamic Orchestrator

**Current version: 2.2.5**

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

There is a single source for UDO: `https://github.com/carderel/UDO` (clone it, or download the zip). See `DOCUMENTATION/QUICK_START.md` for full install steps for a brand new project versus adding UDO to an existing one, on Mac, Linux, and Windows.

### Fastest path, new project

```bash
git clone https://github.com/carderel/UDO.git my-project
cd my-project
```

Then start your LLM CLI from that folder and say: Read 'UDO Framework/START_HERE.md' and begin.

### Upgrading an existing UDO project

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

If you already have `upgrade.py`, preview the plan, then apply it:

```bash
python3 upgrade.py --dry-run
python3 upgrade.py
```

`upgrade.py` auto-detects what you have (a fresh directory, an existing v2.x project, a legacy v4.x install with everything inside a single `UDO/` subfolder, or a legacy v4.x install with the protocol files sitting directly at the project root, mixed in with your own work) and prints a manifest, one line per path, tagged ADD, REPLACE, TRANSFORM, or PRESERVE, before it changes anything. `--dry-run` just prints that manifest and exits. A real run shows the same manifest, asks for confirmation (skip with `--yes`), then backs up the whole target to `.udo-backup-<timestamp>/`, applies exactly the manifest it printed, and finishes by running `validate.py` against the result. If self-validation fails, the upgrade stops and reports the backup path so you can restore.

A legacy v4.x `UDO/` install is carried forward in full: everything under it is ported into the new `UDO Framework/` + `UDO Project/` layout, the old `UDO/` folder is renamed to `UDO-v4-LEGACY-DO-NOT-EDIT/` (kept for reference, never deleted), and a migration record is written to `UDO Project/.project-catalog/decisions/`. If instead your v4.x protocol files sit directly at the project root (no `UDO/` subfolder), `upgrade.py` recognizes that shape too (`--mode migrate-root`, auto-detected when three or more of `ORCHESTRATOR.md`, `HARD_STOPS.md`, `PROJECT_STATE.json`, `COMMANDS.md`, and `REASONING_CONTRACT.md` are present at the root): the recognized v4.x files and folders are ported into `UDO Project/` and then moved into `UDO-v4-LEGACY-DO-NOT-EDIT/`, and everything else at the root, your own files, is left exactly where it was. If only one or two of those markers are present, the auto-detector refuses to guess and asks for an explicit `--mode` instead of risking a fresh install overwriting a partial v4.x install.

Other flags: `--source <path-or-url>` installs from a local checkout or zip instead of the default GitHub release; `--mode fresh|upgrade|migrate|migrate-root|refresh` forces a lane instead of auto-detecting, required if `UDO Framework/VERSION` is missing, empty, or unparseable. `upgrade.sh` (Linux/macOS) and `upgrade.ps1` (Windows) are thin wrappers around the same script and take the same flags.

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
├── UDO Project/                ← Your isolated working context, upgrades add missing pieces here but never overwrite your data (PROJECT_STATE.json, CAPABILITIES.json, HARD_STOPS.md, and PROJECT_META.json get value-preserving updates instead: existing values are kept, only missing pieces are added)
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
2. Add project-specific rules to `/UDO Project/HARD_STOPS.md` (PROJECT_HS_003 and beyond)
3. Never modify Framework files directly

## Upgrade Scripts

`upgrade.py` is a single, cross-platform, stdlib-only Python script that does the actual work; `upgrade.sh` (Linux/macOS) and `upgrade.ps1` (Windows) are equivalents that just call it with whatever arguments you pass. See "Upgrading an existing UDO project" above for the flow and flags.

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
| v2.2.5  | 2026-08-07 | Upgrade detection refuses to install fresh over a project whose real UDO install sits in a subfolder |
| v2.2.4  | 2026-08-06 | START_HERE orientation step 0: non-blocking framework update check against the canonical repo |
| v2.2    | 2026-08-04 | Bridge removed, enforcement hooks, TOOLS/ skills and agents registry, documentation rewrite for the real v2 architecture |
| v2.1    | 2026-03-10 | Session transcripts, conflict detection refinements |
| v2.0    | 2026-03-10 | Framework/Project separation, multi-LLM safety |

The legacy v4.x series (v4.9, v4.10, and earlier) was superseded by the v2.0 rewrite above; it is not compatible with this repository and is not maintained.

## Changelog

### v2.2.5 (2026-08-07)

- Auto-detection now scans one level below the target. A project whose real UDO install lives in a subfolder (`UDO-v2.0/`, `UDO/`, or similar) no longer falls through to the fresh lane, which used to install an empty placeholder project beside the real one and leave the actual work un-upgraded
- The refusal names the subfolder, its detected version, and the exact command to upgrade it directly; `--mode fresh` still overrides when a second, separate install really is what you want
- A `.udo-backup-*` folder left behind by an earlier run does not trip the new guard

### v2.2.4 (2026-08-06)

- START_HERE orientation step 0: a non-blocking framework update check against the canonical repo, so a session reports version drift instead of silently running stale

### v2.2.3 (2026-08-05)

- User .gitignore is merged, never replaced

### v2.2.2 (2026-08-05)

- v4-at-root installs now migrate automatically; fresh mode refuses ambiguous targets

### v2.2.1 (2026-08-05)

- Hotfix: clean failure and guidance when backup hits recursively nested checkpoints or over-long paths, no partial backups left behind

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
- Real `upgrade.py` (fresh/upgrade/migrate detection, dry-run manifest, self-validating)

## Contributing

Found a bug or want to improve the framework? Please open an issue or submit a pull request.

## License

MIT License - See LICENSE file for details.
