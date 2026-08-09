#!/usr/bin/env python3
"""UDO upgrade.py - single cross-platform installer/upgrader for the UDO
markdown/JSON protocol framework (v2.2 layout: "UDO Framework/" + "UDO Project/"
as siblings at the target root, plus DOCUMENTATION/, TOOLS/, User Provided
Files/, validate.py, .claude/, README.md, START_HERE.md, LICENSE, .gitignore).

Usage:
    python3 upgrade.py [TARGET_DIR] [--dry-run] [--yes] [--source PATH_OR_URL]
                        [--mode fresh|upgrade|migrate|migrate-root|refresh]

TARGET_DIR defaults to the current working directory. Exit 0 on success or
when there is nothing to do; exit 1 on any error.

Design: the manifest (a list of (action, relpath) tuples, action one of
ADD / REPLACE / TRANSFORM / PRESERVE) is computed once, before any mutation.
--dry-run prints that manifest and exits. A real run prints the same
manifest, asks for confirmation, backs up the target, then applies exactly
that list; nothing is decided differently between print time and apply time.

Python stdlib only. No shell-outs for file operations (shutil/pathlib
throughout); subprocess is used only to invoke the installed validate.py as
its own self-verification step, per contract.
"""

import argparse
import copy
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_SOURCE_URL = "https://github.com/carderel/UDO/archive/refs/heads/main.zip"

# ---------------------------------------------------------------------------
# Constants: lane membership. These lists are the single source of truth for
# both manifest construction (what gets printed) and apply (what gets done).
# ---------------------------------------------------------------------------

# Names excluded from any scan of a --source directory (or a downloaded zip),
# at any depth, so nothing installs a nested backup, VCS state, dependency
# tree, or the source repo's own planning scratch space.
EXCLUDE_DIR_NAMES = {".git", ".superpowers", "node_modules"}
EXCLUDE_DIR_PREFIXES = (".udo-backup",)

# The two directories that ARE a v2.x install at a given level. A scan looking
# for installs one level down must skip them: they are the current level's own
# structure, not a nested project. "UDO Framework" in particular holds
# ORCHESTRATOR.md, HARD_STOPS.md and friends, so a marker count would otherwise
# report a v2.x install's own framework folder as a nested v4.x install.
V22_STRUCTURAL_DIR_NAMES = {"UDO Framework", "UDO Project"}

# project_id as shipped in UDO Project/PROJECT_STATE.json. Still being present
# means nobody has run a session against this install yet.
PLACEHOLDER_PROJECT_ID = "placeholder-project-id"

# Fresh install: everything at the source root that becomes the new
# installation. Order matters only for readability of the printed manifest.
FRESH_TOP_LEVEL = [
    "DOCUMENTATION",
    "TOOLS",
    "UDO Framework",
    "UDO Project",
    "User Provided Files",
    "validate.py",
    "cleanup-misinstall.py",
    ".claude",
    "README.md",
    "START_HERE.md",
    "LICENSE",
    ".gitignore",
    "upgrade.sh",
    "upgrade.ps1",
    "upgrade.py",
]

# v2.x upgrade, framework lane: replaced wholesale, no merge.
FRAMEWORK_LANE_REPLACE = ["UDO Framework"]

# v2.x upgrade, root lane: replaced wholesale from source (ADD if the target
# does not have it yet, REPLACE if it does).
ROOT_LANE_REPLACE = [
    "DOCUMENTATION",
    "validate.py",
    "cleanup-misinstall.py",
    "README.md",
    "START_HERE.md",
    "TOOLS/README.md",
    "TOOLS/CATALOG.md",
    "TOOLS/CATALOG-AGENTS.md",
]

# v2.x upgrade, root lane: added only if absent. Never overwritten, so a
# user's own hook configuration in .claude/settings.json is never clobbered.
ROOT_LANE_ADD_IF_ABSENT = [
    ".claude/settings.json",
]

# v2.x upgrade, root lane: never touched by the upgrader at all.
ROOT_LANE_PRESERVE = [
    "TOOLS/SKILLS_INDEX.md",
    "TOOLS/skills",
]

# v2.x upgrade, project lane: added only if the target does not already have
# the path.
PROJECT_LANE_ADD_IF_ABSENT = [
    "UDO Project/TOPICS.md",
    "UDO Project/.udo",
    "UDO Project/.project-catalog/STATE_SCHEMA.md",
    "UDO Project/.agents/AGENTS_INDEX.md",
    "UDO Project/LESSONS_LEARNED.md",
]

# Structural directories validate.py hard-requires to exist under
# "UDO Project/". A real v2.x checkout (e.g. cloned from git, which does not
# track empty directories) can be missing these even though every file the
# upgrader otherwise cares about is present, which would fail self-verify
# with no path forward. ADD (mkdir + .gitkeep) any that are missing; existing
# content underneath an already-present directory is never touched.
PROJECT_LANE_REQUIRED_STRUCTURAL_DIRS = [
    "UDO Project/.project-catalog/sessions",
    "UDO Project/.project-catalog/history",
    "UDO Project/.project-catalog/decisions",
    "UDO Project/.project-catalog/handoffs",
    "UDO Project/.memory/canonical",
    "UDO Project/.memory/working",
    "UDO Project/.agents",
    "UDO Project/.outputs",
]

# Files inside UDO Project/.agents/ that are registry/reference, not agent
# definitions; their presence does not count as "an agent is installed".
AGENT_REGISTRY_FILES = {"README.md", "AGENTS_INDEX.md"}

# Seed agent personas, installed only when .agents/ has no real agent files.
SEED_AGENT_FILES = [
    "researcher.md",
    "data-auditor.md",
    "strategist.md",
    "technical-writer.md",
]

# v2.x upgrade, project lane: transformed in place (pure dict/text transform,
# existing values preserved, only missing pieces added).
PROJECT_LANE_TRANSFORM = [
    "UDO Project/PROJECT_STATE.json",
    "UDO Project/CAPABILITIES.json",
    "UDO Project/HARD_STOPS.md",
    "UDO Project/PROJECT_META.json",
]

# v2.x upgrade, project lane: left untouched (session records, decisions,
# memory, outputs, existing agents, lessons, non-goals, user uploads).
# NOTE: .memory, .outputs, and .project-catalog/{sessions,history,decisions}
# are NOT listed here even though their contents are preserved just the same;
# their structural existence is covered (ADD if absent, otherwise PRESERVE)
# by PROJECT_LANE_REQUIRED_STRUCTURAL_DIRS above.
PROJECT_LANE_PRESERVE = [
    "UDO Project/.checkpoints",
    "UDO Project/.inputs",
    "UDO Project/.rules",
    "UDO Project/.project-catalog/backups",
    "UDO Project/.project-catalog/checkpoints",
    "UDO Project/NON_GOALS.md",
    "UDO Project/User Uploads",
]

# Subdirectories of UDO Project/.project-catalog whose CONTENT (real session
# records, real history, real decisions, real handoffs) must never be
# installed into a user's project from a --source directory or downloaded
# zip. Only structural dotfiles (.gitkeep) travel; everything else in these
# directories, in the SOURCE, is the source author's own record, not a
# template.
RECORD_CONTENT_DIRS = [
    "UDO Project/.project-catalog/sessions",
    "UDO Project/.project-catalog/history",
    "UDO Project/.project-catalog/decisions",
    "UDO Project/.project-catalog/handoffs",
]

# v4.x migrate: items ported from legacy UDO/<item> into UDO Project/<item>.
# PROJECT_STATE.json is handled separately (schema mapping, not a merge).
V4_PORT_DIRS = [
    ".project-catalog",
    ".memory",
    ".agents",
    ".outputs",
    ".inputs",
    ".checkpoints",
    ".rules",
]
V4_PORT_FILES = [
    "LESSONS_LEARNED.md",
    "NON_GOALS.md",
    "PROJECT_META.json",
]

LEGACY_DIR_NAME = "UDO-v4-LEGACY-DO-NOT-EDIT"

# migrate-root: field finding is that many real v4.x installs are not inside
# a "UDO/" subfolder at all -- their protocol files sit directly at the
# project root, mixed in with the user's own work files. These are the
# marker files detect() counts to decide whether a bare target root is a
# v4.x install rather than an empty (or unrelated) directory. 3+ present is
# treated as confident; 1-2 is ambiguous and must never be auto-resolved.
V4_ROOT_MARKERS = [
    "ORCHESTRATOR.md",
    "HARD_STOPS.md",
    "PROJECT_STATE.json",
    "COMMANDS.md",
    "REASONING_CONTRACT.md",
]

# migrate-root: the full recognized v4.x root file/dir set. Anything at the
# target root that is NOT in one of these two lists is the user's own work
# and is PRESERVEd untouched (listed explicitly in the manifest so the user
# can see it will not be touched). CLAUDE.md is deliberately not recognized:
# it is not a UDO file, and migrate-root must never assume otherwise.
V4_ROOT_RECOGNIZED_FILES = [
    "ORCHESTRATOR.md",
    "HARD_STOPS.md",
    "COMMANDS.md",
    "START_HERE.md",
    "README.md",
    "REASONING_CONTRACT.md",
    "DEVILS_ADVOCATE.md",
    "AUDIENCE_ANTICIPATION.md",
    "EVIDENCE_PROTOCOL.md",
    "TEACH_BACK_PROTOCOL.md",
    "OVERSIGHT_DASHBOARD.md",
    "HANDOFF_PROMPT.md",
    "LESSONS_LEARNED.md",
    "NON_GOALS.md",
    "PROJECT_META.json",
    "PROJECT_STATE.json",
    "CAPABILITIES.json",
    "VERSION",
    ".manifest.json",
]
V4_ROOT_RECOGNIZED_DIRS = [
    ".project-catalog",
    ".memory",
    ".agents",
    ".outputs",
    ".inputs",
    ".rules",
    ".checkpoints",
    ".templates",
    ".tools",
    ".takeover",
    ".bridge",
]

