#!/usr/bin/env python3
"""Repair a project where upgrade.py installed a placeholder scaffold at the
root instead of upgrading the real UDO install sitting in a subfolder.

The shape this fixes (seen in AI Visibility Reporting and Market Researcher):

    Project Root/
      UDO Framework/      <- scaffold from the bad run, never used
      UDO Project/        <- scaffold, PROJECT_STATE.json still the shipped one
      TOOLS/  DOCUMENTATION/  START_HERE.md  README.md  ...
      .claude/settings.json   <- enforcement hooks pointed at the scaffold
      .udo-backup-YYYYMMDD-HHMMSS/   <- what the root looked like before the run
      UDO/                <- THE REAL PROJECT, un-upgraded, untouched

Nothing was destroyed by the bad run, so this is not data recovery. It is
removing a convincing empty project that sits in front of the real one, and
pointing the enforcement hooks back at the work that matters.

Two rules govern every decision here:

  1. Nothing is deleted. Everything the script removes from the root is moved
     into a quarantine folder you can inspect, and restore from by hand if
     this script got something wrong.
  2. No existing file in the real install is modified or removed. The only
     thing written there is one new decision record, so that a future session
     reading .project-catalog/decisions/ finds out what happened. Verified by
     checksumming the whole tree before and after a rehearsal run against a
     copy of a real affected project: one file added, nothing else changed.

What belongs to the scaffold is decided by evidence, not by a hardcoded list:
the `.udo-backup-*` folder the bad run left behind is a snapshot of the root
from immediately before it. An item present at the root now but absent from
that snapshot was added by the run, and only those are moved. Anything present
in both predates the run and is left strictly alone; if such a file's contents
no longer match the snapshot, the script says so and leaves you to compare,
because it cannot tell an overwrite by the run from your own later edit.

Usage:
    python3 cleanup-misinstall.py [TARGET_DIR] [--real SUBFOLDER] [--apply]

Prints a plan and exits without touching anything unless --apply is given.
TARGET_DIR defaults to the current working directory. Exit 0 on success,
1 on any error or refusal.
"""

import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

PLACEHOLDER_PROJECT_ID = "placeholder-project-id"
V22_STRUCTURAL_DIR_NAMES = {"UDO Framework", "UDO Project"}
EXCLUDE_DIR_NAMES = {".git", ".superpowers", "node_modules"}
BACKUP_PREFIX = ".udo-backup-"
# What a completed migrate/migrate-root run renames the old v4 tree to. Its
# name starts with "UDO", so the name test in describe_install() would flag it
# as an install; it is already-migrated content and never an upgrade target.
LEGACY_DIR_NAME = "UDO-v4-LEGACY-DO-NOT-EDIT"
QUARANTINE_PREFIX = ".udo-misinstall-"
# Everything a fresh install writes at the target root. A leftover is only ever
# quarantined if its name is on this list AND it is absent from the pre-run
# backup: both conditions, so a file the user created after the bad run is
# never mistaken for installer output just because it is new.
INSTALLER_ITEMS = {
    "DOCUMENTATION", "TOOLS", "UDO Framework", "UDO Project", "User Provided Files",
    "validate.py", "cleanup-misinstall.py", ".claude", "README.md", "START_HERE.md",
    "LICENSE", ".gitignore", "upgrade.sh", "upgrade.ps1", "upgrade.py",
}

V4_ROOT_MARKERS = [
    "ORCHESTRATOR.md",
    "HARD_STOPS.md",
    "PROJECT_STATE.json",
    "COMMANDS.md",
    "REASONING_CONTRACT.md",
]


class CleanupError(Exception):
    pass


# ---------------------------------------------------------------------------
# Inspection (pure: reads the filesystem, mutates nothing)
# ---------------------------------------------------------------------------

def read_version(path):
    try:
        return path.read_text(encoding="utf-8").strip() or None
    except (OSError, UnicodeDecodeError):
        return None


