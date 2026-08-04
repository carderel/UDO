#!/usr/bin/env python3
"""UDO upgrade.py - single cross-platform installer/upgrader for the UDO
markdown/JSON protocol framework (v2.2 layout: "UDO Framework/" + "UDO Project/"
as siblings at the target root, plus DOCUMENTATION/, TOOLS/, validate.py,
.claude/, README.md, START_HERE.md, LICENSE, .gitignore).

Usage:
    python3 upgrade.py [TARGET_DIR] [--dry-run] [--yes] [--source PATH_OR_URL]
                        [--mode fresh|upgrade|migrate|refresh]

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

DEFAULT_SOURCE_URL = "https://github.com/carderel/UDO-v2.0/archive/refs/heads/main.zip"

# ---------------------------------------------------------------------------
# Constants: lane membership. These lists are the single source of truth for
# both manifest construction (what gets printed) and apply (what gets done).
# ---------------------------------------------------------------------------

# Names excluded from any scan of a --source directory (or a downloaded zip),
# at any depth, so nothing installs a nested backup, VCS state, dependency
# tree, or the source repo's own planning scratch space.
EXCLUDE_DIR_NAMES = {".git", ".superpowers", "node_modules"}
EXCLUDE_DIR_PREFIXES = (".udo-backup",)

# Fresh install: everything at the source root that becomes the new
# installation. Order matters only for readability of the printed manifest.
FRESH_TOP_LEVEL = [
    "DOCUMENTATION",
    "TOOLS",
    "UDO Framework",
    "UDO Project",
    "validate.py",
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
    "UDO Project/LESSONS_LEARNED.md",
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
                "--mode fresh|upgrade|migrate|refresh to proceed."
            )
        if version == source_version:
            return DetectResult(mode="upgrade", current_version=version, up_to_date=True)
        return DetectResult(mode="upgrade", current_version=version, up_to_date=False)

    udo_dir = target / "UDO"
    if not (target / "UDO Framework").is_dir() and udo_dir.is_dir() and (udo_dir / "ORCHESTRATOR.md").is_file():
        return DetectResult(mode="migrate", current_version=None, up_to_date=False)

    return DetectResult(mode="fresh", current_version=None, up_to_date=False)


# ---------------------------------------------------------------------------
# Manifest construction (pure: reads the filesystem, mutates nothing)
# ---------------------------------------------------------------------------

def build_manifest(lane_mode, target, source):
    if lane_mode == "fresh":
        return _manifest_fresh(target)
    if lane_mode == "upgrade":
        return _manifest_upgrade(target)
    if lane_mode == "migrate":
        return _manifest_migrate(target)
    raise UpgradeError(f"unknown lane mode: {lane_mode}")


def _exists_at(target, relpath):
    return (target / relpath).exists()


def _manifest_fresh(target):
    manifest = []
    for item in FRESH_TOP_LEVEL:
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
    manifest.append(("ADD", ".project-catalog/decisions/<date>-v4-to-v22-migration-record.md"))
    manifest.append(("TRANSFORM", f"UDO -> {LEGACY_DIR_NAME}"))

    return manifest


# ---------------------------------------------------------------------------
# Backup
# ---------------------------------------------------------------------------

def _is_backup_excluded_name(name):
    return name in {".git", ".superpowers"} or name.startswith(EXCLUDE_DIR_PREFIXES)


def _backup_ignore(dir_path, names):
    return {n for n in names if _is_backup_excluded_name(n)}


def backup(target):
    """Copy target into target/.udo-backup-<timestamp>/, excluding
    .udo-backup*, .git, .superpowers (kills nested-backup recursion since the
    new backup directory is never part of the pre-computed source listing)."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = target / f".udo-backup-{timestamp}"
    if backup_dir.exists():
        raise UpgradeError(f"backup destination already exists: {backup_dir}")
    backup_dir.mkdir(parents=True)

    top_level_names = sorted(p.name for p in target.iterdir() if p.name != backup_dir.name)
    for name in top_level_names:
        if _is_backup_excluded_name(name):
            continue
        src = target / name
        dst = backup_dir / name
        if src.is_dir():
            shutil.copytree(src, dst, ignore=_backup_ignore)
        else:
            shutil.copy2(src, dst)
    return backup_dir


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

    normalized_todos = []
    for i, todo in enumerate(inner.get("todos", []), start=1):
        if isinstance(todo, str):
            normalized_todos.append({"id": f"T-{i:03d}", "task": todo, "status": "pending", "priority": "normal"})
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


def map_v4_state_to_v22(v4_obj, source_state_obj):
    """Map a v4 flat PROJECT_STATE.json to the v2.2 nested schema.

    Returns (v22_state_dict, unmapped_dict). unmapped_dict carries the v4
    `completed` list and any field with no v2.2 equivalent, so nothing is
    silently dropped; the caller writes unmapped_dict into the migration
    decision record. Pure: returns new dicts, never mutates its arguments.
    """
    v4 = copy.deepcopy(v4_obj) if isinstance(v4_obj, dict) else {}
    known_v4_keys = {"goal", "phase", "todos", "checkpoints", "completed"}

    todos = []
    for i, t in enumerate(v4.get("todos", []), start=1):
        if isinstance(t, str):
            todos.append({"id": f"T-{i:03d}", "task": t, "status": "pending", "priority": "normal"})
        elif isinstance(t, dict):
            todos.append(t)

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
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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
    else:
        raise UpgradeError(f"unknown lane mode: {lane_mode}")