# migrate-root PORT lane: the subset of the recognized set that has a real
# v2.2 home and is copied/merged/transformed into "UDO Project/", using the
# exact same helpers as the UDO/-subdir migrate lane's V4_PORT_DIRS /
# V4_PORT_FILES (plus CAPABILITIES.json, ported here via transform_
# capabilities the same way PROJECT_META.json is ported via transform_
# project_meta). PROJECT_STATE.json is handled separately, same as the
# subdir migrate lane, via map_v4_state_to_v22.
V4_ROOT_PORT_DIRS = [".project-catalog", ".memory", ".agents", ".outputs", ".inputs", ".checkpoints", ".rules"]
V4_ROOT_PORT_FILES = ["LESSONS_LEARNED.md", "NON_GOALS.md", "PROJECT_META.json", "CAPABILITIES.json"]


class UpgradeError(Exception):
    """A user-facing error. Caught in main(); prints message and exits 1."""


# ---------------------------------------------------------------------------
# Source acquisition
# ---------------------------------------------------------------------------

def fetch_source(source_arg):
    """Resolve --source (or the default GitHub zip) to a local directory.

    Returns (source_dir, cleanup_dir) where cleanup_dir is a temp directory
    the caller should shutil.rmtree() when done, or None if source_dir is a
    directory the caller does not own (a --source local path).
    """
    if source_arg is None:
        return _download_and_extract(DEFAULT_SOURCE_URL)
    if source_arg.startswith("http://") or source_arg.startswith("https://"):
        return _download_and_extract(source_arg)
    local = Path(source_arg).expanduser().resolve()
    if not local.is_dir():
        raise UpgradeError(f"--source path does not exist or is not a directory: {local}")
    return local, None


def _guard_source_not_target(target, source):
    """Refuse a --source that resolves to the target itself, or where one of
    target/source contains the other. Copying a tree into itself (or into an
    ancestor/descendant of itself) corrupts the copy mid-walk; this must be
    caught before any mutation, not discovered partway through apply()."""
    source_resolved = Path(source).resolve()
    target_resolved = Path(target).resolve()
    if source_resolved == target_resolved \
            or target_resolved in source_resolved.parents \
            or source_resolved in target_resolved.parents:
        raise UpgradeError(
            f"--source ({source_resolved}) cannot be the target directory "
            f"({target_resolved}), nor may one contain the other."
        )


def _download_and_extract(url):
    tmp_root = Path(tempfile.mkdtemp(prefix="udo-upgrade-"))
    zip_path = tmp_root / "source.zip"
    try:
        with urllib.request.urlopen(url, timeout=60) as response, open(zip_path, "wb") as fh:
            shutil.copyfileobj(response, fh)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise UpgradeError(
            f"Could not download {url}: {exc}. "
            "If you are offline, use --source <local-directory> instead."
        ) from exc

    extract_dir = tmp_root / "extracted"
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_dir)
    except zipfile.BadZipFile as exc:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise UpgradeError(f"Downloaded file from {url} is not a valid zip: {exc}") from exc

    top_entries = [p for p in extract_dir.iterdir()]
    top_dirs = [p for p in top_entries if p.is_dir()]
    if len(top_dirs) == 1 and len(top_entries) == 1:
        source_dir = top_dirs[0]
    else:
        shutil.rmtree(tmp_root, ignore_errors=True)
        raise UpgradeError(
            f"Unexpected zip layout from {url}: expected exactly one top-level folder, "
            f"found {[p.name for p in top_entries]}. Use --source <local-directory> instead."
        )
    return source_dir, tmp_root


def read_version_file(path):
    """Read and strip a VERSION file. Returns "" if the file does not exist."""
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def read_source_version(source_dir):
    version_path = source_dir / "UDO Framework" / "VERSION"
    version = read_version_file(version_path)
    if not version:
        raise UpgradeError(
            f"Source is missing a usable version: {version_path} does not exist or is empty."
        )
    return version


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

class DetectResult:
    def __init__(self, mode, current_version, up_to_date):
        self.mode = mode
        self.current_version = current_version
        self.up_to_date = up_to_date


def find_nested_installs(target):
    """Scan one level below `target` for folders that are themselves UDO
    installs, and return them as a sorted list of (folder name, description).

    Field finding (2026-08-07): a project root can hold a complete UDO install
    in a subfolder ("UDO-v2.0/", "UDO/", "UDO Project Framework Build/") while
    the root itself carries no framework and no v4 root markers. Every check
    in detect() looks only at `target`, so that shape falls straight through
    to the fresh lane, which installs a placeholder scaffold beside the real
    project. Nothing is destroyed (the real install is in a folder the fresh
    manifest never touches), but the next session resumes into an empty
    scaffold and reads the project as brand new. Detection must not guess here.

    Only immediate children are scanned. Dot-directories and the standard
    exclusions are skipped, which is what keeps a .udo-backup-* from an
    earlier run (whose contents legitimately include an install) from
    reporting itself as a nested install forever after."""
    if not target.is_dir():
        return []
    found = []
    for child in sorted(target.iterdir()):
        name = child.name
        if not child.is_dir():
            continue
        if name.startswith(".") or name in EXCLUDE_DIR_NAMES:
            continue
        if name.startswith(EXCLUDE_DIR_PREFIXES):
            continue
        if name in V22_STRUCTURAL_DIR_NAMES:
            continue
        desc = _describe_child(child)
        if desc:
            found.append((name, desc))
    return found


def _describe_child(child):
    """What `child` looks like, or None if it looks like nothing to do with UDO.

    Two ways to qualify. Either the folder's contents identify it (a framework
    folder, a v4 UDO/ subfolder, enough v4 root markers), or its NAME does.
    The name test matters because a partial or hand-edited install may match
    none of the content checks while still obviously being someone's UDO
    folder: "UDO-v2.0" with a half-finished layout, a copy someone renamed. On
    a bare name match the contents get described as unrecognized rather than
    guessed at, and the caller refuses either way. A false positive here costs
    one refusal the user overrides with an explicit --mode; a false negative
    costs them a silent mis-install, which is what this whole guard exists to
    stop."""
    if (child / "UDO Framework" / "VERSION").is_file():
        version = read_version_file(child / "UDO Framework" / "VERSION")
        return f"v2.x install, version {version or 'unreadable'}"
    if (child / "UDO Framework").is_dir():
        return "v2.x install, no readable VERSION file"
    if (child / "UDO" / "ORCHESTRATOR.md").is_file():
        return "v4.x install in a UDO/ subfolder"
    markers = [m for m in V4_ROOT_MARKERS if (child / m).is_file()]
    if len(markers) >= 3:
        return f"v4.x install at that folder's root ({len(markers)} markers)"
    if child.name.upper().startswith("UDO"):
        if markers:
            return (
                f"folder named like a UDO install, {len(markers)} v4 marker(s) present, "
                "too few to identify the layout"
            )
        return "folder named like a UDO install, contents unrecognized"
    return None


def _nested_lines(nested):
    return "\n".join(f"  - {name}/  ({desc})" for name, desc in nested)


def _nested_remedy(target, nested, override_line=None):
    """The two ways forward out of a nested-install standoff. The suggested
    path is written relative to the invoking shell's cwd when the target sits
    under it (the normal case: the user cd'd into the project and ran the
    one-liner), and absolute otherwise, so the command can be pasted as-is.

    override_line names the explicit --mode that overrides this refusal, which
    differs by caller: the fresh fall-through is overridden with --mode fresh,
    the placeholder-over-nested guard with --mode upgrade."""
    if override_line is None:
        override_line = (
            "If you genuinely want a NEW, separate install at this location "
            "alongside the folder(s) above, re-run with an explicit --mode fresh."
        )
    first = target / nested[0][0]
    try:
        suggested = first.resolve().relative_to(Path.cwd().resolve())
    except (ValueError, OSError):
        suggested = first
    return (
        "To upgrade the real install, point this script at it directly:\n"
        + f'    python3 upgrade.py "{suggested}" --dry-run\n'
        + override_line
    )


def _is_untouched_placeholder(target):
    """True when the install at `target` still carries the state it shipped
    with and has never run a session: same project_id as the distribution, no
    goal, no todos, no counted sessions or prompts, no session logs. Any one of
    those being false means somebody has used this install, so it is real work
    and must be upgraded normally."""
    state_path = target / "UDO Project" / "PROJECT_STATE.json"
    if state_path.is_file():
        try:
            obj = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        state = obj.get("project_state", obj) if isinstance(obj, dict) else None
        if not isinstance(state, dict):
            return False
        if state.get("project_id") != PLACEHOLDER_PROJECT_ID:
            return False
        if state.get("goal") or state.get("todos"):
            return False
        if state.get("session_count") or state.get("prompt_count"):
            return False
    # No state file at all is the remnant of a half-removed scaffold. Nothing
    # there proves the install belongs to anyone, so it stays a candidate and
    # the session-log check below still has to clear it.
    sessions = target / "UDO Project" / ".project-catalog" / "sessions"
    if sessions.is_dir():
        for entry in sessions.iterdir():
            if not entry.name.startswith("."):
                return False
    return True