def describe_install(path):
    """Return a human description if `path` looks like a UDO install, else None.

    Contents identify it first. Failing that, the folder's NAME does: a folder
    called UDO-anything is somebody's UDO folder even when its layout matches
    none of the known shapes, and this script must not step around it silently.
    Kept deliberately in step with _describe_child() in upgrade.py."""
    if not path.is_dir():
        return None
    fw_version = path / "UDO Framework" / "VERSION"
    if fw_version.is_file():
        return f"v2.x layout, version {read_version(fw_version) or 'unreadable'}"
    if (path / "UDO Framework").is_dir():
        return "v2.x layout, no readable VERSION file"
    if (path / "UDO" / "ORCHESTRATOR.md").is_file():
        return "v4.x install in a UDO/ subfolder"
    markers = [m for m in V4_ROOT_MARKERS if (path / m).is_file()]
    if len(markers) >= 3:
        return f"v4.x install at that folder's root ({len(markers)} markers)"
    if path.name.upper().startswith("UDO"):
        if markers:
            return (f"folder named like a UDO install, {len(markers)} v4 marker(s), "
                    "too few to identify the layout")
        return "folder named like a UDO install, contents unrecognized"
    return None


def find_nested_installs(target):
    found = []
    for child in sorted(target.iterdir()):
        name = child.name
        if not child.is_dir():
            continue
        if name.startswith(".") or name in EXCLUDE_DIR_NAMES:
            continue
        if name in V22_STRUCTURAL_DIR_NAMES:
            continue
        if name == LEGACY_DIR_NAME or name.startswith(LEGACY_DIR_NAME + "-"):
            continue
        desc = describe_install(child)
        if desc:
            found.append((name, desc))
    return found


RECORD_SUBDIRS = ["sessions", "history", "decisions", "handoffs", "checkpoints"]
RECORD_SKIP_NAMES = {"README.md", ".gitkeep"}


def record_files(install):
    """Every session log, transcript, decision, handoff and checkpoint under
    `install`, as (subdir, Path) pairs. Boilerplate the distribution ships is
    skipped so an untouched scaffold reports nothing."""
    catalog = catalog_dir(install)
    if catalog is None:
        return []
    out = []
    for sub in RECORD_SUBDIRS:
        d = catalog / sub
        if not d.is_dir():
            continue
        for entry in sorted(d.iterdir()):
            if entry.name.startswith(".") or entry.name in RECORD_SKIP_NAMES:
                continue
            out.append((sub, entry))
    return out


def catalog_dir(install):
    """`.project-catalog` for either layout, or None."""
    for candidate in (install / "UDO Project" / ".project-catalog",
                      install / ".project-catalog"):
        if candidate.is_dir():
            return candidate
    return None


def classify_install(target):
    """Decide what the install at `target` is, as (kind, detail):

      "used"        a real project. project_id was changed from the shipped
                    placeholder, which only happens when someone sets the
                    project up deliberately. Never touched, no override.
      "placeholder" still carries the state it shipped with, and nothing has
                    been written into it. Safe to move as-is.
      "journaled"   never initialised as a project (project_id is still the
                    shipped one) but records have accumulated in it anyway:
                    somebody has been working in the wrong tree. Those records
                    are real and must be carried across before anything moves.
      "remnant"     no PROJECT_STATE.json at all, e.g. a scaffold someone has
                    already half-removed by hand.

    project_id is the discriminator that matters. A scaffold that a session
    journaled into still has the shipped id, because nothing in the protocol
    rewrites it until the project is actually set up. That is what separates
    "wrong tree, rescue the records" from "this is somebody's project, hands
    off"."""
    state_path = target / "UDO Project" / "PROJECT_STATE.json"
    kind = "placeholder"
    detail = "carries the state it shipped with, nothing written into it"

    if not state_path.is_file():
        kind = "remnant"
        detail = "no UDO Project/PROJECT_STATE.json, so this install is already partial"
    else:
        try:
            obj = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return "used", f"PROJECT_STATE.json could not be parsed ({exc})"
        state = obj.get("project_state", obj) if isinstance(obj, dict) else None
        if not isinstance(state, dict):
            return "used", "PROJECT_STATE.json has an unrecognized shape"
        if state.get("project_id") != PLACEHOLDER_PROJECT_ID:
            return "used", f"project_id is {state.get('project_id')!r}, not the shipped placeholder"

        written = []
        if state.get("goal"):
            written.append("a goal")
        if state.get("todos"):
            written.append(f"{len(state['todos'])} todo(s)")
        if state.get("session_count"):
            written.append(f"session_count {state['session_count']}")
        if state.get("prompt_count"):
            written.append(f"prompt_count {state['prompt_count']}")
        if written:
            kind, detail = "journaled", "state carries " + ", ".join(written)

    records = record_files(target)
    if records:
        counts = {}
        for sub, _path in records:
            counts[sub] = counts.get(sub, 0) + 1
        summary = ", ".join(f"{n} {sub}" for sub, n in sorted(counts.items()))
        if kind == "journaled":
            detail += f"; {summary}"
        else:
            kind, detail = "journaled", summary
    return kind, detail


