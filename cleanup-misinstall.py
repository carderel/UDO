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
QUARANTINE_PREFIX = ".udo-misinstall-"
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
    """Return a human description if `path` looks like a UDO install, else None."""
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
        desc = describe_install(child)
        if desc:
            found.append((name, desc))
    return found


def classify_install(target):
    """Decide what the install at `target` is, as (kind, detail):

      "used"        something proves a person has worked in it. Never touched.
      "placeholder" still carries the state it shipped with. Safe to move.
      "remnant"     no PROJECT_STATE.json at all, e.g. a scaffold someone has
                    already half-removed by hand. Nothing there belongs to
                    anyone, and session logs still have to come up empty.

    Only "used" stops the cleanup. The distinction between the other two exists
    so the report can say which one it saw rather than inventing a reason."""
    state_path = target / "UDO Project" / "PROJECT_STATE.json"
    kind = "placeholder"
    detail = "carries the state it shipped with"

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
        if state.get("goal"):
            return "used", "a goal has been written"
        if state.get("todos"):
            return "used", f"{len(state['todos'])} todo(s) recorded"
        if state.get("session_count"):
            return "used", f"session_count is {state['session_count']}"
        if state.get("prompt_count"):
            return "used", f"prompt_count is {state['prompt_count']}"

    sessions = target / "UDO Project" / ".project-catalog" / "sessions"
    if sessions.is_dir():
        logs = [e.name for e in sessions.iterdir() if not e.name.startswith(".")]
        if logs:
            return "used", f"{len(logs)} session log(s) exist ({', '.join(sorted(logs)[:3])})"
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


def build_plan(target, real_name, stamp):
    if not target.is_dir():
        raise CleanupError(f"{target} is not a directory.")

    scaffold_version = read_version(target / "UDO Framework" / "VERSION")
    if not (target / "UDO Framework").is_dir():
        raise CleanupError(
            f"No UDO install at {target} itself (no 'UDO Framework/' folder), so there "
            "is no scaffold here to clean up. If the real install is in a subfolder and "
            "you simply want to upgrade it, point upgrade.py at that subfolder instead."
        )

    kind, detail = classify_install(target)
    if kind == "used":
        raise CleanupError(
            f"Refusing to touch {target}: the UDO install here has been used ({detail}). "
            "This script only removes a scaffold nobody has worked in. If this really "
            "is one you want gone, move it by hand so the decision is yours."
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
    backup = newest_backup(target)
    plan = Plan(target, real, scaffold_version, backup, target / f"{QUARANTINE_PREFIX}{stamp}")
    plan.kind, plan.detail = kind, detail

    if backup is None:
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
            plan.quarantine_items.append((name, "added by the run, absent from the backup"))
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
    print(f"Scaffold:        UDO Framework/ version {plan.scaffold_version or '?'} "
          f"[{plan.kind}: {plan.detail}]")
    print(f"Real project:    {plan.real.name}/  ({describe_install(plan.real)})")
    print(f"Pre-run backup:  {plan.backup.name if plan.backup else '(none found)'}")
    print(f"Quarantine:      {plan.quarantine.name}/")
    print("=" * 72)

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
    p.add_argument("--apply", action="store_true",
                   help="Actually make the changes. Without this, prints the plan and exits.")
    return p


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    target = Path(args.target_dir).expanduser().resolve()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    try:
        plan = build_plan(target, args.real, stamp)
    except CleanupError as exc:
        print(f"\nERROR: {exc}\n", file=sys.stderr)
        return 1

    print_plan(plan, args.apply)
    if not args.apply:
        return 0

    if not plan.quarantine_items and not plan.hook_action and not plan.quarantine_settings:
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
