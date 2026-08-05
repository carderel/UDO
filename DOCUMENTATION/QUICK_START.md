# Quick Start: Install and First Session

Get UDO running in a few minutes.

## Step 1: Get UDO

There is one source for UDO: `https://github.com/carderel/UDO-v2.0`. Clone it or download the zip. Do not use any other repository; any older guide pointing elsewhere is out of date.

### Starting a brand new project

**Mac / Linux**

```bash
git clone https://github.com/carderel/UDO-v2.0.git my-project
cd my-project
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/carderel/UDO-v2.0.git my-project
Set-Location my-project
```

No `git`? Download the zip instead: `https://github.com/carderel/UDO-v2.0/archive/refs/heads/main.zip`, unzip it, and rename the extracted folder to your project name.

### Adding UDO to a project you already have

Clone to a temporary folder, then copy UDO's root items into your existing project root:

**Mac / Linux**

```bash
git clone https://github.com/carderel/UDO-v2.0.git udo-src
cp -r udo-src/DOCUMENTATION udo-src/TOOLS "udo-src/UDO Framework" "udo-src/UDO Project" "udo-src/User Provided Files" udo-src/README.md udo-src/START_HERE.md udo-src/validate.py udo-src/upgrade.sh udo-src/upgrade.ps1 .
rm -rf udo-src
```

**Windows (PowerShell)**

```powershell
git clone https://github.com/carderel/UDO-v2.0.git udo-src
Copy-Item -Recurse -Force "udo-src\DOCUMENTATION","udo-src\TOOLS","udo-src\UDO Framework","udo-src\UDO Project","udo-src\User Provided Files","udo-src\README.md","udo-src\START_HERE.md","udo-src\validate.py","udo-src\upgrade.sh","udo-src\upgrade.ps1" -Destination .
Remove-Item -Recurse -Force udo-src
```

**Either way, you now have 5 folders at your project root:** `DOCUMENTATION/`, `TOOLS/`, `UDO Framework/`, `UDO Project/`, `User Provided Files/`.

## Step 2: Start Your LLM

Open your AI CLI from inside the project folder (the one that now contains `UDO Framework/` and `UDO Project/`):

```bash
cd /path/to/your/project
```

Then start your LLM's CLI as you normally would. UDO is LLM-agnostic; it does not depend on any particular flag or startup mode. What matters is that your LLM's working directory is the project folder, so it can see and read the UDO files.

## Step 3: Begin Your First Session

Tell your AI:

> Read 'UDO Framework/START_HERE.md' and begin.

The AI will:
1. Read the framework's onboarding document
2. Check `UDO Project/PROJECT_STATE.json` and recent session logs
3. Declare whether it can delegate to subagents in this harness
4. Ask you clarifying questions and give you an orientation report
5. Ask what you want to work on

That's it. You're now in a UDO session.

## Step 4 (optional, recommended for Claude Code): Turn on the Enforcement Hook

If you're using Claude Code, the repo root `.claude/settings.json` already wires up `UDO Project/.udo/udo_hook.py`. It runs automatically once you start Claude Code from the project folder: no extra install step. The hook injects project state at session start, shows a drift status line on each prompt, and blocks session end if `PROJECT_STATE.json` or today's session log is stale.

This is optional. It only works with Claude Code. Any other LLM CLI can still follow the full protocol; use `python3 validate.py` (see below) to check compliance instead.

## After Your First Session

Your project now looks like this:

```
your-project/
├── UDO Framework/          # Protocol. Never edit. Replaced wholesale on upgrade.
│   ├── START_HERE.md       # The AI reads this at session start
│   ├── ORCHESTRATOR.md
│   └── [other framework files]
├── UDO Project/            # Your working context. Upgrades preserve your data here.
│   ├── PROJECT_STATE.json  # Current goal and progress
│   ├── TOPICS.md           # Parallel workstreams
│   ├── .agents/            # Agent personas
│   ├── .project-catalog/   # Session logs and decisions
│   └── [other project files]
├── TOOLS/                  # Installed skills and agents registry
├── DOCUMENTATION/          # You are here
└── User Provided Files/    # External reference material
```

## Next Steps

**For your next session:**
- Start your LLM from the project folder again.
- Tell the AI `Resume` or `Deep resume`.
- The AI loads previous context and continues.

**To check compliance yourself, anytime, with any LLM:**

```bash
python3 validate.py
```

This checks that required files and folders exist, `PROJECT_STATE.json` parses and matches its schema, today's session has a log, and installed agents are in sync. Exit code 0 means pass.

**To understand the structure:**
- Read [FOLDER_GUIDE.md](FOLDER_GUIDE.md) to learn what each folder does.

**To learn more:**
- Read `UDO Framework/ORCHESTRATOR.md` for the full protocol.
- Read `UDO Framework/HARD_STOPS.md` to understand the non-negotiable rules.

## Troubleshooting

**"My AI doesn't see the UDO folders"**
- Make sure you started your LLM's CLI from inside the project folder, not a parent or sibling folder.
- Check that both folders exist: `ls -la "UDO Framework" "UDO Project"` (Mac/Linux) or `dir "UDO Framework"` (Windows).

**"I'm getting permission errors"**
- Make sure you have write access to the project folder.

**"How do I upgrade later?"**
- **Coming from an older version?** If your install does not have `upgrade.py` yet (any UDO v4.x, v2.0, or v2.1, since your install predates it), download the latest script first, then run it. Mac/Linux:
  ```bash
  curl -O https://raw.githubusercontent.com/carderel/UDO-v2.0/main/upgrade.py
  python3 upgrade.py --dry-run
  ```
  Windows (PowerShell):
  ```powershell
  Invoke-WebRequest https://raw.githubusercontent.com/carderel/UDO-v2.0/main/upgrade.py -OutFile upgrade.py
  py -3 upgrade.py --dry-run
  ```
  The script always fetches the newest UDO release from the repo, so downloading the latest `upgrade.py` first is all the updating the updater ever needs.
- If you already have `upgrade.py`, run `python3 upgrade.py --dry-run` from the project root first. It prints a manifest (what will be added, replaced, transformed, or left alone) without changing anything. Review it, then run `python3 upgrade.py` for real. It shows that same manifest, asks for confirmation (skip with `--yes`), then backs up the whole project to `.udo-backup-<timestamp>/` before touching anything, and finishes by running `validate.py` on the result, failing loudly with the backup path if that check does not pass. Use `--source <path-or-url>` to install from a local checkout or zip instead of the default GitHub release. A legacy single-folder `UDO/` install (v4.x) is carried forward automatically; the old folder is renamed to `UDO-v4-LEGACY-DO-NOT-EDIT/` and kept, never deleted. `upgrade.sh` / `upgrade.ps1` are equivalent wrappers around the same script.

**"Should I turn on the enforcement hook?"**
- If you're on Claude Code, yes, it's already wired up and costs nothing extra. On other LLM CLIs, use `python3 validate.py` instead; see Step 4 above.

---

**Ready?** Start your LLM CLI from the project folder and say: Read 'UDO Framework/START_HERE.md' and begin.