def newest_backup(target):
    backups = sorted(
        (p for p in target.iterdir() if p.is_dir() and p.name.startswith(BACKUP_PREFIX)),
        key=lambda p: p.name,
    )
    return backups[-1] if backups else None


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

class Plan:
    def __init__(self, target, real, scaffold_version, backup, quarantine):
        self.target = target
        self.real = real
        self.scaffold_version = scaffold_version
        self.backup = backup
        self.quarantine = quarantine
        self.kind = "placeholder"
        self.detail = ""
        self.merge_items = []        # (subdir, source Path, destination Path)
        self.merge_state = None      # (source Path, destination Path)
        self.quarantine_items = []   # (name, why)
        self.hook_action = None      # (description, old_command_path, new_command_path)
        self.quarantine_settings = False
        self.warnings = []


def hook_paths_in(settings_obj):
    """Every command string configured under settings["hooks"], flattened."""
    out = []
    hooks = settings_obj.get("hooks") if isinstance(settings_obj, dict) else None
    if not isinstance(hooks, dict):
        return out
    for entries in hooks.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            for hook in (entry or {}).get("hooks", []) if isinstance(entry, dict) else []:
                cmd = hook.get("command") if isinstance(hook, dict) else None
                if isinstance(cmd, str):
                    out.append(cmd)
    return out