def _apply_fresh(manifest, target, source):
    for action, relpath in manifest:
        if action == "ADD":
            copy_path_from_source(relpath, target, source)
        elif action == "REPLACE":
            replace_path_from_source(relpath, target, source)
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
        if relpath.startswith(".project-catalog/decisions/") and action == "ADD":
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
    if relpath == "UDO/PROJECT_STATE.json -> UDO Project/PROJECT_STATE.json":
        v4_state_path = legacy_root / "PROJECT_STATE.json"
        v4_state = load_json(v4_state_path)
        source_state = load_json(source / "UDO Project" / "PROJECT_STATE.json")
        v22_state, unmapped = map_v4_state_to_v22(v4_state, source_state)
        write_json(target / "UDO Project" / "PROJECT_STATE.json", v22_state)
        return unmapped

    item = relpath.split(" -> ", 1)[0].replace("UDO/", "", 1)
    legacy_src = legacy_root / item
    project_dst = target / "UDO Project" / item
    if not legacy_src.exists():
        return None

    if item == "PROJECT_META.json":
        data = load_json(legacy_src)
        write_json(project_dst, transform_project_meta(data))
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


# ---------------------------------------------------------------------------
# Reporting / decision records
# ---------------------------------------------------------------------------

def print_manifest(manifest):
    buckets = {"ADD": [], "REPLACE": [], "TRANSFORM": [], "PRESERVE": []}
    for action, relpath in manifest:
        buckets.setdefault(action, []).append(relpath)

    for label in ("ADD", "REPLACE", "TRANSFORM", "PRESERVE"):
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


def write_migration_record(target, unmapped_by_lane, legacy_dir_name=LEGACY_DIR_NAME):
    date = datetime.date.today().isoformat()
    decisions_dir = target / "UDO Project" / ".project-catalog" / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    record_path = decisions_dir / f"{date}-v4-to-v22-migration-record.md"

    lines = [
        "# v4.x to v2.2 migration record",
        "",
        f"- Date: {date}",
        f"- Legacy installation preserved at: {legacy_dir_name}/",
    ]
    if legacy_dir_name != LEGACY_DIR_NAME:
        lines.append(
            f"- Note: renamed to a timestamp-suffixed name because \"{LEGACY_DIR_NAME}/\" "
            "already existed at this target (most likely a retry after an earlier "
            "migrate attempt)."
        )
    lines += [
        "",
        "## Unmapped / unmappable fields",
        "",
        "Nothing from the v4 PROJECT_STATE.json is dropped silently. Fields with",
        "no v2.2 equivalent, and the v4 `completed` list, are recorded here.",
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
        lines.append(json.dumps(unmapped, indent=2))
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
    parser.add_argument("--mode", choices=["fresh", "upgrade", "migrate", "refresh"], default=None, help="Force a mode instead of auto-detecting")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    target = Path(args.target_dir).expanduser().resolve()

    cleanup_dir = None
    try:
        source, cleanup_dir = fetch_source(args.source)
        source_version = read_source_version(source)

        detection = detect(target, source_version, args.mode)

        if detection.up_to_date:
            print(f"Already up to date: UDO Framework/VERSION is {detection.current_version}.")
            return 0

        mode = detection.mode
        lane_mode = "upgrade" if mode == "refresh" else mode

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

        backup_dir = backup(target)
        print(f"Backup created at: {backup_dir}")

        legacy_dir_name = LEGACY_DIR_NAME
        if lane_mode == "migrate":
            unmapped_by_lane, legacy_dir_name = _apply_migrate(manifest, target, source)
        else:
            apply(manifest, lane_mode, target, source)
            unmapped_by_lane = {}

        returncode, output = run_validate(target)
        if returncode != 0:
            print("")
            print("UPGRADE FAILED: self-verification (validate.py) reported errors.")
            print(output)
            print(f"Backup is at: {backup_dir}")
            print("Restore it if needed before retrying.")
            return 1

        if mode == "migrate":
            migration_record = write_migration_record(target, unmapped_by_lane, legacy_dir_name)
            print(f"Migration record written: {migration_record}")
            if legacy_dir_name != LEGACY_DIR_NAME:
                print(
                    f"Note: legacy UDO/ was renamed to \"{legacy_dir_name}/\" (timestamp-suffixed) "
                    f"because \"{LEGACY_DIR_NAME}/\" already existed at this target."
                )

        record_path = write_decision_record(target, mode, source_version, manifest, backup_dir)
        print("")
        print(f"Upgrade to {source_version} complete (mode: {mode}).")
        print(f"Decision record: {record_path}")
        print(f"Backup: {backup_dir}")
        return 0

    except UpgradeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if cleanup_dir is not None:
            shutil.rmtree(cleanup_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