def _guard_placeholder_over_nested(target, version):
    """v2.2.5 stopped the fresh lane from dropping a scaffold beside a real
    install. It cannot help a project where that already happened. The scaffold
    presents a valid UDO Framework/VERSION, so detect() returns on its very
    first check and the nested scan is never reached; the run then upgrades the
    empty placeholder, reports success, and leaves the real project
    un-upgraded one level down. Same silent failure, one release later.

    So the upgrade lane has to ask the question too, but only in the one case
    where the answer is unambiguous: the install here has never been used AND a
    real install sits directly below it. A used install is never touched by
    this guard, and neither is a placeholder with nothing underneath it (that
    is just a fresh install someone has not started yet)."""
    if not _is_untouched_placeholder(target):
        return
    nested = find_nested_installs(target)
    if not nested:
        return
    raise UpgradeError(
        f"The UDO install at {target} (version {version}) has never been used: it still "
        "carries the placeholder state it shipped with, with no goal, no todos and no "
        "session logs. And these subfolder(s) are themselves UDO installs:\n"
        + _nested_lines(nested)
        + "\n\nThis is what a mis-install looks like: an earlier run put a scaffold here "
        "beside the real project instead of upgrading it. Upgrading the scaffold would "
        "report success and change nothing that matters, leaving the real work behind.\n\n"
        + _nested_remedy(
            target,
            nested,
            "If you really do mean to upgrade the empty install at this location, "
            "re-run with an explicit --mode upgrade.",
        )
    )


def detect(target, source_version, forced_mode):
    """Determine which lane to run. Auto-detection only runs when forced_mode
    is None; an explicit --mode always wins and skips the empty/unparseable
    VERSION guard below (the user has taken explicit responsibility)."""
    fw_version_path = target / "UDO Framework" / "VERSION"

    if forced_mode:
        current_version = read_version_file(fw_version_path) or None
        return DetectResult(mode=forced_mode, current_version=current_version, up_to_date=False)

    if fw_version_path.exists():
        if not fw_version_path.is_file():
            raise UpgradeError(f"{fw_version_path} exists but is not a regular file.")
        raw = fw_version_path.read_text(encoding="utf-8")
        version = raw.strip()
        if not version or not re.search(r"[0-9]", version):
            raise UpgradeError(
                f"{fw_version_path} exists but is empty or unparseable (contents: {raw!r}). "
                "Refusing to guess the installed version. Re-run with an explicit "
                "--mode fresh|upgrade|migrate|migrate-root|refresh to proceed."
            )
        _guard_placeholder_over_nested(target, version)
        if version == source_version:
            return DetectResult(mode="upgrade", current_version=version, up_to_date=True)
        return DetectResult(mode="upgrade", current_version=version, up_to_date=False)

    if (target / "UDO Framework").is_dir():
        raise UpgradeError(
            f"{target / 'UDO Framework'} exists but {fw_version_path} does not. "
            "Refusing to guess the installed version. Re-run with an explicit "
            "--mode fresh|upgrade|migrate|migrate-root|refresh to proceed."
        )

    # "UDO Framework" is guaranteed not to be a dir here: the guard above
    # already raised if it were.
    udo_dir = target / "UDO"
    if udo_dir.is_dir() and (udo_dir / "ORCHESTRATOR.md").is_file():
        return DetectResult(mode="migrate", current_version=None, up_to_date=False)

    # Field finding: many real v4.x installs are not in a "UDO/" subfolder
    # at all -- their protocol files sit directly at the project root, mixed
    # in with the user's own work (client files, images, app folders).
    # Neither check above catches that shape, and falling through to
    # "fresh" here would apply the fresh manifest straight over it, silently
    # overwriting root files (README.md, START_HERE.md, .gitignore) that
    # belong to the v4 install. Count recognized v4 root marker files; 3+ is
    # treated as confident enough to auto-select migrate-root, 1-2 is
    # ambiguous (could just be a same-named file of the user's own) and must
    # never be resolved by guessing fresh.
    found_markers = sorted(m for m in V4_ROOT_MARKERS if (target / m).is_file())
    if len(found_markers) >= 3:
        return DetectResult(mode="migrate-root", current_version=None, up_to_date=False)

    # Computed before the ambiguity guard below so that a target which is both
    # partially marked AND has a nested install reports the more actionable
    # fact. It is only decisive at the fresh fall-through: the confident lanes
    # above (upgrade, migrate, migrate-root) keep their existing behaviour.
    nested = find_nested_installs(target)

    if found_markers:
        raise UpgradeError(
            f"Found {len(found_markers)} v4.x root marker file(s) at {target} "
            f"({', '.join(found_markers)}) -- not enough to confidently auto-detect a v4.x "
            "install at the project root, but not zero either. Refusing to guess: applying "
            "a fresh install here could silently overwrite files that belong to a partial "
            "v4.x install. Re-run with an explicit --mode fresh|upgrade|migrate|migrate-root"
            "|refresh to proceed."
            + (
                "\n\nNote: this folder also contains what looks like a complete UDO install "
                "one level down:\n"
                + _nested_lines(nested)
                + "\n\n"
                + _nested_remedy(target, nested)
                if nested
                else ""
            )
        )

    if nested:
        raise UpgradeError(
            f"No UDO install found at {target} itself, but "
            f"{'a subfolder is already one' if len(nested) == 1 else 'these subfolders already are'}"
            ":\n"
            + _nested_lines(nested)
            + "\n\nRefusing to guess. Installing fresh here would put an empty placeholder "
            "project beside your real one. Nothing would be destroyed, but the real work "
            "would stay un-upgraded and the next session would resume into the empty "
            "scaffold and read the project as brand new.\n\n"
            + _nested_remedy(target, nested)
        )

    return DetectResult(mode="fresh", current_version=None, up_to_date=False)


# ---------------------------------------------------------------------------
# Manifest construction (pure: reads the filesystem, mutates nothing)
# ---------------------------------------------------------------------------

def build_manifest(lane_mode, target, source):
    if lane_mode == "fresh":
        return _manifest_fresh(target, source)
    if lane_mode == "upgrade":
        return _manifest_upgrade(target)
    if lane_mode == "migrate":
        return _manifest_migrate(target)
    if lane_mode == "migrate-root":
        return _manifest_migrate_root(target, source)
    raise UpgradeError(f"unknown lane mode: {lane_mode}")


def _exists_at(target, relpath):
    return (target / relpath).exists()


def _claude_manifest_entries(target):
    """Manifest entries for ".claude" wherever a FRESH_TOP_LEVEL loop would
    otherwise blanket-REPLACE it. A real .claude/ can hold a user's
    settings.local.json (permission allowlist), MCP config, and installed
    plugins -- none of that may ever be replaced or deleted. If present, the
    whole directory is PRESERVEd untouched, and only settings.json is added
    inside it if that one file happens to be absent (mirrors
    ROOT_LANE_ADD_IF_ABSENT, the existing v2.x upgrade lane's pattern for the
    same file). If .claude does not exist at all, it is a plain new-install
    ADD of the whole tree from source, same as any other fresh top-level
    item."""
    claude_dir = target / ".claude"
    if not claude_dir.is_dir():
        return [("ADD", ".claude")]
    settings = claude_dir / "settings.json"
    return [
        ("PRESERVE", ".claude"),
        ("PRESERVE" if settings.exists() else "ADD", ".claude/settings.json"),
    ]


def _gitignore_manifest_entries(target, source):
    """Manifest entries for ".gitignore" wherever a FRESH_TOP_LEVEL loop
    would otherwise blanket-REPLACE it. A real target root is often the
    user's own app repo, whose .gitignore already protects its own repo
    hygiene (node_modules/, dist/, .env, ...) -- replacing it outright would
    silently break that. Same class of fix as _claude_manifest_entries.

    If .gitignore does not exist at all, it is a plain new-install ADD of
    the template as-is. If it exists, the template's entries are merged in
    (see merge_gitignore) instead of the file being replaced: TRANSFORM is
    reported unless the merge is a no-op (marker already present from an
    earlier run, or every template entry already covered by the user's own
    lines), in which case PRESERVE is reported -- matching exactly what
    apply will do, per this file's print-time/apply-time consistency
    contract.
    """
    gitignore_path = target / ".gitignore"
    if not gitignore_path.is_file():
        return [("ADD", ".gitignore")]
    source_gitignore = source / ".gitignore"
    existing_text = gitignore_path.read_text(encoding="utf-8")
    source_text = source_gitignore.read_text(encoding="utf-8") if source_gitignore.is_file() else ""
    merged = merge_gitignore(existing_text, source_text)
    action = "TRANSFORM" if merged != existing_text else "PRESERVE"
    return [(action, ".gitignore")]


def _manifest_fresh(target, source):
    manifest = []
    for item in FRESH_TOP_LEVEL:
        if item == ".claude":
            manifest.extend(_claude_manifest_entries(target))
            continue
        if item == ".gitignore":
            manifest.extend(_gitignore_manifest_entries(target, source))
            continue
        action = "REPLACE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))
    return manifest


def _manifest_upgrade(target):
    manifest = []

    for item in FRAMEWORK_LANE_REPLACE:
        action = "REPLACE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    for item in ROOT_LANE_REPLACE:
        action = "REPLACE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    for item in ROOT_LANE_ADD_IF_ABSENT:
        action = "PRESERVE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    for item in ROOT_LANE_PRESERVE:
        action = "PRESERVE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    for item in PROJECT_LANE_ADD_IF_ABSENT:
        action = "PRESERVE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    for item in PROJECT_LANE_REQUIRED_STRUCTURAL_DIRS:
        action = "PRESERVE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    agents_dir = target / "UDO Project" / ".agents"
    if _has_agent_definitions(agents_dir):
        manifest.append(("PRESERVE", "UDO Project/.agents (existing agent definitions)"))
    else:
        for name in SEED_AGENT_FILES:
            manifest.append(("ADD", f"UDO Project/.agents/{name}"))

    for item in PROJECT_LANE_TRANSFORM:
        manifest.append(("TRANSFORM", item))

    for item in PROJECT_LANE_PRESERVE:
        manifest.append(("PRESERVE", item))

    return manifest


def _has_agent_definitions(agents_dir):
    if not agents_dir.is_dir():
        return False
    for p in agents_dir.iterdir():
        if p.is_file() and p.name not in AGENT_REGISTRY_FILES:
            return True
    return False