def build_plan(target, real_name, stamp, merge_records=False):
    if not target.is_dir():
        raise CleanupError(f"{target} is not a directory.")

    scaffold_version = read_version(target / "UDO Framework" / "VERSION")

    if (target / "UDO Framework").is_dir():
        kind, detail = classify_install(target)
    else:
        # No scaffold install here, but that does not mean the root is clean.
        # Somebody may have deleted "UDO Framework/" and "UDO Project/" by hand
        # and left the other ten things the installer wrote (DOCUMENTATION/,
        # TOOLS/, START_HERE.md, validate.py ...) sitting at the root. The
        # backup snapshot still identifies them, so the cleanup can still run.
        kind = "debris"
        detail = "no scaffold install left here; identifying leftovers from the backup"
    if kind == "used":
        raise CleanupError(
            f"Refusing to touch {target}: the UDO install here is a real project "
            f"({detail}). This script only clears a scaffold nobody set up deliberately. "
            "If this really is one you want gone, move it by hand so the decision is yours."
        )

    nested = find_nested_installs(target)
    if not nested:
        raise CleanupError(
            f"The install at {target} is an unused placeholder, but there is no other UDO "
            "install in any subfolder, so nothing here is a mis-install. This looks like a "
            "fresh install nobody has started yet. Leaving it alone."
        )

    names = [n for n, _ in nested]
    if real_name is None:
        if len(nested) > 1:
            listing = "\n".join(f"  - {n}/  ({d})" for n, d in nested)
            raise CleanupError(
                f"{len(nested)} subfolders under {target} are UDO installs:\n{listing}\n\n"
                "Refusing to guess which one is the live project. Re-run naming it:\n"
                f'    python3 cleanup-misinstall.py "{target}" --real "{names[0]}"'
            )
        real_name = names[0]
    elif real_name not in names:
        listing = ", ".join(names) or "(none)"
        raise CleanupError(
            f"--real {real_name!r} is not a UDO install directly under {target}. "
            f"Candidates: {listing}"
        )

    real = target / real_name

    if kind == "journaled":
        if not merge_records:
            raise CleanupError(
                f"The install at {target} was never set up as a project (project_id is "
                f"still the shipped placeholder), but work has accumulated in it: "
                f"{detail}.\n\nSomebody has been journaling into the wrong tree. Those "
                "records are real, and clearing the scaffold without them would throw "
                "them away.\n\nRe-run with --merge-records to copy them into "
                f"{real_name}/ first, then clear the scaffold:\n"
                f'    python3 cleanup-misinstall.py "{target}" --real "{real_name}" '
                "--merge-records\n\nAdd --apply once the printed plan looks right."
            )
        if catalog_dir(real) is None:
            raise CleanupError(
                f"--merge-records was asked for, but {real_name}/ has no .project-catalog "
                "to merge into, so there is nowhere for the records to go. Refusing rather "
                "than inventing a folder layout in someone's project."
            )

    backup = newest_backup(target)
    plan = Plan(target, real, scaffold_version, backup, target / f"{QUARANTINE_PREFIX}{stamp}")
    plan.kind, plan.detail = kind, detail
    if kind == "journaled" and merge_records:
        plan_record_merge(plan)

    if backup is None:
        if kind == "debris":
            raise CleanupError(
                f"{target} has no UDO install of its own and no .udo-backup-* folder, so "
                "there is no evidence here of a mis-install and nothing to identify "
                f"leftovers against. {real_name}/ looks like the real project; if you just "
                f'want to upgrade it, run: python3 upgrade.py "{real_name}" --dry-run'
            )
        plan.warnings.append(
            "No .udo-backup-* folder from the bad run was found, so there is no snapshot "
            "of what the root looked like before it. Only the two scaffold folders are "
            "quarantined; every other root file is left exactly where it is, including "
            "any the run may have overwritten. Check them by hand."
        )
        before = None
    else:
        before = {p.name for p in backup.iterdir()}

    for child in sorted(target.iterdir()):
        name = child.name
        if name == real_name or name == plan.quarantine.name:
            continue
        if name.startswith(BACKUP_PREFIX) or name.startswith(QUARANTINE_PREFIX):
            continue
        if name in EXCLUDE_DIR_NAMES or name == ".claude":
            continue

        if before is None:
            # No snapshot to reason from. Only the two folders that are
            # unambiguously the scaffold get moved; everything else stays.
            if name in V22_STRUCTURAL_DIR_NAMES:
                plan.quarantine_items.append((name, "scaffold structure"))
            continue

        if name not in before:
            if name in INSTALLER_ITEMS:
                plan.quarantine_items.append((name, "installed by the run, absent from the backup"))
            else:
                plan.warnings.append(
                    f"{name} appeared after the run but is not something the installer "
                    "writes, so it is yours and is being left alone."
                )
            continue

        # Present before the run, so it is the user's, not the scaffold's.
        # Leave it exactly where it is. The one thing worth saying out loud is
        # when a file's contents have since changed.
        if name in V22_STRUCTURAL_DIR_NAMES:
            plan.quarantine_items.append((name, "scaffold structure"))
            plan.warnings.append(
                f"{name}/ existed before the run as well, so the quarantined copy may mix "
                f"scaffold and original content. Compare it against {backup.name}/{name} "
                "before discarding either."
            )
        elif child.is_file() and not files_match(child, backup / name):
            plan.warnings.append(
                f"{name} predates the run but no longer matches {backup.name}/{name}. "
                "Left untouched: this script cannot tell an overwrite by the run from "
                "an edit you made afterwards. Compare them yourself if it matters."
            )

    plan.hook_action = plan_hook_repair(plan, before)
    return plan


