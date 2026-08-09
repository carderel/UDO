#!/usr/bin/env python3
"""Detection fixtures for upgrade.py.

Why this file exists: the same defect class has now shipped three times. Each
time, detect() picked a lane from a signal that looked positive but pointed at
the wrong thing, the run reported success, and the user's real project was
left behind un-upgraded.

  v2.2.2  v4-at-root installs fell through to fresh
  v2.2.5  installs one folder down fell through to fresh
  v2.2.6  a placeholder scaffold from a previous mis-install took the upgrade
          lane, so the v2.2.5 guard was never reached

Detection is pure (it reads the filesystem and mutates nothing), so it is cheap
to pin down. Every lane gets a fixture here, not just the ones that broke.

Run: python3 tests/test_detect.py     Exit 0 = all pass.
"""

import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE_VERSION = "2.2.6"


def load_upgrade():
    spec = importlib.util.spec_from_file_location("udo_upgrade", REPO / "upgrade.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["udo_upgrade"] = mod
    spec.loader.exec_module(mod)
    return mod


U = load_upgrade()

PLACEHOLDER_STATE = {
    "project_state": {
        "project_name": "New Project",
        "project_id": "placeholder-project-id",
        "goal": "",
        "current_phase": "setup",
        "session_count": 0,
        "prompt_count": 0,
        "todos": [],
    }
}

USED_STATE = {
    "project_state": {
        "project_name": "Market Researcher",
        "project_id": "mr-7731",
        "goal": "EV switch solar research",
        "current_phase": "generator_reported_awaiting_owner_gates",
        "session_count": 41,
        "prompt_count": 235,
        "todos": [{"id": "T-001", "task": "collect owner outputs", "status": "pending"}],
    }
}


# --- fixture builders -------------------------------------------------------

def make_v2_install(path, version="2.2.4", state=None, session_logs=()):
    """A v2.x install: 'UDO Framework/' + 'UDO Project/' as siblings."""
    (path / "UDO Framework").mkdir(parents=True, exist_ok=True)
    (path / "UDO Framework" / "VERSION").write_text(version, encoding="utf-8")
    (path / "UDO Framework" / "ORCHESTRATOR.md").write_text("# orchestrator\n", encoding="utf-8")
    (path / "UDO Framework" / "HARD_STOPS.md").write_text("# hard stops\n", encoding="utf-8")
    (path / "UDO Framework" / "COMMANDS.md").write_text("# commands\n", encoding="utf-8")
    (path / "UDO Framework" / "REASONING_CONTRACT.md").write_text("# rc\n", encoding="utf-8")
    sessions = path / "UDO Project" / ".project-catalog" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / ".gitkeep").write_text("", encoding="utf-8")
    for name in session_logs:
        (sessions / name).write_text("# session\n", encoding="utf-8")
    body = PLACEHOLDER_STATE if state is None else state
    (path / "UDO Project" / "PROJECT_STATE.json").write_text(
        json.dumps(body, indent=2), encoding="utf-8"
    )
    return path


def make_v4_udo_subfolder_install(path):
    """A v4.x install living in a 'UDO/' subfolder."""
    (path / "UDO").mkdir(parents=True, exist_ok=True)
    for name in U.V4_ROOT_MARKERS:
        (path / "UDO" / name).write_text("# v4\n", encoding="utf-8")
    return path


def make_v4_root_install(path, marker_count=5):
    """A v4.x install with its protocol files loose at the folder root."""
    path.mkdir(parents=True, exist_ok=True)
    for name in U.V4_ROOT_MARKERS[:marker_count]:
        (path / name).write_text("# v4\n", encoding="utf-8")
    return path


# --- assertions -------------------------------------------------------------

RESULTS = []


def check(name, fn):
    try:
        fn()
    except AssertionError as exc:
        RESULTS.append((name, False, str(exc)))
    except Exception as exc:  # noqa: BLE001 - a crash is a failed fixture
        RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
    else:
        RESULTS.append((name, True, ""))


def expect_lane(target, lane, forced=None, version=None):
    res = U.detect(target, SOURCE_VERSION, forced)
    assert res.mode == lane, f"expected lane {lane!r}, got {res.mode!r}"
    if version is not None:
        assert res.current_version == version, (
            f"expected current_version {version!r}, got {res.current_version!r}"
        )
    return res


def expect_refusal(target, *must_contain, forced=None):
    try:
        res = U.detect(target, SOURCE_VERSION, forced)
    except U.UpgradeError as exc:
        text = str(exc)
        for fragment in must_contain:
            assert fragment in text, f"refusal did not mention {fragment!r}:\n{text}"
        return text
    raise AssertionError(f"expected a refusal, got lane {res.mode!r}")


# --- the fixtures ----------------------------------------------------------

