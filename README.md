# UDO: Universal Dynamic Orchestrator

**Current version: 2.5.0**

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

There is a single source for UDO: `https://github.com/carderel/UDO`. Clone it somewhere temporary and install from there; do not use the clone itself as your project (see below). See `DOCUMENTATION/QUICK_START.md` for full install steps for a brand new project versus adding UDO to an existing one, on Mac, Linux, and Windows.

### New project

```bash
git clone --depth 1 https://github.com/carderel/UDO.git /tmp/udo-latest
mkdir my-project && cd my-project
python3 /tmp/udo-latest/upgrade.py .
```

Then start your LLM CLI **from `my-project`**. It will boot itself: `AGENTS.md` is installed at that root and carries the boot sequence, and `CLAUDE.md` and `GEMINI.md` point at it.

**Do not clone this repository as your project.** It used to be the documented shortcut and it produces a subtly broken install:

- The project metadata is never stamped, because stamping happens in `upgrade.py`. You get current framework files next to `PROJECT_STATE.json` claiming an older version, and a session that reads its own state will report the wrong one.
- You inherit this repository's git history and its `origin`, so commits you make in your project target the UDO repository rather than one of your own.
- You get `tests/`, the release tooling and the distribution's `DOCUMENTATION/`, none of which belong in a project.

`validate.py` now fails on all of this, so an install made the old way will tell you.

### Where to install it

Install UDO **at the root of the project it serves**, so `UDO Framework/` and `UDO Project/` sit beside your own files. That is what the Framework/Project split is for.

Installing into a `UDO/` subfolder inside a larger folder works, but the session has to be opened at that subfolder, not the folder above it. Opened above, the protocol's relative paths do not resolve and, less visibly, the harness configuration at the install root is never read, so UDO's own enforcement hooks are silently inactive for the whole session.

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

**One caveat on that `curl`.** `raw.githubusercontent.com` is CDN-cached and has been observed serving a copy of `upgrade.py` several releases behind for a while after a release, while the release zip it downloads is already current. The run then reports the new version and installs the new files, but silently does none of the newer upgrader's work. You cannot spot it afterwards either, because a fresh install copies `upgrade.py` from the source over the one you downloaded. Since v2.3.3 the script compares itself against the release and warns when it is behind. If you want to skip the question entirely, clone instead:

```bash
git clone --depth 1 https://github.com/carderel/UDO.git /tmp/udo-latest
python3 /tmp/udo-latest/upgrade.py <YOUR_PROJECT> --dry-run
```

If you already have `upgrade.py`, preview the plan, then apply it:

```bash
python3 upgrade.py --dry-run
python3 upgrade.py
```

`upgrade.py` auto-detects what you have (a fresh directory, an existing v2.x project, a legacy v4.x install with everything inside a single `UDO/` subfolder, or a legacy v4.x install with the protocol files sitting directly at the project root, mixed in with your own work) and prints a manifest, one line per path, tagged ADD, REPLACE, TRANSFORM, or PRESERVE, before it changes anything. `--dry-run` just prints that manifest and exits. A real run shows the same manifest, asks for confirmation (skip with `--yes`), then backs up the whole target to `.udo-backup-<timestamp>/`, applies exactly the manifest it printed, and finishes by running `validate.py` against the result. If self-validation fails, the upgrade stops and reports the backup path so you can restore.

A legacy v4.x `UDO/` install is carried forward in full: everything under it is ported into the new `UDO Framework/` + `UDO Project/` layout, the old `UDO/` folder is renamed to `UDO-v4-LEGACY-DO-NOT-EDIT/` (kept for reference, never deleted), and a migration record is written to `UDO Project/.project-catalog/decisions/`. If instead your v4.x protocol files sit directly at the project root (no `UDO/` subfolder), `upgrade.py` recognizes that shape too (`--mode migrate-root`, auto-detected when three or more of `ORCHESTRATOR.md`, `HARD_STOPS.md`, `PROJECT_STATE.json`, `COMMANDS.md`, and `REASONING_CONTRACT.md` are present at the root): the recognized v4.x files and folders are ported into `UDO Project/` and then moved into `UDO-v4-LEGACY-DO-NOT-EDIT/`, and everything else at the root, your own files, is left exactly where it was. If only one or two of those markers are present, the auto-detector refuses to guess and asks for an explicit `--mode` instead of risking a fresh install overwriting a partial v4.x install.

Other flags: `--source <path-or-url>` installs from a local checkout or zip instead of the default GitHub release; `--mode fresh|upgrade|migrate|migrate-root|refresh` forces a lane instead of auto-detecting, required if `UDO Framework/VERSION` is missing, empty, or unparseable. `upgrade.sh` (Linux/macOS) and `upgrade.ps1` (Windows) are thin wrappers around the same script and take the same flags.