def plan_record_merge(plan):
    """Copy, never move, every record out of the scaffold into the real
    project's catalog. Copying means the originals still go to quarantine, so
    until you delete that folder the records exist in two places rather than
    none. Name collisions are suffixed, never overwritten: a file already in
    the real project always wins its own name."""
    dest_catalog = catalog_dir(plan.real)
    for sub, src in record_files(plan.target):
        dst_dir = dest_catalog / sub
        dst = dst_dir / src.name
        if dst.exists():
            dst = dst_dir / f"{src.stem}-from-root-scaffold{src.suffix}"
        plan.merge_items.append((sub, src, dst))

    # The scaffold's own state is not merged: the schemas and the semantics
    # differ, and a machine-merged goal or todo list is the kind of thing
    # nobody notices is wrong. It is copied in whole, next to the records, for
    # a person to read.
    state = plan.target / "UDO Project" / "PROJECT_STATE.json"
    if state.is_file():
        stamp = datetime.date.today().isoformat()
        plan.merge_state = (state, dest_catalog / f"{stamp}-root-scaffold-PROJECT_STATE.json")


def files_match(a, b):
    """Byte comparison, used only to decide whether to warn. Any error reading
    either side counts as 'cannot confirm they match', which produces the
    warning rather than silence."""
    try:
        if not b.is_file():
            return False
        if a.stat().st_size != b.stat().st_size:
            return False
        return a.read_bytes() == b.read_bytes()
    except OSError:
        return False


def plan_hook_repair(plan, before):
    """Point the enforcement hooks at the real install, if they currently
    resolve into the scaffold and the real install has a hook to run.

    The failure mode this has to avoid: quarantining the scaffold while the
    hooks still name a file inside it leaves every future session start
    invoking a path that no longer exists."""
    settings = plan.target / ".claude" / "settings.json"
    if not settings.is_file():
        return None
    try:
        obj = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        plan.warnings.append(f".claude/settings.json could not be parsed ({exc}); left alone.")
        return None

    commands = hook_paths_in(obj)
    if not commands:
        return None
    scaffold_ref = '$CLAUDE_PROJECT_DIR/UDO Project/.udo/udo_hook.py'
    if not any(scaffold_ref in cmd for cmd in commands):
        return None

    real_hook = plan.real / "UDO Project" / ".udo" / "udo_hook.py"
    if not real_hook.is_file():
        # Nothing to repoint at, and leaving the hooks naming a file that is
        # about to be quarantined would break every session start.
        claude_existed_before = before is not None and ".claude" in before
        if claude_existed_before:
            plan.warnings.append(
                f"The enforcement hooks point into the scaffold, but {real_hook} does not "
                "exist, so there is nothing to repoint them at. .claude/ predates the run, "
                "so it is being left alone rather than moved. AFTER this cleanup the hooks "
                "will name a path that no longer exists and every session start will fail. "
                "Fix it by installing the hook in the real project and re-running, or by "
                "editing .claude/settings.json by hand."
            )
        else:
            plan.quarantine_settings = True
            plan.warnings.append(
                f"The enforcement hooks point into the scaffold, but {real_hook} does not "
                "exist, so there is nothing to repoint them at. .claude/settings.json was "
                "installed by the run, so it is being quarantined too, leaving no hooks "
                "rather than broken ones."
            )
        return None

    new_ref = f'$CLAUDE_PROJECT_DIR/{plan.real.name}/UDO Project/.udo/udo_hook.py'
    return (
        f"repoint {len(commands)} hook command(s) in .claude/settings.json",
        scaffold_ref,
        new_ref,
    )


# ---------------------------------------------------------------------------
# Reporting and application
# ---------------------------------------------------------------------------

