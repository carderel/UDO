#!/usr/bin/env python3
"""Handoff bundle fixtures (v2.3 Phase A: export and restore).

Phase A cannot destroy anything, by construction: export is read-only and
restore only recovers. These fixtures hold that line, and pin the properties
the red team said the design depended on.

Run: python3 tests/test_export.py     Exit 0 = all pass.
"""

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_upgrade():
    spec = importlib.util.spec_from_file_location("udo_upgrade_exp", REPO / "upgrade.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["udo_upgrade_exp"] = mod
    spec.loader.exec_module(mod)
    return mod


U = load_upgrade()

RESULTS = []


def check(name, fn):
    try:
        fn()
    except AssertionError as exc:
        RESULTS.append((name, False, str(exc)))
    except Exception as exc:  # noqa: BLE001
        RESULTS.append((name, False, f"{type(exc).__name__}: {exc}"))
    else:
        RESULTS.append((name, True, ""))


def tree_digest(root):
    """One digest over every file's relative path and contents."""
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# --- install builders -------------------------------------------------------

def build_v2(root, version="2.2.4", flat_state=False, sessions=3):
    write(root / "UDO Framework" / "VERSION", version)
    for name in U.V4_ROOT_MARKERS:
        write(root / "UDO Framework" / name, f"# framework {name}\n")
    state = {"project_name": "Test", "project_id": "real-1", "goal": "ship it",
             "session_count": 7, "todos": [{"id": "T-1", "task": "a", "status": "pending"}]}
    body = state if flat_state else {"project_state": state}
    write(root / "UDO Project" / "PROJECT_STATE.json", json.dumps(body, indent=2))
    for i in range(sessions):
        write(root / "UDO Project" / ".project-catalog" / "sessions" / f"2026-08-0{i+1}-session.md",
              f"# session {i}\n")
    write(root / "UDO Project" / ".project-catalog" / "history" / "2026-08-01-transcript.md", "t\n")
    write(root / "UDO Project" / ".project-catalog" / "decisions" / "2026-08-01-choice.md", "d\n")
    write(root / "UDO Project" / "LESSONS_LEARNED.md", "# lessons\n")
    write(root / "UDO Project" / ".agents" / "researcher.md", "# agent\n")
    return root


def build_v4_root(root, sessions=3):
    for name in U.V4_ROOT_MARKERS:
        write(root / name, f"# v4 {name}\n")
    write(root / "PROJECT_STATE.json", json.dumps(
        {"goal": "v4 goal", "phase": "build", "todos": ["do a thing"],
         "completed": ["an old thing"]}, indent=2))
    for i in range(sessions):
        write(root / ".project-catalog" / "sessions" / f"2026-07-0{i+1}-session.md", f"# s{i}\n")
    write(root / "LESSONS_LEARNED.md", "# v4 lessons\n")
    return root


def build_v4_udo(root, sessions=3):
    build_v4_root(root / "UDO", sessions=sessions)
    write(root / "client-work" / "notes.md", "not udo\n")
    return root


# --- fixtures ---------------------------------------------------------------

def run_all(tmp):
    def case(name):
        d = tmp / name
        d.mkdir(parents=True)
        return d

    def t_script_version_matches_the_release():
        """SCRIPT_VERSION is what lets a stale download announce itself. A
        literal nobody keeps current would announce the wrong thing, so the
        repo holds it in step rather than trusting release discipline."""
        shipped = (REPO / "UDO Framework" / "VERSION").read_text(encoding="utf-8").strip()
        assert U.SCRIPT_VERSION == shipped, (
            f"SCRIPT_VERSION is {U.SCRIPT_VERSION!r} but UDO Framework/VERSION is "
            f"{shipped!r}. Bump both, or the staleness warning lies.")

    def t_stale_script_warns(capsys=None):
        """A script older than the release it installs must say so."""
        import io
        import contextlib
        buf = io.StringIO()
        real = U.SCRIPT_VERSION
        U.SCRIPT_VERSION = "2.2.0"
        try:
            with contextlib.redirect_stdout(buf):
                U._warn_if_script_is_stale("2.3.3", None)
        finally:
            U.SCRIPT_VERSION = real
        out = buf.getvalue()
        assert "WARNING" in out and "2.2.0" in out and "2.3.3" in out, out
        assert "git clone" in out, "the warning must offer a way to get the current script"

    def t_current_script_does_not_warn():
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            U._warn_if_script_is_stale(U.SCRIPT_VERSION, None)
        assert buf.getvalue() == "", f"unexpected output: {buf.getvalue()!r}"

    def t_export_read_only():
        """The invariant the whole design rests on. Whole tree, no exclusions."""
        d = build_v2(case("ro") / "proj")
        before = tree_digest(d)
        U.export_bundle(d, bundle_path=str(tmp / "ro-bundle"))
        assert tree_digest(d) == before, "export modified the source install"

    def t_bundle_defaults_outside_the_project():
        d = build_v2(case("outside") / "proj")
        bundle, _m, _u = U.export_bundle(d)
        assert not str(bundle).startswith(str(d) + "/"), (
            f"bundle {bundle} was written inside the install {d}")

    def t_roundtrip_v2():
        d = build_v2(case("rt_v2") / "proj", sessions=4)
        bundle, manifest, _u = U.export_bundle(d, bundle_path=str(tmp / "rt-v2-bundle"))
        assert manifest["counts"]["sessions"] == 4, manifest["counts"]
        assert (bundle / "records" / "sessions" / "2026-08-01-session.md").is_file()
        state = json.loads((bundle / "state.json").read_text())
        assert state["project_state"]["goal"] == "ship it"
        assert state["project_state"]["session_count"] == 7

    def t_roundtrip_v4_root():
        d = build_v4_root(case("rt_v4r") / "proj", sessions=2)
        bundle, manifest, _u = U.export_bundle(d, bundle_path=str(tmp / "rt-v4r-bundle"))
        assert manifest["source"]["layout"] == "v4-root", manifest["source"]
        assert manifest["counts"]["sessions"] == 2, manifest["counts"]
        state = json.loads((bundle / "state.json").read_text())
        assert state["project_state"]["goal"] == "v4 goal", state
        # v4 "completed" has no v2.2 home and must be preserved, not dropped
        unmapped = json.loads((bundle / "unmapped.json").read_text())
        assert "completed" in json.dumps(unmapped), unmapped

    def t_roundtrip_v4_udo():
        d = build_v4_udo(case("rt_v4u") / "proj", sessions=2)
        bundle, manifest, _u = U.export_bundle(d, bundle_path=str(tmp / "rt-v4u-bundle"))
        assert manifest["source"]["layout"] == "v4-udo", manifest["source"]
        assert manifest["counts"]["sessions"] == 2, (
            f"v4-udo sessions not found; map paths are relative to the install "
            f"root, not the project folder. counts={manifest['counts']}")
        assert (bundle / "records" / "sessions" / "2026-07-01-session.md").is_file()

    def t_v21_flat_state_is_wrapped():
        """v2.0/v2.1 kept state flat; v2.2 nests it. Proven as a standalone
        normalizer, not as a side effect of the upgrade lane."""
        d = build_v2(case("flat") / "proj", version="2.1", flat_state=True)
        bundle, _m, _u = U.export_bundle(d, bundle_path=str(tmp / "flat-bundle"))
        state = json.loads((bundle / "state.json").read_text())
        assert "project_state" in state, f"flat v2.1 state was not wrapped: {state}"
        assert state["project_state"]["goal"] == "ship it"
        assert state["project_state"]["session_count"] == 7

    def t_raw_on_unknown_shape():
        d = case("raw_unknown") / "proj"
        write(d / "weird" / "thing.md", "who knows\n")
        write(d / "PROJECT_STATE.json", "{}\n")
        bundle, manifest, unclassified = U.export_bundle(
            d, bundle_path=str(tmp / "raw-bundle"), raw=True)
        assert manifest["mode"] == "raw", manifest["mode"]
        assert manifest["source"]["layout_source"] == "none"
        assert (bundle / "UNCLASSIFIED" / "weird" / "thing.md").is_file()
        assert len(unclassified) >= 2, unclassified

    def t_raw_needs_no_detection():
        """H1: export must not depend on detect(), which is the thing v2.3
        exists to stop depending on."""
        d = case("raw_nodetect") / "proj"
        write(d / "anything.md", "x\n")
        original = U.detect
        U.detect = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("detect() must not be called in raw mode"))
        try:
            _b, manifest, _u = U.export_bundle(
                d, bundle_path=str(tmp / "nodetect-bundle"), raw=True)
        finally:
            U.detect = original
        assert manifest["mode"] == "raw"

    def t_ambiguity_points_at_raw():
        """Where export cannot resolve the install it must hand the user a
        working next step, not a dead end."""
        d = case("ambiguous") / "proj"
        build_v2(d / "UDO", version="4.10")
        write(d / "ORCHESTRATOR.md", "# partial\n")
        try:
            U.export_bundle(d, bundle_path=str(tmp / "amb-bundle"))
        except U.UpgradeError as exc:
            assert "--raw" in str(exc), f"refusal did not offer --raw:\n{exc}"
            return
        raise AssertionError("expected a refusal for an ambiguous target")

    def t_manifest_accounts_for_every_file():
        """Completeness has to be checkable against the source, not against the
        bundle's own contents."""
        d = build_v2(case("complete") / "proj")
        write(d / "UDO Project" / "mystery.dat", "?\n")
        _b, manifest, _u = U.export_bundle(d, bundle_path=str(tmp / "complete-bundle"))
        seen = {e["path"] for e in manifest["inventory"]}
        on_disk = {p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()}
        assert on_disk <= seen, f"files missing from the inventory: {sorted(on_disk - seen)}"

    def t_windows_hostile_paths():
        d = build_v2(case("win") / "proj")
        write(d / "UDO Project" / "CON.md", "reserved device name\n")
        write(d / "UDO Project" / "trailing.", "trailing dot\n")
        write(d / "UDO Project" / "Collide.md", "one\n")
        write(d / "UDO Project" / "collide.md", "two\n")
        bundle, manifest, _u = U.export_bundle(d, bundle_path=str(tmp / "win-bundle"))
        renamed = [e for e in manifest["inventory"] if "renamed_from" in e]
        assert renamed, "no renames recorded for Windows-hostile paths"
        for entry in manifest["inventory"]:
            if entry.get("bundle_path"):
                assert (bundle / entry["bundle_path"]).is_file(), entry
        written = [e for e in manifest["inventory"] if e.get("bundle_path")]
        assert len({e["bundle_path"] for e in written}) == len(written), (
            "two files were written to the same bundle path")

    def t_merged_record_folders_do_not_collide():
        """Several source folders merge into one bundle folder by design
        (.checkpoints and .project-catalog/checkpoints both carry checkpoints).
        Same-named files from two of them must not overwrite each other."""
        d = build_v2(case("merge") / "proj")
        write(d / "UDO Project" / ".checkpoints" / "same-name.md", "from dot-checkpoints\n")
        write(d / "UDO Project" / ".project-catalog" / "checkpoints" / "same-name.md",
              "from catalog checkpoints\n")
        bundle, manifest, _u = U.export_bundle(d, bundle_path=str(tmp / "merge-bundle"))
        written = [e for e in manifest["inventory"] if e.get("bundle_path")]
        paths = [e["bundle_path"] for e in written]
        assert len(set(paths)) == len(paths), f"collision: {sorted(paths)}"
        bodies = {(bundle / p).read_text() for p in paths if p.startswith("records/checkpoints")}
        assert bodies == {"from dot-checkpoints\n", "from catalog checkpoints\n"}, bodies

    def t_refuses_to_overwrite_a_bundle():
        d = build_v2(case("overwrite") / "proj")
        target = str(tmp / "overwrite-bundle")
        U.export_bundle(d, bundle_path=target)
        try:
            U.export_bundle(d, bundle_path=target)
        except U.UpgradeError as exc:
            assert "already exists" in str(exc)
            return
        raise AssertionError("expected a refusal to overwrite an existing bundle")

    def t_notes_lists_every_unclassified_item():
        d = build_v2(case("notes") / "proj")
        write(d / "UDO Project" / "mystery.dat", "?\n")
        bundle, manifest, unclassified = U.export_bundle(
            d, bundle_path=str(tmp / "notes-bundle"))
        notes = (bundle / "NOTES.md").read_text()
        for rel in unclassified:
            assert rel in notes, f"{rel} missing from NOTES.md"
        assert manifest["notes_sha256"], "manifest must record the notes checksum"

    def t_restore_round_trip():
        d = build_v2(case("restore") / "proj")
        before = tree_digest(d)
        backup = d / ".udo-backup-20260810-120000"
        backup.mkdir()
        for item in list(d.iterdir()):
            if item.name.startswith(".udo-backup-"):
                continue
            dst = backup / item.name
            shutil.copytree(str(item), str(dst)) if item.is_dir() else shutil.copy2(
                str(item), str(dst))
        shutil.rmtree(d / "UDO Project")
        write(d / "UDO Project" / "PROJECT_STATE.json", '{"project_state": {"goal": "wrong"}}')
        rc = U.restore_backup(backup, d, assume_yes=True)
        assert rc == 0, f"restore returned {rc}"
        state = json.loads((d / "UDO Project" / "PROJECT_STATE.json").read_text())
        assert state["project_state"]["goal"] == "ship it", state
        assert (d / "UDO Project" / ".project-catalog" / "sessions").is_dir()
        del before  # backup dir and quarantine make a whole-tree digest unequal by design

    def t_restore_refuses_a_foreign_directory(sub=None):
        d = build_v2(case("restore_foreign") / "proj")
        notabackup = d.parent / "some-folder"
        notabackup.mkdir()
        try:
            U.restore_backup(notabackup, d, assume_yes=True)
        except U.UpgradeError as exc:
            assert "does not look like a backup" in str(exc)
            return
        raise AssertionError("expected a refusal to restore from a foreign directory")

    for fn in [
        t_script_version_matches_the_release,
        t_stale_script_warns, t_current_script_does_not_warn,
        t_export_read_only, t_bundle_defaults_outside_the_project,
        t_roundtrip_v2, t_roundtrip_v4_root, t_roundtrip_v4_udo,
        t_v21_flat_state_is_wrapped,
        t_raw_on_unknown_shape, t_raw_needs_no_detection, t_ambiguity_points_at_raw,
        t_manifest_accounts_for_every_file, t_windows_hostile_paths,
        t_merged_record_folders_do_not_collide,
        t_refuses_to_overwrite_a_bundle, t_notes_lists_every_unclassified_item,
        t_restore_round_trip, t_restore_refuses_a_foreign_directory,
    ]:
        check(fn.__name__[2:], fn)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="udo-export-fixtures-"))
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