## Directory Structure

A completed install gives you these at your project root:

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
| v2.5.0  | 2026-08-11 | Handoff bundle import (Phase B); backup no longer dies on a symlink |
| v2.4.3  | 2026-08-11 | Seed agents are actually installed into the harness instead of shipping inert |
| v2.4.2  | 2026-08-11 | Clone-as-project installs are detected and refused by validate.py; install docs corrected |
| v2.4.1  | 2026-08-11 | Bootstrap is LLM-agnostic (AGENTS.md canonical); transcript rule moved to step 1; PROJECT_META version stamped |
| v2.4.0  | 2026-08-11 | Ships a CLAUDE.md so a fresh install boots the protocol on its own, and says where to open the session |
| v2.3.3  | 2026-08-11 | The upgrader says so when it is older than the release it is installing |
| v2.3.2  | 2026-08-11 | Version stamp reaches the migrate lanes too |
| v2.3.1  | 2026-08-11 | Installed state reports the version it was actually installed or upgraded to |
| v2.3.0  | 2026-08-10 | Handoff bundles: export an install to a verifiable bundle, and restore a target from a backup |
| v2.2.8  | 2026-08-09 | Legacy migration folder is no longer mistaken for a nested install |
| v2.2.7  | 2026-08-09 | Any folder named UDO-anything counts as an install for detection; cleanup handles scaffolds that were journaled into or half-removed by hand |
| v2.2.6  | 2026-08-09 | Upgrade lane refuses to "upgrade" an unused placeholder scaffold while the real install sits below it; detection regression fixtures |
| v2.2.5  | 2026-08-07 | Upgrade detection refuses to install fresh over a project whose real UDO install sits in a subfolder |
| v2.2.4  | 2026-08-06 | START_HERE orientation step 0: non-blocking framework update check against the canonical repo |
| v2.2    | 2026-08-04 | Bridge removed, enforcement hooks, TOOLS/ skills and agents registry, documentation rewrite for the real v2 architecture |
| v2.1    | 2026-03-10 | Session transcripts, conflict detection refinements |
| v2.0    | 2026-03-10 | Framework/Project separation, multi-LLM safety |

The legacy v4.x series (v4.9, v4.10, and earlier) was superseded by the v2.0 rewrite above; it is not compatible with this repository and is not maintained.

## Changelog

### v2.5.0 (2026-08-11)

**`--import-handoff` (v2.3 Phase B).** Rebuilds a project from a handoff bundle. Held back deliberately until real bundles from every field layout had been read by hand; that gate is met.

Safety comes from two properties, neither of which is "verify the bundle":

- **Nothing moves until the replacement exists and validates.** The new install is built in a staging directory and checked there. A crash, a bad bundle or a failed validation before the swap leaves the project exactly as it was, proven by a fixture that forces validation to fail and asserts the target is byte-identical
- **The bundle is compared against what it would replace.** Checking a bundle against its own manifest proves it is internally perfect, which a bundle exported from the wrong folder also is. Import refuses when the bundle carries fewer records than the install being retired, and prints the comparison

Four refusals, ordered by how badly they indicate the import is wrong: a real install one level below the target, a bundle thinner than what it replaces, unclassified items nobody described in NOTES.md, and another session active in the target. Each has an explicit override. The previous install is moved to `UDO-PRE-IMPORT-<timestamp>/`, never deleted, and every run prints its own `--restore` command.

**Also fixed, found by rehearsing the import against a real project:**

- `backup()` followed symlinks, so a single dangling one failed the backup and therefore every upgrade and import, before anything started. Container Site had one: its `.claude/skills/web-perf` pointed at a path one of our own migrate-root runs had moved, so that project could not be upgraded at all and nothing had said so. Links are now copied as links
- Backup failures reported the offending path truncated from the wrong end, showing directory prefix instead of filename, and dropped the underlying OS error entirely whenever a path was identified, making "name too long", "permission denied" and "no such file" indistinguishable. Both fixed, and that is what found the symlink in one run
- Export silently skipped symlinks. Nothing was lost in practice because the only one was dangling, which is exactly how it stayed invisible. They are now recorded in the manifest with their target and whether it exists, upholding the rule that nothing goes missing unnamed

`tests/test_import.py`, 12 fixtures, all but two of them refusals.

### v2.4.3 (2026-08-11)