def _manifest_migrate(target):
    manifest = []

    # Fresh-install the non-project pieces (framework, docs, tools, root files).
    for item in FRESH_TOP_LEVEL:
        if item == "UDO Project":
            continue
        action = "REPLACE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))

    # Bootstrap the v2.2 project template, then port real v4 data into it.
    manifest.append(("ADD", "UDO Project"))

    for item in V4_PORT_DIRS:
        manifest.append(("TRANSFORM", f"UDO/{item} -> UDO Project/{item}"))
    for item in V4_PORT_FILES:
        manifest.append(("TRANSFORM", f"UDO/{item} -> UDO Project/{item}"))
    manifest.append(("TRANSFORM", "UDO/PROJECT_STATE.json -> UDO Project/PROJECT_STATE.json"))
    manifest.append(("ADD", "UDO Project/.project-catalog/decisions/<date>-v4-to-v22-migration-record.md"))
    manifest.append(("TRANSFORM", f"UDO -> {LEGACY_DIR_NAME}"))

    return manifest


def _v4_root_recognized_present(target):
    """Recognized v4 root marker names (files, then dirs) actually present
    at target, in V4_ROOT_RECOGNIZED_FILES + V4_ROOT_RECOGNIZED_DIRS order."""
    present = []
    for name in V4_ROOT_RECOGNIZED_FILES:
        if (target / name).is_file():
            present.append(name)
    for name in V4_ROOT_RECOGNIZED_DIRS:
        if (target / name).is_dir():
            present.append(name)
    return present


def _manifest_migrate_root(target, source):
    """A v4.x install whose protocol files sit directly at the target root,
    mixed with the user's own files, rather than inside a "UDO/" subfolder.

    Four lanes: ADD (the v2.2 structure, "UDO Project/" bootstrapped then
    ported into below), PORT (recognized v4 root data merged/transformed
    into "UDO Project/"), LEGACY (every recognized v4 root item, moved
    wholesale into the legacy folder -- including the items PORT already
    read, since PORT copies rather than moves), and PRESERVE (every root
    entry that is not recognized as v4 and not part of the v2.2 structure:
    the user's own work, named explicitly so they can see it will not be
    touched).

    A path never appears under both REPLACE and LEGACY: README.md and
    START_HERE.md are both a FRESH_TOP_LEVEL item AND a recognized v4 root
    file. By the time the new v2.2 copy is placed, the old one has already
    been moved into the legacy folder (see apply order in
    _apply_migrate_root), so that placement is an ADD into a now-empty
    slot, not an in-place REPLACE of a file that is still sitting there --
    it is listed under ADD (once) and LEGACY (once), never REPLACE.
    """
    manifest = []
    recognized = set(V4_ROOT_RECOGNIZED_FILES) | set(V4_ROOT_RECOGNIZED_DIRS)

    for item in FRESH_TOP_LEVEL:
        if item == "UDO Project":
            continue
        if item == ".claude":
            manifest.extend(_claude_manifest_entries(target))
            continue
        if item == ".gitignore":
            manifest.extend(_gitignore_manifest_entries(target, source))
            continue
        if item in recognized:
            manifest.append(("ADD", item))
            continue
        action = "REPLACE" if _exists_at(target, item) else "ADD"
        manifest.append((action, item))
    manifest.append(("ADD", "UDO Project"))

    for item in V4_ROOT_PORT_DIRS + V4_ROOT_PORT_FILES:
        if _exists_at(target, item):
            manifest.append(("PORT", f"{item} -> UDO Project/{item}"))
    if _exists_at(target, "PROJECT_STATE.json"):
        manifest.append(("PORT", "PROJECT_STATE.json -> UDO Project/PROJECT_STATE.json"))
    manifest.append(("ADD", "UDO Project/.project-catalog/decisions/<date>-v4-to-v22-migration-record.md"))

    for item in _v4_root_recognized_present(target):
        manifest.append(("LEGACY", f"{item} -> {LEGACY_DIR_NAME}/{item}"))

    fresh_names = set(FRESH_TOP_LEVEL)
    if target.is_dir():
        for entry in sorted(target.iterdir(), key=lambda p: p.name):
            name = entry.name
            if name in recognized or name in fresh_names:
                continue
            if name in EXCLUDE_DIR_NAMES or name.startswith(EXCLUDE_DIR_PREFIXES):
                continue
            manifest.append(("PRESERVE", name))

    return manifest


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _is_backup_excluded_name(name):
    """Shares EXCLUDE_DIR_NAMES (.git, .superpowers, node_modules) with the
    source-tree scan, plus the backup-specific .udo-backup* prefix. A real
    v4-at-root target is often an app repo; without this, backing it up
    before every upgrade/migrate copies node_modules (and anything else the
    source scan already knows to skip) right along with it."""
    return name in EXCLUDE_DIR_NAMES or name.startswith(EXCLUDE_DIR_PREFIXES)


def _backup_ignore(dir_path, names):
    return {n for n in names if _is_backup_excluded_name(n)}


def _backup_shorten(path_str, limit=120):
    """Truncate a path for display; only appends '...' when it actually
    had to cut something, so short paths are not shown as truncated."""
    s = str(path_str)
    if len(s) > limit:
        return s[:limit] + "..."
    return s


def _backup_offending_paths(exc):
    """Pull up to 3 offending SOURCE paths out of a copytree failure.

    shutil.Error carries exc.args[0] as a list of (src, dst, why) tuples
    (raised once, after copytree collects every per-entry failure). A bare
    OSError (e.g. the top-level destination mkdir failing outright) carries
    the failing path on .filename instead."""
    paths = []
    if isinstance(exc, shutil.Error):
        for item in exc.args[0] if exc.args else []:
            if isinstance(item, (tuple, list)) and item:
                paths.append(str(item[0]))
    elif isinstance(exc, OSError):
        if exc.filename:
            paths.append(str(exc.filename))
        elif exc.filename2:
            paths.append(str(exc.filename2))
    return paths[:3]


def _backup_path_has_repeated_component(path_str, min_repeats=3):
    """True if some directory component (e.g. '.checkpoints') repeats 3+
    times in the path, the signature of a snapshot that recursively
    copied itself into itself."""
    counts = {}
    for part in Path(str(path_str)).parts:
        counts[part] = counts.get(part, 0) + 1
        if counts[part] >= min_repeats:
            return True
    return False


def _backup_failure_error(exc):
    """Build the clean UpgradeError to raise when backup() cannot copy the
    project, instead of letting a raw shutil/OSError traceback surface."""
    offending = _backup_offending_paths(exc)
    lines = ["Backup failed, no changes were made to your project."]
    if offending:
        lines.append("Offending path(s):")
        for p in offending:
            lines.append(f"  - {_backup_shorten(p)}")
    else:
        lines.append(f"Underlying error: {exc}")
    if any(_backup_path_has_repeated_component(p) for p in offending):
        lines.append(
            "This looks like recursively nested checkpoint or backup copies "
            "inside the install (snapshots that included their own snapshot "
            "folder). Delete the nested copies inside .checkpoints/<name>/ "
            "(keep only the first level) and re-run."
        )
    return UpgradeError("\n".join(lines))