def print_plan(plan, applying):
    print()
    print("=" * 72)
    print(f"Target:          {plan.target}")
    if plan.kind == "debris":
        print(f"Scaffold:        none left at the root [{plan.detail}]")
    else:
        print(f"Scaffold:        UDO Framework/ version {plan.scaffold_version or '?'} "
              f"[{plan.kind}: {plan.detail}]")
    print(f"Real project:    {plan.real.name}/  ({describe_install(plan.real)})")
    print(f"Pre-run backup:  {plan.backup.name if plan.backup else '(none found)'}")
    print(f"Quarantine:      {plan.quarantine.name}/")
    print("=" * 72)

    if plan.merge_items or plan.merge_state:
        print(f"\nCOPY INTO {plan.real.name}/ BEFORE CLEARING ({len(plan.merge_items)}"
              f"{' + state' if plan.merge_state else ''}):")
        for sub, src, dst in plan.merge_items:
            renamed = "  (renamed, name already taken)" if dst.name != src.name else ""
            print(f"  {sub}/{src.name}  ->  {dst.parent.name}/{dst.name}{renamed}")
        if plan.merge_state:
            src, dst = plan.merge_state
            print(f"  UDO Project/PROJECT_STATE.json  ->  {dst.parent.name}/{dst.name}"
                  "  (copied whole, for a person to read; not merged)")

    print(f"\nMOVE TO QUARANTINE ({len(plan.quarantine_items)}):")
    for name, why in plan.quarantine_items or []:
        print(f"  {name}    [{why}]")
    if not plan.quarantine_items:
        print("  (none)")

    print("\nHOOKS:")
    if plan.hook_action:
        desc, old, new = plan.hook_action
        print(f"  {desc}")
        print(f"    from: {old}")
        print(f"    to:   {new}")
    elif plan.quarantine_settings:
        print("  .claude/settings.json moved to quarantine (see warnings)")
    else:
        print("  (no change)")

    print(f"\nLEFT ALONE: {plan.real.name}/ (one decision record added, nothing else "
          f"changed), {plan.backup.name + '/, ' if plan.backup else ''}"
          "and every root item not listed above")

    if plan.warnings:
        print("\nWARNINGS:")
        for w in plan.warnings:
            print(f"  ! {w}")

    if not applying:
        print("\nDry run. Nothing has been changed. Re-run with --apply to do the above.")
    print()


def apply_plan(plan):
    # Merge first. If anything here fails, nothing has been moved yet and the
    # scaffold is still intact for a second attempt.
    for _sub, src, dst in plan.merge_items:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
        print(f"  merged       {dst.parent.name}/{dst.name}")
    if plan.merge_state:
        src, dst = plan.merge_state
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        print(f"  merged       {dst.parent.name}/{dst.name}")

    plan.quarantine.mkdir(parents=True, exist_ok=False)
    moved = []

    for name, _why in plan.quarantine_items:
        src = plan.target / name
        dst = plan.quarantine / name
        shutil.move(str(src), str(dst))
        moved.append(name)
        print(f"  quarantined  {name}")

    if plan.quarantine_settings:
        settings = plan.target / ".claude" / "settings.json"
        if settings.is_file():
            (plan.quarantine / ".claude").mkdir(parents=True, exist_ok=True)
            shutil.move(str(settings), str(plan.quarantine / ".claude" / "settings.json"))
            moved.append(".claude/settings.json")
            print("  quarantined  .claude/settings.json  (hooks had nowhere to point)")

    if plan.hook_action:
        _desc, old, new = plan.hook_action
        settings = plan.target / ".claude" / "settings.json"
        raw = settings.read_text(encoding="utf-8")
        backup_path = settings.with_name(
            f"settings.json.bak-misinstall-{plan.quarantine.name[len(QUARANTINE_PREFIX):]}"
        )
        backup_path.write_text(raw, encoding="utf-8")
        patched = raw.replace(old, new)
        json.loads(patched)  # refuse to write anything that is not valid JSON
        settings.write_text(patched, encoding="utf-8")
        print(f"  hooks        repointed at {plan.real.name}/ (old file kept at {backup_path.name})")

    write_record(plan, moved)
    return moved