- **Agents are now generated into the harness by the installer.** `UDO Project/.agents/` has always been the documented source of truth, with harness copies described as "regenerated by the resume protocol's Agent sync step". That step was prose asking the LLM to do it, and across every install in the field no session ever did: the four seed agents shipped marked `synced-to-harness: pending` and stayed inert. Sync now runs in code on every lane, and `--sync-agents` re-runs it after you add or edit one
- Sync never deletes. A harness agent with no `.agents/` source is yours and is left alone, and `validate.py` now explains how to register it instead of just naming it as drift
- `AGENTS_INDEX.md` gets its `synced-to-harness` column updated to `yes`, since a column that still says `pending` after the copies exist is worse than not tracking it

### v2.4.2 (2026-08-11)

The documented "fastest path" for a new project was `git clone` the distribution and use it as your project. That produced a subtly broken install, and a real session found it by reporting an "uninitialized install on UDO 2.2" while the framework beside it read 2.4.1.

- `validate.py` now **errors** when `UDO Framework/VERSION` disagrees with `udo_version` in `PROJECT_STATE.json` or `PROJECT_META.json`. Stamping happens in `upgrade.py`, so an install that never ran it carries current framework files and stale project metadata, and nothing said so
- `validate.py` now **errors** when the folder's git remote points at the UDO repository. Cloning in place means commits made in your project target UDO itself, which is the worst part of that shortcut and the least visible
- `validate.py` warns when the distribution's `tests/` is present, another sign of the same thing
- Install docs rewritten: clone to a temp directory and run `upgrade.py` into your project folder. A new section says where to install it and what breaks when the session is opened above the install
- Installing into a folder named `UDO*` now prints a note explaining that the session must be opened there rather than at the parent, and that installing at the project root is the intended shape

### v2.4.1 (2026-08-11)

All three items came from a real onboarding session's orientation report.

- **The bootstrap file is no longer named for one vendor.** v2.4.0 shipped a `CLAUDE.md`, which baked in one harness and contradicted the point of an LLM-agnostic framework: switch to Gemini and there is no `GEMINI.md`. `AGENTS.md` now holds the canonical boot sequence, with `CLAUDE.md` and `GEMINI.md` as one-line pointers to it. A harness whose filename is not covered creates its own pointer during initialization, per AGENTS.md step 1. All are add-if-absent, so a hand-written bootstrap is never overwritten
- **Transcript creation is now step 1, before the reading list.** HS-UDO-013 requires a transcript before the first response, but the rule lived in a compliance checklist part-way through `UDO Framework/START_HERE.md`, so it could only be discovered by reading, which takes responses, which means it was already broken by the time anyone learned it existed. A session reported exactly that violation and was correct. Fixed in both AGENTS.md and START_HERE.md
- **`PROJECT_META.json` version fields are stamped at install time.** v2.3.1 fixed this for `PROJECT_STATE.json` and missed the file next to it, so an install could report framework 2.3.1, state 2.2 and metadata 2.0 simultaneously. Both files are now stamped on every lane, and the shipped metadata no longer hardcodes a version or a creation date

### v2.4.0 (2026-08-11)

Found by installing 2.3.3 into a new folder and watching a real session try to onboard.

- **Ships `CLAUDE.md`.** Claude Code reads it automatically, so a fresh install now boots the protocol without anyone having to say "read START_HERE". Every existing project had hand-written its own; the distribution never shipped one. Added on fresh installs and add-if-absent on upgrades, so a project's own CLAUDE.md is never overwritten
- The shipped `CLAUDE.md` opens by checking the working directory, because the failure it exists to catch is silent: if the install sits one level down, the protocol's relative paths do not resolve AND `.claude/settings.json` is never read, so the enforcement hooks do not run at all. Prefixing paths does not fix the hooks, so it says to reopen the session instead
- A successful install now prints where to open the session, and notes when the folder is not a git repository, since the protocol writes history that would not be version controlled
- Export: source folders that deliberately merge into one bundle folder (`.checkpoints` and `.project-catalog/checkpoints`, `communications` into handoffs) could silently overwrite same-named files. Now suffixed and recorded, like every other rename

### v2.3.3 (2026-08-11)

- The upgrader now compares its own version against the release it is installing and warns when it is behind, naming both versions and offering a clone command that bypasses the CDN. Found by installing 2.3.2 from GitHub and getting a correct-looking install that had skipped the new work: `raw.githubusercontent.com` served a pre-2.3.1 script while the zip was current. A `SCRIPT_VERSION` constant carries this, held in step with the framework VERSION by a test rather than by release discipline
- Install docs now state the caveat and give a clone-based alternative

### v2.3.2 (2026-08-11)