def run_all(tmp):
    def case(name):
        d = tmp / name
        d.mkdir(parents=True)
        return d

    # Lanes that must keep working exactly as they did.
    def t_bare():
        expect_lane(case("bare"), "fresh")

    def t_upgrade():
        d = make_v2_install(case("upgrade"), version="2.2.4", state=USED_STATE)
        expect_lane(d, "upgrade", version="2.2.4")

    def t_up_to_date():
        d = make_v2_install(case("uptodate"), version=SOURCE_VERSION, state=USED_STATE)
        res = expect_lane(d, "upgrade", version=SOURCE_VERSION)
        assert res.up_to_date is True, "same version should report up_to_date"

    def t_migrate():
        d = make_v4_udo_subfolder_install(case("migrate"))
        expect_lane(d, "migrate")

    def t_migrate_root():
        d = make_v4_root_install(case("migrateroot"))
        expect_lane(d, "migrate-root")

    # v2.2.5: nested installs must never fall through to fresh.
    def t_nested_v2():
        d = case("nested_v2")
        make_v2_install(d / "UDO-v2.0", version="2.1", state=USED_STATE)
        expect_refusal(d, "UDO-v2.0/", "v2.x install, version 2.1")

    def t_nested_v4_subfolder():
        d = case("nested_v4_sub")
        make_v4_udo_subfolder_install(d / "project")
        expect_refusal(d, "project/", "v4.x install in a UDO/ subfolder")

    def t_nested_v4_root():
        d = case("nested_v4_root")
        make_v4_root_install(d / "legacy")
        expect_refusal(d, "legacy/", "v4.x install at that folder's root")

    def t_backup_not_nested():
        d = case("backup_only")
        make_v2_install(d / ".udo-backup-20260807-120924", state=USED_STATE)
        expect_lane(d, "fresh")

    def t_forced_fresh_overrides_nested():
        d = case("forced_fresh")
        make_v2_install(d / "UDO", state=USED_STATE)
        expect_lane(d, "fresh", forced="fresh")

    def t_ambiguous_markers_plus_nested():
        d = case("ambiguous")
        make_v4_root_install(d, marker_count=2)
        make_v2_install(d / "UDO", version="4.10", state=USED_STATE)
        expect_refusal(d, "2 v4.x root marker file(s)", "UDO/", "one level down")

    # v2.2.6: a placeholder scaffold must not take the upgrade lane while a
    # real install sits below it. This is the Market Researcher shape.
    def t_placeholder_over_nested():
        d = case("placeholder_over_nested")
        make_v2_install(d, version="2.2.4")               # scaffold, never used
        make_v2_install(d / "UDO", version="4.10", state=USED_STATE)
        make_v2_install(d / "UDO-v2.0", version="2.1", state=USED_STATE)
        text = expect_refusal(d, "has never been used", "UDO/", "UDO-v2.0/", "--mode upgrade")
        assert "UDO Framework/" not in text, (
            "the install's own framework folder was reported as a nested install:\n" + text
        )

    def t_placeholder_alone_upgrades():
        d = make_v2_install(case("placeholder_alone"), version="2.2.4")
        expect_lane(d, "upgrade", version="2.2.4")

    def t_used_install_over_nested_still_upgrades():
        d = case("used_over_nested")
        make_v2_install(d, version="2.2.4", state=USED_STATE)
        make_v2_install(d / "subproject", version="2.2.4", state=USED_STATE)
        expect_lane(d, "upgrade", version="2.2.4")

    def t_placeholder_with_session_log_upgrades():
        """One session log is enough to prove the install is real."""
        d = case("placeholder_with_log")
        make_v2_install(d, version="2.2.4", session_logs=("2026-08-09-session.md",))
        make_v2_install(d / "UDO", version="4.10", state=USED_STATE)
        expect_lane(d, "upgrade", version="2.2.4")

    def t_forced_upgrade_overrides_placeholder_guard():
        d = case("forced_upgrade")
        make_v2_install(d, version="2.2.4")
        make_v2_install(d / "UDO", version="4.10", state=USED_STATE)
        expect_lane(d, "upgrade", forced="upgrade")

    def t_remnant_scaffold_over_nested():
        """A scaffold someone has already half-removed by hand: the framework
        folder is still there, UDO Project/ is gone. Nothing in it proves it is
        anyone's project, so it must not quietly take the upgrade lane either."""
        d = case("remnant")
        make_v2_install(d, version="2.2.4")
        shutil.rmtree(d / "UDO Project")
        make_v2_install(d / "UDO", version="4.10", state=USED_STATE)
        expect_refusal(d, "has never been used", "UDO/")

    def t_structural_dirs_not_nested():
        d = make_v2_install(case("structural"), state=USED_STATE)
        found = [name for name, _ in U.find_nested_installs(d)]
        assert found == [], f"structural dirs reported as nested installs: {found}"

    for fn in [
        t_bare, t_upgrade, t_up_to_date, t_migrate, t_migrate_root,
        t_nested_v2, t_nested_v4_subfolder, t_nested_v4_root,
        t_backup_not_nested, t_forced_fresh_overrides_nested,
        t_ambiguous_markers_plus_nested,
        t_placeholder_over_nested, t_placeholder_alone_upgrades,
        t_used_install_over_nested_still_upgrades,
        t_placeholder_with_session_log_upgrades,
        t_forced_upgrade_overrides_placeholder_guard,
        t_remnant_scaffold_over_nested,
        t_structural_dirs_not_nested,
    ]:
        check(fn.__name__[2:], fn)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="udo-detect-fixtures-"))
    try:
        run_all(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("\n".join("        " + ln for ln in detail.splitlines()))
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