def write_record(plan, moved):
    """Leave the account of this cleanup inside the real project, which is the
    only place a future session will actually look."""
    for catalog in (
        plan.real / "UDO Project" / ".project-catalog" / "decisions",
        plan.real / ".project-catalog" / "decisions",
    ):
        if catalog.is_dir():
            break
    else:
        plan.warnings.append(
            "No .project-catalog/decisions/ folder found in the real project, so no "
            "record was written there. The quarantine folder is the only account."
        )
        return

    stamp = datetime.date.today().isoformat()
    path = catalog / f"{stamp}-misinstall-cleanup.md"
    lines = [
        f"# Mis-install cleanup: {stamp}",
        "",
        "## What happened",
        "",
        f"An earlier `upgrade.py` run installed a placeholder UDO scaffold "
        f"(version {plan.scaffold_version or '?'}) at `{plan.target.name}/` instead of "
        f"upgrading the real install at `{plan.real.name}/`. The scaffold was never used: "
        "it still carried the shipped placeholder state, with no goal, no todos and no "
        "session logs. Nothing was lost, but the root presented an empty project in front "
        "of the real one, and any session booting from the root read it as brand new.",
        "",
        "## What this cleanup did",
        "",
        f"- Moved {len(plan.quarantine_items)} scaffold item(s) into `{plan.quarantine.name}/`",
        "- Left every root item that predates the run exactly where it was",
    ]
    if plan.merge_items or plan.merge_state:
        lines.append(
            f"- Carried {len(plan.merge_items)} record(s) written into the scaffold across "
            f"into this project's `.project-catalog/` first"
        )
        if plan.merge_state:
            lines.append(
                f"- Copied the scaffold's PROJECT_STATE.json to "
                f"`{plan.merge_state[1].name}` whole. It was NOT merged: read it and "
                "decide what belongs in this project's goal and todos"
            )
    if plan.quarantine_settings:
        lines.append(
            "- Quarantined `.claude/settings.json` as well: its hooks pointed into the "
            "scaffold and the real project has no hook to repoint them at"
        )
    if plan.hook_action:
        lines.append(
            f"- Repointed the `.claude/` enforcement hooks from the scaffold to "
            f"`{plan.real.name}/UDO Project/.udo/udo_hook.py`"
        )
    lines += [
        f"- Left `{plan.real.name}/` completely untouched",
        "",
        "Nothing was deleted. Quarantined items are recoverable by moving them back.",
        "",
        "## Items quarantined",
        "",
    ]
    lines += [f"- `{name}`" for name in moved] or ["- (none)"]
    lines += [
        "",
        "## Still open",
        "",
        f"- Decide whether `{plan.quarantine.name}/` and any `{BACKUP_PREFIX}*` folders can go",
        f"- `{plan.real.name}/` is still on its original version. Upgrade it with:",
        f"  `python3 upgrade.py \"{plan.real.name}\" --dry-run`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  record       {path}")


def build_arg_parser():
    p = argparse.ArgumentParser(
        description="Repair a project where a UDO upgrade installed a placeholder "
                    "scaffold beside the real install instead of upgrading it."
    )
    p.add_argument("target_dir", nargs="?", default=".",
                   help="Project root holding the scaffold (default: current directory)")
    p.add_argument("--real", metavar="SUBFOLDER", default=None,
                   help="Name of the subfolder holding the real install. Required when "
                        "more than one subfolder is a UDO install.")
    p.add_argument("--merge-records", action="store_true",
                   help="When sessions have written into the scaffold, copy those records "
                        "into the real project before clearing it. Required to proceed in "
                        "that case; the script refuses rather than discard them silently.")
    p.add_argument("--apply", action="store_true",
                   help="Actually make the changes. Without this, prints the plan and exits.")
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    target = Path(args.target_dir).expanduser().resolve()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    try:
        plan = build_plan(target, args.real, stamp, merge_records=args.merge_records)
    except CleanupError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        return 1

    print_plan(plan, args.apply)
    if not args.apply:
        return 0

    if (not plan.quarantine_items and not plan.hook_action
            and not plan.quarantine_settings and not plan.merge_items):
        print("Nothing to do.\n")
        return 0

    print("Applying:")
    try:
        apply_plan(plan)
    except OSError as exc:
        print(f"\nERROR while applying: {exc}", file=sys.stderr)
        print(f"Partial state: inspect {plan.quarantine} and move items back as needed.\n",
              file=sys.stderr)
        return 1

    print(f"\nDone. The real project is at {plan.real}")
    print(f"Quarantined copies are in {plan.quarantine}")
    print(f"Next: python3 upgrade.py \"{plan.real.name}\" --dry-run\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
