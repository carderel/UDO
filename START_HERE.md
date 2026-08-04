# New AI? Start Here.

This file is a pointer, not the protocol. The actual entry point for every session lives in `UDO Framework/START_HERE.md`. Read that file, not this one, for the full onboarding steps, compliance checklist, and command reference. Keeping the protocol in one place (the Framework copy) means it never drifts out of sync with a duplicate.

## First Session

Start your LLM CLI from this project folder and say:

> Read 'UDO Framework/START_HERE.md' and begin.

This works with any LLM CLI. UDO does not depend on a specific flag or startup mode; what matters is that the AI's working directory is this project folder so it can read the UDO files.

## Framework vs Project

UDO splits into two folder hierarchies so multiple AI assistants can work on the same project without one accidentally modifying the other's rules:

- **`UDO Framework/`**, the immutable reference files (read-only for your project). Replaced wholesale on upgrade.
- **`UDO Project/`**, your working context (where the AI reads and writes). Upgrades never touch it.

```
Your Project Root
├── UDO Framework/                  <- immutable reference, never edit
│   ├── START_HERE.md               (the real entry point, read this)
│   ├── ORCHESTRATOR.md
│   ├── HARD_STOPS.md
│   ├── REASONING_CONTRACT.md
│   └── [all other protocol files]
│
├── UDO Project/                    <- your working context
│   ├── PROJECT_STATE.json
│   ├── TOPICS.md
│   ├── .agents/
│   ├── .project-catalog/           (sessions, decisions, history)
│   ├── .memory/                    (your facts and working notes)
│   ├── .outputs/                   (your deliverables)
│   └── [all your project data]
│
├── TOOLS/                          <- installed skills and agents registry
├── DOCUMENTATION/                  <- onboarding guides for humans
└── User Provided Files/            <- external references and handoffs
```

**Key rule (HS-UDO-014): never modify files in `UDO Framework/`.** It is the reference copy, updated by the upgrade tool. Your customizations go in `UDO Project/HARD_STOPS.md` or `UDO Project/.rules/`.

## Do Not Use Symlinks

`UDO Framework/` must be a real directory, not a symlink.

**Bad:**
```bash
ln -s /actual/location/UDO\ Framework ./UDO\ Framework  # wrong
```

**Why:** Framework immutability (HS-UDO-014) depends on an isolated folder structure per project. Symlinks break that isolation and can cause multiple projects to share Framework modifications, lose the immutability guarantee, or corrupt data across projects.

**Good:**
```bash
cp -r /template/UDO\ Framework ./UDO\ Framework  # correct
```

## Not Sure Where to Start?

- New to UDO entirely? See `DOCUMENTATION/QUICK_START.md` for install and first-session steps.
- Confused about the folders? See `DOCUMENTATION/FOLDER_GUIDE.md`.
- Ready to work? Read `UDO Framework/START_HERE.md` as instructed above.