- The v2.3.1 version stamp only reached `fresh` and `upgrade`. `main()` dispatches the two migrate lanes straight to their own apply functions, bypassing `apply()` where the stamp lived, so a migrated project still reported the wrong version. Now stamped on all four lanes and verified against a real v4-at-root and a real v4-in-`UDO/` shape

### v2.3.1 (2026-08-11)

- `udo_version` in `UDO Project/PROJECT_STATE.json` is now stamped from the framework VERSION at install time, on every lane. It was a literal in the shipped file that nothing updated, so a fresh 2.3.0 install reported 2.2, and an upgraded project kept reporting whatever version it was first installed at. That mismatch has already cost a real project a decision record to resolve

### v2.3.0 (2026-08-10)

Phase A of the handoff bundle. Neither command in this release can destroy anything: export is read-only by invariant, restore only recovers.

- `--export` writes a handoff bundle: normalized state, every session log, transcript, decision, handoff and checkpoint, project files, and a manifest listing **every file the exporter saw** with a sha256 and a disposition of classified, unclassified or excluded with a reason. Completeness is checkable against the source rather than against the bundle's own contents
- `--raw` copies the whole tree with no classification at all. It consults neither detection nor the name table, so it works on a layout nobody has seen before. Where export cannot resolve an install it names the ambiguity and points here instead of dead-ending
- Anything the exporter cannot place goes to `UNCLASSIFIED/` with its original path and is listed in `NOTES.md` for a session to describe. Unrecognized no longer means skipped
- The bundle is written outside the project by default, so the read-only invariant is literally true and is tested by checksumming the entire source tree before and after
- Windows-hostile paths (reserved device names, trailing dots, case-insensitive collisions) are made portable on the way in, with every rename recorded in the manifest
- `--restore BACKUP_DIR` puts a target back from any `.udo-backup-*` this tool wrote, moving what is currently there into a quarantine folder first. Failure paths now end at a command rather than a directory path
- `tests/test_export.py`, 15 fixtures. Rehearsed against four real installs covering every layout in the field

Import (`--import-handoff`) is Phase B, deliberately not in this release. It is the only part that can destroy a project, and it will be built after real bundles from every layout have been inspected by hand.

### v2.2.8 (2026-08-09)

- `UDO-v4-LEGACY-DO-NOT-EDIT/`, the folder a completed migrate or migrate-root run leaves behind, starts with `UDO` and so was caught by the v2.2.7 name test. It was reported as a nested install and could be suggested as an upgrade target, which is exactly backwards: it is already-migrated content the run itself marked do-not-edit. Now skipped by name, in both `upgrade.py` and `cleanup-misinstall.py`

### v2.2.7 (2026-08-09)

- Detection now treats a folder **named** `UDO`-anything as an install even when its contents match none of the known layouts. A partial, renamed or hand-edited install used to be invisible to every content check and got scaffolded straight over. The refusal says the contents were unrecognized rather than guessing at them, and an explicit `--mode` still overrides
- `cleanup-misinstall.py` handles a scaffold that sessions have been **journaling into**. It refuses by default, since clearing it would discard real session logs, transcripts and decisions, and explains the `--merge-records` option, which copies those records into the real project first and copies the scaffold's PROJECT_STATE.json across whole for a person to read. State is never machine-merged
- `cleanup-misinstall.py` handles a root somebody has already **half-cleaned by hand**. Deleting `UDO Framework/` and `UDO Project/` leaves ten other things the installer wrote sitting at the root; those are now identified from the backup snapshot and cleared
- A leftover is only moved when its name is one the installer actually writes AND it is absent from the pre-run backup. A file you created after the bad run is never mistaken for installer output

### v2.2.6 (2026-08-09)

- The v2.2.5 guard was preventive only. Once a mis-install had already happened, the placeholder scaffold presented a valid `UDO Framework/VERSION`, so detection took the upgrade lane on its first check and never reached the nested scan. The run upgraded the empty scaffold, reported success, and left the real project un-upgraded one folder down
- The upgrade lane now refuses when the install at the target has never been used (shipped `project_id`, no goal, no todos, no counted sessions or prompts, no session logs) and a real install sits directly below it. A used install is never affected, and a placeholder with nothing underneath it upgrades normally. `--mode upgrade` overrides
- `cleanup-misinstall.py`: repairs projects where this already happened. Quarantines the scaffold rather than deleting it, and repoints `.claude/` enforcement hooks at the real install. Dry run by default
- Fixed: the nested-install scan reported a v2.x install's own `UDO Framework/` folder as a nested v4.x install
- Added `tests/test_detect.py`, 17 fixtures pinning every detection lane and all three regressions in this class

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