def backup(target):
    """Copy target into target/.udo-backup-<timestamp>/, excluding
    EXCLUDE_DIR_NAMES (.git, .superpowers, node_modules -- the same set the
    source-tree scan uses) plus .udo-backup* (kills nested-backup recursion
    since the new backup directory is never part of the pre-computed source
    listing).

    If that name is already taken (e.g. a second upgrade run within the same
    second), append -2, -3, ... until an unused name is found, rather than
    failing the upgrade outright.

    Returns (backup_dir, excluded_count): excluded_count is the number of
    top-level and nested entries skipped for being an excluded name, so the
    caller can report it (a real target may be an app repo with a large
    node_modules/ that should never balloon the backup)."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base_name = f".udo-backup-{timestamp}"
    backup_dir = target / base_name
    suffix = 1
    while backup_dir.exists():
        suffix += 1
        backup_dir = target / f"{base_name}-{suffix}"

    try:
        backup_dir.mkdir(parents=True)
    except OSError as exc:
        raise _backup_failure_error(exc) from exc

    excluded_count = 0

    def _counting_ignore(dir_path, names):
        skipped = _backup_ignore(dir_path, names)
        nonlocal excluded_count
        excluded_count += len(skipped)
        return skipped

    top_level_names = sorted(p.name for p in target.iterdir() if p.name != backup_dir.name)
    for name in top_level_names:
        if _is_backup_excluded_name(name):
            excluded_count += 1
            continue
        src = target / name
        dst = backup_dir / name
        try:
            if src.is_dir():
                shutil.copytree(src, dst, ignore=_counting_ignore)
            else:
                shutil.copy2(src, dst)
        except (shutil.Error, OSError) as exc:
            shutil.rmtree(backup_dir, ignore_errors=True)
            raise _backup_failure_error(exc) from exc
    return backup_dir, excluded_count


# ---------------------------------------------------------------------------
# Source-tree copying (fresh/upgrade/migrate ADD and REPLACE actions)
# ---------------------------------------------------------------------------

def _build_source_ignore(source_root):
    record_dirs_abs = set()
    for rel in RECORD_CONTENT_DIRS:
        p = source_root / rel
        try:
            record_dirs_abs.add(p.resolve())
        except OSError:
            record_dirs_abs.add(p)

    def ignore(dir_path, names):
        ignored = {n for n in names if n in EXCLUDE_DIR_NAMES or n.startswith(EXCLUDE_DIR_PREFIXES)}
        try:
            resolved_dir = Path(dir_path).resolve()
        except OSError:
            resolved_dir = Path(dir_path)
        if resolved_dir in record_dirs_abs:
            ignored |= {n for n in names if n != ".gitkeep"}
        return ignored

    return ignore


def copy_tree_from_source(src, dst, source_root):
    """Copy a directory from the source tree into the target, excluding VCS
    state, planning scratch, nested backups, node_modules, and (inside
    UDO Project/.project-catalog) real session/history/decision/handoff
    content that belongs to the source author, not the template."""
    shutil.copytree(src, dst, dirs_exist_ok=True, ignore=_build_source_ignore(source_root))


def copy_path_from_source(relpath, target, source):
    src = source / relpath
    dst = target / relpath
    if not src.exists():
        raise UpgradeError(f"source is missing expected path: {relpath}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        copy_tree_from_source(src, dst, source)
    else:
        shutil.copy2(src, dst)


def ensure_structural_dir(path):
    """Create a required-but-possibly-missing structural directory (one of
    PROJECT_LANE_REQUIRED_STRUCTURAL_DIRS, which validate.py hard-requires to
    exist). Idempotent and never touches existing content: a .gitkeep is
    only written if the directory ends up empty, so a directory that already
    has real files (e.g. .agents/ after seed agents were added) is left
    exactly as those other steps left it."""
    path.mkdir(parents=True, exist_ok=True)
    if not any(path.iterdir()):
        (path / ".gitkeep").write_text("", encoding="utf-8")


def replace_path_from_source(relpath, target, source):
    dst = target / relpath
    if dst.exists():
        if dst.is_dir():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    copy_path_from_source(relpath, target, source)


# ---------------------------------------------------------------------------
# Pure transform functions (dict/text in, dict/text out; no I/O)
# ---------------------------------------------------------------------------

def _collect_todo_ids(todos):
    """Return the set of T-NNN ids already used by structured todo dicts."""
    ids = set()
    for t in todos:
        if isinstance(t, dict) and isinstance(t.get("id"), str):
            ids.add(t["id"])
    return ids


def _next_todo_id(used_ids):
    """Return the lowest unused T-NNN id, marking it used in used_ids."""
    n = 1
    while True:
        candidate = f"T-{n:03d}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate
        n += 1


def _map_v4_todo_item(item, existing_ids, status_default):
    """Map one item from a v4 `todos` or `in_progress` list into a
    structured v2.2 todo dict, tolerating malformed dict items instead of
    letting validate.py's structured-todo check fail the whole migration.

    - str -> structured todo (auto id).
    - dict with a non-empty string `task` -> structured todo (auto id if
      missing/non-string).
    - dict with no usable `task` but a non-empty string `description`,
      `title`, or `name` -> that value becomes `task` (auto id if needed);
      the substitution is reported via the returned note so the caller can
      record it in the migration record.
    - anything else (dict with no usable text field at all, or a
      non-str/non-dict item) -> not mapped; the raw item is returned so the
      caller can route it to the migration record's unmapped section
      instead of into todos.

    Returns (todo_dict_or_None, substitution_note_or_None, unmapped_raw_or_None).
    Exactly one of (todo_dict_or_None, unmapped_raw_or_None) is non-None.
    """
    if isinstance(item, str):
        return (
            {"id": _next_todo_id(existing_ids), "task": item, "status": status_default, "priority": "normal"},
            None,
            None,
        )
    if isinstance(item, dict):
        task = item.get("task")
        if isinstance(task, str) and task.strip():
            out = dict(item)
            out.setdefault("status", status_default)
            if not isinstance(out.get("id"), str):
                out["id"] = _next_todo_id(existing_ids)
            return out, None, None
        for fallback_key in ("description", "title", "name"):
            value = item.get(fallback_key)
            if isinstance(value, str) and value.strip():
                out = dict(item)
                out["task"] = value
                out.setdefault("status", status_default)
                if not isinstance(out.get("id"), str):
                    out["id"] = _next_todo_id(existing_ids)
                note = {"used_key": fallback_key, "task": value, "original_item": item}
                return out, note, None
        return None, None, item
    return None, None, item


def transform_state(state_obj, source_state_obj):
    """v2.x in-place upgrade transform of a parsed PROJECT_STATE.json.

    Ensures the project_state wrapper exists, adds any missing v2.2 fields
    using the source template's defaults, and converts plain-string todos to
    structured {id, task, status, priority} dicts. Every existing value is
    preserved. Pure: returns a new dict, never mutates its arguments.
    """
    if isinstance(state_obj, dict) and isinstance(state_obj.get("project_state"), dict):
        inner = copy.deepcopy(state_obj["project_state"])
    else:
        inner = copy.deepcopy(state_obj) if isinstance(state_obj, dict) else {}

    source_inner = {}
    if isinstance(source_state_obj, dict) and isinstance(source_state_obj.get("project_state"), dict):
        source_inner = source_state_obj["project_state"]

    defaults = {
        "goal": source_inner.get("goal", ""),
        # not in the brief's field list, but required by validate.py's schema
        # check; without it every pre-2.2 install would fail self-verify.
        "current_phase": source_inner.get("current_phase", "setup"),
        "scope_locked": False,
        "todos": [],
        "deferred_debt": [],
        "auto_checkpoint": source_inner.get(
            "auto_checkpoint",
            {"enabled": True, "trigger": "phase-boundary", "last_auto_checkpoint": None},
        ),
        "circuit_breaker": source_inner.get(
            "circuit_breaker", {"triggered": False, "reason": None, "timestamp": None}
        ),
        "context_health": source_inner.get(
            "context_health", {"estimated_usage": "low", "last_archive": None}
        ),
        "prompt_counter": source_inner.get(
            "prompt_counter", {"count_since_last_state_update": 0, "last_state_update_session": "none"}
        ),
    }
    for key, default in defaults.items():
        if key not in inner:
            inner[key] = copy.deepcopy(default)

    existing_ids = _collect_todo_ids(inner.get("todos", []))
    normalized_todos = []
    for todo in inner.get("todos", []):
        if isinstance(todo, str):
            normalized_todos.append(
                {"id": _next_todo_id(existing_ids), "task": todo, "status": "pending", "priority": "normal"}
            )
        else:
            normalized_todos.append(todo)
    inner["todos"] = normalized_todos

    return {"project_state": inner}


def transform_capabilities(caps_obj, source_caps_obj):
    """Add a missing delegation block and any missing tools_available keys,
    using the source template's defaults. Everything else is preserved.
    Pure: returns a new dict.
    """
    data = copy.deepcopy(caps_obj) if isinstance(caps_obj, dict) else {}
    source = source_caps_obj if isinstance(source_caps_obj, dict) else {}

    if "delegation" not in data:
        data["delegation"] = copy.deepcopy(
            source.get("delegation", {"available": None, "mechanism": "", "detected_by": "", "detected_date": ""})
        )

    existing_tools = data.get("tools_available")
    if not isinstance(existing_tools, dict):
        existing_tools = {}
    for key, default in source.get("tools_available", {}).items():
        if key not in existing_tools:
            existing_tools[key] = default
    data["tools_available"] = existing_tools

    return data


def transform_project_meta(meta_obj):
    """Add protocol_strict: true if missing, preserve everything else. Pure."""
    data = copy.deepcopy(meta_obj) if isinstance(meta_obj, dict) else {}
    metadata = data.get("project_metadata")
    if isinstance(metadata, dict):
        config = metadata.get("configuration")
        if isinstance(config, dict):
            config.setdefault("protocol_strict", True)
        else:
            metadata["configuration"] = {"protocol_strict": True}
    else:
        data.setdefault("protocol_strict", True)
    return data


def append_hard_stops_project_blocks(existing_text, source_text):
    """Append the source template's PROJECT_HS_001/PROJECT_HS_002 blocks to
    existing_text, only if PROJECT_HS_001 is not already present. Pure
    string transform.
    """
    if "PROJECT_HS_001" in existing_text:
        return existing_text

    start_marker = "### PROJECT_HS_001"
    end_marker = "## Relationship to Framework"
    start = source_text.find(start_marker)
    if start == -1:
        return existing_text
    end = source_text.find(end_marker, start)
    block = source_text[start:end].rstrip() if end != -1 else source_text[start:].rstrip()

    base = existing_text.rstrip("\n")
    return base + "\n\n" + block + "\n"


GITIGNORE_MARKER_START = "# --- UDO runtime (added by upgrade.py) ---"
GITIGNORE_MARKER_END = "# --- end UDO runtime ---"


def _gitignore_template_entries(source_text):
    """Non-blank, non-comment lines of a .gitignore, in order -- the
    UDO-specific ignore entries a merge must ensure are present. Pure."""
    entries = []
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def merge_gitignore(existing_text, source_text):
    """Merge the UDO template's .gitignore entries into a user's existing
    .gitignore, without ever removing or reordering the user's own lines
    (same intent as append_hard_stops_project_blocks, applied to a file a
    real app repo owns for its own hygiene -- node_modules, dist, .env --
    which a blanket REPLACE would otherwise clobber).

    Idempotent: once the marker block has been appended, existing_text is
    returned unchanged on every later call, regardless of what source_text
    contains, so a repeat upgrade never reopens or duplicates the block. On
    a first merge, only template entries not already present verbatim as a
    line in existing_text are appended, wrapped once in marker lines; if
    every template entry is already covered, existing_text is returned
    unchanged rather than adding an empty marker block. Pure.
    """
    if GITIGNORE_MARKER_START in existing_text:
        return existing_text

    existing_lines = {line.strip() for line in existing_text.splitlines()}
    missing = [e for e in _gitignore_template_entries(source_text) if e not in existing_lines]
    if not missing:
        return existing_text

    block = "\n".join([GITIGNORE_MARKER_START] + missing + [GITIGNORE_MARKER_END])
    base = existing_text.rstrip("\n")
    if base:
        return base + "\n\n" + block + "\n"
    return block + "\n"


def map_v4_state_to_v22(v4_obj, source_state_obj):
    """Map a v4 flat PROJECT_STATE.json to the v2.2 nested schema.

    Fields that exist in both schemas, or have a natural v2.2 home, carry
    their live v4 values forward instead of reverting to template defaults:
    `circuit_breaker` and `context_health` carry verbatim when present;
    `auto_checkpoint` carries when present with `trigger` normalized to
    "phase-boundary" (any v4 count-based subfield with no v2.2 shape, e.g.
    `todos_since_checkpoint`, is moved into the returned unmapped dict
    instead; an explicit `trigger` value other than "phase-boundary" is
    also recorded there rather than silently discarded); v4 `in_progress[]`
    items become structured todos with status "in_progress", placed before
    the pending todos and sharing the same T-NNN id sequence (no duplicate
    ids, even when some todos already carry an explicit id).

    Dict items in `in_progress[]` or `todos[]` are never let through to
    validate.py's structured-todo check unless they have a usable `task`:
    a dict with a non-empty string `task` maps as-is (auto id if missing);
    a dict with no `task` but a `description`, `title`, or `name` string
    uses that as `task` (recorded as a substitution in unmapped_dict); a
    dict with none of those, or any other non-str/non-dict item, is never
    put into todos at all and instead is recorded, verbatim, in
    unmapped_dict, so a single malformed item can never abort the whole
    migration.

    Returns (v22_state_dict, unmapped_dict). unmapped_dict carries the v4
    `completed` list, any field with no v2.2 equivalent (e.g. blockers,
    agent_registry, bridge, current_session, prompt_counter internals),
    any todo/in_progress key substitutions, and any unmappable todo/
    in_progress items, so nothing is silently dropped; the caller writes
    unmapped_dict into the migration decision record, where it lives only
    in that record. Pure: returns new dicts, never mutates its arguments.
    """
    v4 = copy.deepcopy(v4_obj) if isinstance(v4_obj, dict) else {}
    known_v4_keys = {
        "goal", "phase", "todos", "in_progress", "checkpoints", "completed",
        "circuit_breaker", "context_health", "auto_checkpoint",
    }

    existing_ids = _collect_todo_ids(v4.get("todos", [])) | _collect_todo_ids(v4.get("in_progress", []))

    todos = []
    todo_substitutions = []
    unmapped_in_progress_items = []
    unmapped_todos_items = []
    for t in v4.get("in_progress", []):
        mapped, note, raw = _map_v4_todo_item(t, existing_ids, "in_progress")
        if mapped is not None:
            todos.append(mapped)
            if note is not None:
                todo_substitutions.append({"list": "in_progress", **note})
        else:
            unmapped_in_progress_items.append(raw)
    for t in v4.get("todos", []):
        mapped, note, raw = _map_v4_todo_item(t, existing_ids, "pending")
        if mapped is not None:
            todos.append(mapped)
            if note is not None:
                todo_substitutions.append({"list": "todos", **note})
        else:
            unmapped_todos_items.append(raw)

    checkpoints = []
    for cp in v4.get("checkpoints", []):
        if isinstance(cp, dict):
            checkpoints.append(
                {
                    "name": cp.get("name", cp.get("id", "checkpoint")),
                    "timestamp": cp.get("timestamp", ""),
                    "trigger": "manual",
                    "description": cp.get("description", ""),
                }
            )

    source_inner = {}
    if isinstance(source_state_obj, dict) and isinstance(source_state_obj.get("project_state"), dict):
        source_inner = source_state_obj["project_state"]

    inner = copy.deepcopy(source_inner)
    inner["goal"] = v4.get("goal", "")
    inner["current_phase"] = v4.get("phase", "setup")
    inner["todos"] = todos
    inner["checkpoints"] = checkpoints
    inner["deferred_debt"] = inner.get("deferred_debt", [])
    inner["scope_locked"] = False

    unmapped = {"completed": v4.get("completed", [])}
    if todo_substitutions:
        unmapped["todo_key_substitutions"] = todo_substitutions
    if unmapped_in_progress_items:
        unmapped["in_progress_unmapped_items"] = unmapped_in_progress_items
    if unmapped_todos_items:
        unmapped["todos_unmapped_items"] = unmapped_todos_items

    if "circuit_breaker" in v4:
        inner["circuit_breaker"] = copy.deepcopy(v4["circuit_breaker"])
    else:
        inner["circuit_breaker"] = copy.deepcopy(
            source_inner.get("circuit_breaker", {"triggered": False, "reason": None, "timestamp": None})
        )

    if "context_health" in v4:
        inner["context_health"] = copy.deepcopy(v4["context_health"])
    else:
        inner["context_health"] = copy.deepcopy(
            source_inner.get("context_health", {"estimated_usage": "low", "last_archive": None})
        )

    if isinstance(v4.get("auto_checkpoint"), dict):
        ac = v4["auto_checkpoint"]
        inner["auto_checkpoint"] = {
            "enabled": ac.get("enabled", True),
            "trigger": "phase-boundary",
            "last_auto_checkpoint": ac.get("last_auto_checkpoint"),
        }
        leftover = {k: v for k, v in ac.items() if k not in {"enabled", "last_auto_checkpoint", "trigger"}}
        original_trigger = ac.get("trigger")
        if isinstance(original_trigger, str) and original_trigger != "phase-boundary":
            leftover = dict(leftover)
            leftover["trigger"] = original_trigger
        if leftover:
            unmapped["auto_checkpoint"] = leftover
    else:
        inner["auto_checkpoint"] = copy.deepcopy(
            source_inner.get(
                "auto_checkpoint",
                {"enabled": True, "trigger": "phase-boundary", "last_auto_checkpoint": None},
            )
        )

    for key, value in v4.items():
        if key not in known_v4_keys:
            unmapped[key] = value

    return {"project_state": inner}, unmapped


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def load_json(path):
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UpgradeError(f"{path}: invalid JSON ({exc})") from exc
    except UnicodeDecodeError as exc:
        raise UpgradeError(f"{path}: could not read as UTF-8 ({exc})") from exc


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------

def apply(manifest, lane_mode, target, source):
    if lane_mode == "fresh":
        _apply_fresh(manifest, target, source)
    elif lane_mode == "upgrade":
        _apply_upgrade(manifest, target, source)
    elif lane_mode == "migrate":
        _apply_migrate(manifest, target, source)
    elif lane_mode == "migrate-root":
        _apply_migrate_root(manifest, target, source)
    else:
        raise UpgradeError(f"unknown lane mode: {lane_mode}")


def _apply_fresh(manifest, target, source):
    for action, relpath in manifest:
        if action == "PRESERVE":
            continue  # .claude or .gitignore, when merge is already a no-op
        if action == "ADD":
            copy_path_from_source(relpath, target, source)
        elif action == "REPLACE":
            replace_path_from_source(relpath, target, source)
        elif action == "TRANSFORM":
            _apply_transform(relpath, target, source)
        else:
            raise UpgradeError(f"unexpected action in fresh manifest: {action} {relpath}")


def _apply_upgrade(manifest, target, source):
    for action, relpath in manifest:
        if relpath == "UDO Project/.agents (existing agent definitions)":
            continue  # PRESERVE, informational entry only
        if relpath in PROJECT_LANE_REQUIRED_STRUCTURAL_DIRS:
            if action == "ADD":
                ensure_structural_dir(target / relpath)
            continue  # PRESERVE: existing content under it is untouched
        if action == "PRESERVE":
            continue
        if action == "ADD":
            copy_path_from_source(relpath, target, source)
        elif action == "REPLACE":
            replace_path_from_source(relpath, target, source)
        elif action == "TRANSFORM":
            _apply_transform(relpath, target, source)
        else:
            raise UpgradeError(f"unexpected action in upgrade manifest: {action} {relpath}")


def _apply_transform(relpath, target, source):
    dst = target / relpath
    src = source / relpath
    name = dst.name

    if name == "PROJECT_STATE.json":
        existing = load_json(dst)
        source_state = load_json(src)
        write_json(dst, transform_state(existing, source_state))
    elif name == "CAPABILITIES.json":
        existing = load_json(dst)
        source_caps = load_json(src)
        write_json(dst, transform_capabilities(existing, source_caps))
    elif name == "PROJECT_META.json":
        existing = load_json(dst)
        write_json(dst, transform_project_meta(existing))
    elif name == "HARD_STOPS.md":
        existing_text = dst.read_text(encoding="utf-8") if dst.is_file() else ""
        source_text = src.read_text(encoding="utf-8") if src.is_file() else ""
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(append_hard_stops_project_blocks(existing_text, source_text), encoding="utf-8")
    elif name == ".gitignore":
        existing_text = dst.read_text(encoding="utf-8") if dst.is_file() else ""
        source_text = src.read_text(encoding="utf-8") if src.is_file() else ""
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(merge_gitignore(existing_text, source_text), encoding="utf-8")
    else:
        raise UpgradeError(f"no transform defined for: {relpath}")


def _apply_migrate(manifest, target, source):
    legacy_root = target / "UDO"
    unmapped_by_lane = {}
    legacy_dir_name = LEGACY_DIR_NAME

    for action, relpath in manifest:
        if relpath == "UDO Project" and action == "ADD":
            copy_path_from_source("UDO Project", target, source)
            continue
        if relpath.startswith("UDO Project/.project-catalog/decisions/") and action == "ADD":
            continue  # written after the port below, once we know what's unmapped
        if relpath == f"UDO -> {LEGACY_DIR_NAME}" and action == "TRANSFORM":
            name = _finalize_legacy_rename(legacy_root, target)
            if name:
                legacy_dir_name = name
            continue
        if " -> " in relpath and action in ("REPLACE", "ADD"):
            continue  # handled by the TRANSFORM branch below (shares the merge logic)
        if action == "ADD":
            copy_path_from_source(relpath, target, source)
        elif action == "REPLACE":
            replace_path_from_source(relpath, target, source)
        elif action == "TRANSFORM":
            unmapped = _apply_migrate_transform(relpath, target, source, legacy_root)
            if unmapped:
                unmapped_by_lane[relpath] = unmapped

    return unmapped_by_lane, legacy_dir_name


def _apply_migrate_transform(relpath, target, source, legacy_root):
    # relpath is "<item> -> UDO Project/<item>", optionally prefixed with
    # "UDO/" (the subdir migrate lane); migrate-root passes the bare item
    # name since its v4 data sits directly at legacy_root (the target root
    # itself) rather than under a "UDO/" subfolder.
    item = relpath.split(" -> ", 1)[0].replace("UDO/", "", 1)

    if item == "PROJECT_STATE.json":
        v4_state_path = legacy_root / "PROJECT_STATE.json"
        v4_state = load_json(v4_state_path)
        source_state = load_json(source / "UDO Project" / "PROJECT_STATE.json")
        v22_state, unmapped = map_v4_state_to_v22(v4_state, source_state)
        write_json(target / "UDO Project" / "PROJECT_STATE.json", v22_state)
        return unmapped

    legacy_src = legacy_root / item
    project_dst = target / "UDO Project" / item
    if not legacy_src.exists():
        return None

    if item == "PROJECT_META.json":
        data = load_json(legacy_src)
        write_json(project_dst, transform_project_meta(data))
        return None

    if item == "CAPABILITIES.json":
        data = load_json(legacy_src)
        source_caps = load_json(source / "UDO Project" / "CAPABILITIES.json")
        write_json(project_dst, transform_capabilities(data, source_caps))
        return None

    if legacy_src.is_dir():
        _merge_directory(legacy_src, project_dst)
        if item == ".agents":
            missing = _agents_without_frontmatter(project_dst)
            return {"agents_missing_frontmatter": missing} if missing else None
        return None

    project_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy_src, project_dst)
    return None


def _agents_without_frontmatter(agents_dir):
    """Ported v4 agents are carried over as-is (brief: "as-is"). This flags
    any .md file that does not open with YAML frontmatter, so the migration
    record can note it rather than silently assuming compliance."""
    missing = []
    for p in sorted(agents_dir.glob("*.md")):
        if p.name in AGENT_REGISTRY_FILES:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not text.lstrip().startswith("---"):
            missing.append(p.name)
    return missing


def _merge_directory(legacy_src, project_dst):
    """Copy every entry from a legacy v4 directory into its v2.2 destination,
    overwriting template placeholders with the real ported data. Never
    deletes anything already at project_dst that legacy_src does not have."""
    project_dst.mkdir(parents=True, exist_ok=True)
    for entry in legacy_src.iterdir():
        dst_entry = project_dst / entry.name
        if entry.is_dir():
            if dst_entry.exists() and not dst_entry.is_dir():
                dst_entry.unlink()
            shutil.copytree(entry, dst_entry, dirs_exist_ok=True)
        else:
            if dst_entry.exists() and dst_entry.is_dir():
                shutil.rmtree(dst_entry)
            shutil.copy2(entry, dst_entry)


def _finalize_legacy_rename(legacy_root, target):
    """Rename UDO/ (the legacy v4.x install) out of the way.

    If UDO-v4-LEGACY-DO-NOT-EDIT/ already exists at the target (a retry
    after an earlier migrate that renamed the legacy folder but did not
    complete, e.g. the backup was restored and --mode migrate re-run), fall
    back to a timestamp-suffixed name (same format as backup dirs) instead
    of letting Path.rename() raise straight into main() as a raw traceback.
    Any other OSError from the rename itself is wrapped in UpgradeError so it
    surfaces through the normal "UPGRADE FAILED ... Backup is at: ..." path.

    Returns the final legacy directory name (just the name, not a full
    path), or None if there was no UDO/ to rename.
    """
    if not legacy_root.exists():
        return None

    legacy_dest = target / LEGACY_DIR_NAME
    suffixed = False
    if legacy_dest.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        legacy_dest = target / f"{LEGACY_DIR_NAME}-{timestamp}"
        suffixed = True

    try:
        legacy_root.rename(legacy_dest)
    except OSError as exc:
        raise UpgradeError(
            f"could not move the legacy installation from {legacy_root} to "
            f"{legacy_dest}: {exc}"
        ) from exc

    extra_note = ""
    if suffixed:
        extra_note = (
            f"\nRenamed to \"{legacy_dest.name}/\" (timestamp-suffixed) because "
            f"\"{LEGACY_DIR_NAME}/\" already existed at this target, most likely "
            "from a previous migrate attempt.\n"
        )

    notice = legacy_dest / "_LEGACY_NOTICE.md"
    notice.write_text(
        "# Legacy UDO v4.x installation\n\n"
        "This directory is the original UDO v4.x installation, preserved as-is\n"
        "after migration to UDO v2.2. It is kept for reference and audit only.\n\n"
        "Do not edit files in this directory. The active project now lives in\n"
        "\"UDO Project/\" at the repository root; the migration record is at\n"
        "\"UDO Project/.project-catalog/decisions/\".\n\n"
        "This directory is never deleted by upgrade.py.\n"
        f"{extra_note}",
        encoding="utf-8",
    )
    return legacy_dest.name


def _apply_migrate_root(manifest, target, source, progress=None):
    """Apply the migrate-root lane: a v4.x install whose protocol files sit
    directly at the project root, mixed with the user's own work, rather
    than inside a "UDO/" subfolder. Mirrors _apply_migrate's structure and
    reuses the same transform helpers, in this order:

    1. Bootstrap "UDO Project/" from source, then PORT the recognized v4
       root data into it -- while those v4 files are still at their
       original root location, so they can be read.
    2. LEGACY: move every recognized v4 root item (including the ones PORT
       just read, whose copies now live in "UDO Project/") into a fresh
       legacy folder.
    3. ADD the rest of the v2.2 root structure. By now every recognized v4
       item that could collide with a fresh top-level name (README.md,
       START_HERE.md, ...) has already been moved into the legacy folder,
       so this step never overwrites a v4 file unseen.

    `progress`, if given, is a {"lane": ..., "phase": ...} dict mutated in
    place so main()'s failure handlers can give lane/phase-accurate restore
    guidance instead of a generic message -- see _failure_guidance(). It is
    set to "legacy_done" right after step 2 completes, the point past which
    the original v4.x files are no longer at their original location.

    Returns (unmapped_by_lane, legacy_dir_name), same contract as
    _apply_migrate.
    """
    unmapped_by_lane = {}

    for action, relpath in manifest:
        if action == "ADD" and relpath == "UDO Project":
            copy_path_from_source("UDO Project", target, source)
            break

    for action, relpath in manifest:
        if action != "PORT":
            continue
        unmapped = _apply_migrate_transform(relpath, target, source, target)
        if unmapped:
            unmapped_by_lane[relpath] = unmapped

    legacy_items = [relpath for action, relpath in manifest if action == "LEGACY"]
    legacy_dir_name = _finalize_legacy_root_rename(legacy_items, target)
    if legacy_dir_name is None:
        legacy_dir_name = LEGACY_DIR_NAME
    if progress is not None:
        progress["phase"] = "legacy_done"

    for action, relpath in manifest:
        if relpath == "UDO Project" or action in ("PORT", "LEGACY", "PRESERVE"):
            continue
        if relpath.startswith("UDO Project/.project-catalog/decisions/"):
            continue  # written after apply(), once we know what's unmapped
        if action == "ADD":
            copy_path_from_source(relpath, target, source)
        elif action == "REPLACE":
            replace_path_from_source(relpath, target, source)
        elif action == "TRANSFORM":
            _apply_transform(relpath, target, source)
        else:
            raise UpgradeError(f"unexpected action in migrate-root manifest: {action} {relpath}")

    return unmapped_by_lane, legacy_dir_name


def _finalize_legacy_root_rename(legacy_items, target):
    """Move every recognized v4 root item into a fresh legacy folder at the
    target root (root-layout counterpart to _finalize_legacy_rename, which
    renames a single "UDO/" subfolder in one shot; migrate-root instead has
    many individual root-level items to relocate).

    legacy_items is the manifest's LEGACY-action relpath list, each shaped
    "<item> -> UDO-v4-LEGACY-DO-NOT-EDIT/<item>". Uses the same suffix-on-
    collision naming as backup()/_finalize_legacy_rename if the legacy
    folder name is already taken (a retry after an earlier migrate-root
    attempt), instead of raising a raw traceback. Writes _LEGACY_NOTICE.md.

    Returns the final legacy directory name (just the name, not a full
    path), or None if there was nothing to move.
    """
    if not legacy_items:
        return None

    legacy_dest = target / LEGACY_DIR_NAME
    suffixed = False
    if legacy_dest.exists():
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        legacy_dest = target / f"{LEGACY_DIR_NAME}-{timestamp}"
        suffixed = True

    legacy_dest.mkdir(parents=True)

    for relpath in legacy_items:
        item = relpath.split(" -> ", 1)[0]
        src = target / item
        if not src.exists():
            continue
        dst = legacy_dest / item
        try:
            src.rename(dst)
        except OSError as exc:
            raise UpgradeError(
                f"could not move the legacy v4.x file/folder from {src} to {dst}: {exc}"
            ) from exc

    extra_note = ""
    if suffixed:
        extra_note = (
            f"\nRenamed to \"{legacy_dest.name}/\" (timestamp-suffixed) because "
            f"\"{LEGACY_DIR_NAME}/\" already existed at this target, most likely "
            "from a previous migrate-root attempt.\n"
        )

    notice = legacy_dest / "_LEGACY_NOTICE.md"
    notice.write_text(
        "# Legacy UDO v4.x installation (root layout)\n\n"
        "This directory holds the original UDO v4.x protocol files and data.\n"
        "They used to sit directly at your project root, mixed in with your\n"
        "own work files, before migration to UDO v2.2. They are kept here\n"
        "for reference and audit only.\n\n"
        "Do not edit files in this directory. The active project now lives in\n"
        "\"UDO Project/\" at the repository root; the migration record is at\n"
        "\"UDO Project/.project-catalog/decisions/\". Every root file or folder\n"
        "that was not part of the recognized UDO v4.x set was left exactly\n"
        "where it was, at the project root -- nothing else was moved.\n\n"
        "This directory is never deleted by upgrade.py.\n"
        f"{extra_note}",
        encoding="utf-8",
    )
    return legacy_dest.name


# ---------------------------------------------------------------------------
# Reporting / decision records
# ---------------------------------------------------------------------------

def print_manifest(manifest):
    buckets = {"ADD": [], "REPLACE": [], "TRANSFORM": [], "PRESERVE": []}
    for action, relpath in manifest:
        buckets.setdefault(action, []).append(relpath)

    # PORT and LEGACY (migrate-root only) are printed as their own sections,
    # positioned between REPLACE and TRANSFORM, but only when the manifest
    # actually contains them -- so fresh/upgrade/migrate output is unchanged.
    order = ["ADD", "REPLACE"]
    if "PORT" in buckets:
        order.append("PORT")
    if "LEGACY" in buckets:
        order.append("LEGACY")
    order += ["TRANSFORM", "PRESERVE"]

    for label in order:
        items = buckets.get(label, [])
        print(f"{label} ({len(items)}):")
        if not items:
            print("  (none)")
        for relpath in items:
            print(f"  {relpath}")
        print("")


def confirm():
    try:
        response = input("Proceed? [y/N] ").strip().lower()
    except EOFError:
        return False
    return response in ("y", "yes")


def write_decision_record(target, mode, source_version, manifest, backup_dir):
    counts = {"ADD": 0, "REPLACE": 0, "TRANSFORM": 0, "PRESERVE": 0}
    for action, _ in manifest:
        counts[action] = counts.get(action, 0) + 1

    date = datetime.date.today().isoformat()
    safe_version = re.sub(r"[^A-Za-z0-9._-]", "-", source_version)
    decisions_dir = target / "UDO Project" / ".project-catalog" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    record_path = decisions_dir / f"{date}-upgrade-to-{safe_version}.md"

    lines = [
        f"# Upgrade to {source_version}",
        "",
        f"- Date: {date}",
        f"- Mode: {mode}",
        f"- Source version: {source_version}",
        f"- Backup: {backup_dir if backup_dir else '(none, no mutation needed)'}",
        "",
        "## Manifest counts",
        "",
    ]
    for label in ("ADD", "REPLACE", "TRANSFORM", "PRESERVE"):
        lines.append(f"- {label}: {counts.get(label, 0)}")
    lines.append("")
    record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record_path


def write_migration_record(target, unmapped_by_lane, legacy_dir_name=LEGACY_DIR_NAME, mode="migrate"):
    date = datetime.date.today().isoformat()
    decisions_dir = target / "UDO Project" / ".project-catalog" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    record_path = decisions_dir / f"{date}-v4-to-v22-migration-record.md"

    lines = [
        "# v4.x to v2.2 migration record",
        "",
        f"- Date: {date}",
        f"- Mode: {mode}",
        f"- Legacy installation preserved at: {legacy_dir_name}/",
    ]
    if legacy_dir_name != LEGACY_DIR_NAME:
        lines.append(
            f"- Note: renamed to a timestamp-suffixed name because \"{LEGACY_DIR_NAME}/\" "
            "already existed at this target (most likely a retry after an earlier "
            f"{mode} attempt)."
        )
    lines += [
        "",
        "## Unmapped / unmappable fields",
        "",
        "The following v4 fields have no v2.2 equivalent and live only in this",
        "record. They are not silently dropped, but they are not carried into",
        "the live PROJECT_STATE.json either. Fields with a natural v2.2 home",
        "(circuit_breaker, context_health, auto_checkpoint, in_progress) are",
        "carried into the live state directly and do not appear below.",
        "",
    ]
    any_unmapped = False
    for lane, unmapped in unmapped_by_lane.items():
        if not unmapped:
            continue
        any_unmapped = True
        lines.append(f"### {lane}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(unmapped, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")
    if not any_unmapped:
        lines.append("(none)")
        lines.append("")
    record_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record_path


def run_validate(target):
    validate_path = target / "validate.py"
    if not validate_path.is_file():
        raise UpgradeError(f"self-verify failed: {validate_path} does not exist after install")
    result = subprocess.run(
        [sys.executable, str(validate_path), "UDO Project"],
        cwd=str(target),
        capture_output=True,
        text=True,
    )
    return result.returncode, (result.stdout or "") + (result.stderr or "")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog="upgrade.py",
        description="Install or upgrade a UDO project in place.",
    )
    parser.add_argument("target_dir", nargs="?", default=".", help="Target directory (default: current directory)")
    parser.add_argument("--dry-run", action="store_true", help="Print the manifest and exit without changing anything")
    parser.add_argument("--yes", action="store_true", help="Do not prompt for confirmation")
    parser.add_argument("--source", default=None, help="Local directory or URL to a zip, used instead of the default GitHub release")
    parser.add_argument("--mode", choices=["fresh", "upgrade", "migrate", "migrate-root", "refresh"], default=None, help="Force a mode instead of auto-detecting")
    return parser


def _failure_guidance(progress, backup_dir):
    """Restore guidance for a failure, tailored to how far apply actually
    got (tracked via `progress`, a simple {"lane": ..., "phase": ...} dict
    mutated in place by the apply function) rather than one generic message
    for every lane and phase.

    migrate-root is the case that needs this: once its LEGACY step has run,
    the original v4.x root files no longer exist at their original
    location -- they were moved (Path.rename), not copied -- so "just
    restore the backup" on its own does not tell the user where things
    actually are or what "restore" means here. Every other lane/phase keeps
    the previous generic message.
    """
    if backup_dir is None:
        return None
    if progress.get("lane") == "migrate-root" and progress.get("phase") == "legacy_done":
        return (
            f"Your original v4.x files have already been moved into {LEGACY_DIR_NAME}/ "
            "at the target root; they are no longer at their original location.\n"
            f"A full copy of the project exactly as it was before this run is at: {backup_dir}\n"
            "To restore: delete the partially-created v2.2 items (\"UDO Project\", "
            "\"UDO Framework\", DOCUMENTATION, TOOLS, README.md, START_HERE.md, "
            f"{LEGACY_DIR_NAME}/, and any other new top-level item from this run), then "
            "copy everything back from the backup above."
        )
    return (
        f"The target may be in a partially-applied state. Backup is at: {backup_dir}\n"
        "Restore it if needed before retrying."
    )


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    target = Path(args.target_dir).expanduser().resolve()

    cleanup_dir = None
    backup_dir = None
    progress = {"lane": None, "phase": None}
    try:
        source, cleanup_dir = fetch_source(args.source)
        _guard_source_not_target(target, source)
        source_version = read_source_version(source)

        detection = detect(target, source_version, args.mode)

        if detection.up_to_date:
            print(f"Already up to date: UDO Framework/VERSION is {detection.current_version}.")
            return 0

        mode = detection.mode
        lane_mode = "upgrade" if mode == "refresh" else mode
        progress["lane"] = lane_mode

        manifest = build_manifest(lane_mode, target, source)

        if detection.current_version:
            print(f"Detected mode: {mode} (current version: {detection.current_version}, source version: {source_version})")
        else:
            print(f"Detected mode: {mode} (source version: {source_version})")
        print("")
        print_manifest(manifest)

        if not manifest:
            print("Nothing to do.")
            return 0

        if args.dry_run:
            print("Dry run: no changes made.")
            return 0

        if not args.yes:
            if not confirm():
                print("Cancelled.")
                return 0

        # Only touch the filesystem once we are committed to applying: a
        # --dry-run (or a cancelled prompt) against a nonexistent nested
        # TARGET_DIR must leave it absent, per the "no changes" contract.
        target.mkdir(parents=True, exist_ok=True)

        backup_dir, excluded_count = backup(target)
        print(f"Backup created at: {backup_dir} ({excluded_count} entries excluded: node_modules, .git, etc.)")

        legacy_dir_name = LEGACY_DIR_NAME
        if lane_mode == "migrate":
            unmapped_by_lane, legacy_dir_name = _apply_migrate(manifest, target, source)
        elif lane_mode == "migrate-root":
            unmapped_by_lane, legacy_dir_name = _apply_migrate_root(manifest, target, source, progress)
        else:
            apply(manifest, lane_mode, target, source)
            unmapped_by_lane = {}

        returncode, output = run_validate(target)
        if returncode != 0:
            print("")
            print("UPGRADE FAILED: self-verification (validate.py) reported errors.")
            print(output)
            guidance = _failure_guidance(progress, backup_dir)
            if guidance:
                print(guidance)
            return 1

        if mode in ("migrate", "migrate-root"):
            migration_record = write_migration_record(target, unmapped_by_lane, legacy_dir_name, mode=mode)
            print(f"Migration record written: {migration_record}")
            if legacy_dir_name != LEGACY_DIR_NAME:
                print(
                    f"Note: legacy v4.x install was renamed to \"{legacy_dir_name}/\" "
                    f"(timestamp-suffixed) because \"{LEGACY_DIR_NAME}/\" already existed "
                    "at this target."
                )

        record_path = write_decision_record(target, mode, source_version, manifest, backup_dir)
        print("")
        print(f"Upgrade to {source_version} complete (mode: {mode}).")
        print(f"Decision record: {record_path}")
        print(f"Backup: {backup_dir}")
        return 0

    except UpgradeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        guidance = _failure_guidance(progress, backup_dir)
        if guidance:
            print(guidance, file=sys.stderr)
        return 1
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
