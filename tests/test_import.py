#!/usr/bin/env python3
"""Handoff bundle import fixtures (v2.3 Phase B).

Import is the only command in this tool that can destroy a project. These
fixtures exist for the refusals, not the happy path: each one is a way the
import could have quietly replaced good work with less of it.

Run: python3 tests/test_import.py     Exit 0 = all pass.
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
    spec = importlib.util.spec_from_file_location("udo_upgrade_imp", REPO / "upgrade.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["udo_upgrade_imp"] = mod
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


def tree_digest(root, skip_prefixes=()):
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if any(rel.startswith(p) for p in skip_prefixes):
            continue
        h.update(rel.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_v2(root, sessions=3, goal="ship it", version="2.2.4"):
    write(root / "UDO Framework" / "VERSION", version)
    for name in U.V4_ROOT_MARKERS:
        write(root / "UDO Framework" / name, f"# framework {name}\n")
    write(root / "UDO Project" / "PROJECT_STATE.json", json.dumps({"project_state": {
        "project_name": "T", "project_id": "real-1", "goal": goal, "current_phase": "build",
        "session_count": sessions, "todos": [], "deferred_debt": [], "scope_locked": False,
        "auto_checkpoint": {}, "circuit_breaker": {}}}, indent=2))
    for i in range(sessions):
        write(root / "UDO Project" / ".project-catalog" / "sessions" / f"2026-08-{i+1:02d}-s.md",
              f"# session {i}\n")
    write(root / "UDO Project" / "LESSONS_LEARNED.md", "# lessons\n")
    return root


def make_bundle(tmp, name, sessions=3, goal="ship it"):
    src = build_v2(tmp / f"{name}-src", sessions=sessions, goal=goal)
    bundle, manifest, _u = U.export_bundle(src, bundle_path=str(tmp / f"{name}-bundle"))
    return src, bundle, manifest


def expect_refusal(fn, *must_contain):
    try:
        fn()
    except U.UpgradeError as exc:
        text = str(exc)
        for frag in must_contain:
            assert frag in text, f"refusal did not mention {frag!r}:\n{text}"
        return text
    raise AssertionError("expected a refusal, got success")


def run_all(tmp):
    SOURCE = REPO

    def t_unknown_bundle_format_refused():
        _src, bundle, _m = make_bundle(tmp, "fmt")
        m = json.loads((bundle / "manifest.json").read_text())
        m["bundle_format"] = 2
        (bundle / "manifest.json").write_text(json.dumps(m))
        expect_refusal(lambda: U.import_handoff(bundle, tmp / "fmt-src", SOURCE, assume_yes=True),
                       "bundle_format", "Refusing to guess")

    def t_tampered_file_refused():
        _src, bundle, _m = make_bundle(tmp, "tamper")
        victim = next((bundle / "records" / "sessions").glob("*.md"))
        victim.write_text("tampered\n", encoding="utf-8")
        expect_refusal(lambda: U.import_handoff(bundle, tmp / "tamper-src", SOURCE, assume_yes=True),
                       "not intact", "checksum")

    def t_missing_file_refused():
        _src, bundle, _m = make_bundle(tmp, "missing")
        next((bundle / "records" / "sessions").glob("*.md")).unlink()
        expect_refusal(lambda: U.import_handoff(bundle, tmp / "missing-src", SOURCE, assume_yes=True),
                       "not intact", "not in the bundle")

    def t_thin_bundle_over_fat_install_refused():
        """The scenario the whole comparison exists for: a bundle exported from
        the wrong folder is internally perfect and carries almost nothing."""
        _thin_src, bundle, _m = make_bundle(tmp, "thin", sessions=1)
        fat = build_v2(tmp / "thin-src", sessions=1)  # same path as the bundle's source
        for i in range(40):
            write(fat / "UDO Project" / ".project-catalog" / "sessions" / f"2026-09-{i+1:02d}-s.md",
                  "# real work\n")
        text = expect_refusal(
            lambda: U.import_handoff(bundle, fat, SOURCE, assume_yes=True,
                                     force_concurrent=True),
            "carries less than the install it would replace", "--accept-record-loss")
        assert "sessions" in text

    def t_record_loss_override_works():
        _s, bundle, _m = make_bundle(tmp, "thin2", sessions=1)
        fat = build_v2(tmp / "thin2-src", sessions=1)
        for i in range(10):
            write(fat / "UDO Project" / ".project-catalog" / "sessions" / f"2026-09-{i+1:02d}-s.md",
                  "# real work\n")
        rc = U.import_handoff(bundle, fat, SOURCE, assume_yes=True,
                              accept_record_loss=True, force_concurrent=True)
        assert rc == 0, f"import returned {rc}"

    def t_nested_install_refused():
        _s, bundle, _m = make_bundle(tmp, "nest")
        target = tmp / "nest-src"
        build_v2(target / "RealProject", sessions=2)
        expect_refusal(
            lambda: U.import_handoff(bundle, target, SOURCE, assume_yes=True, force_concurrent=True),
            "one level below", "RealProject/", "--install-root")

    def t_concurrency_refused():
        _s, bundle, _m = make_bundle(tmp, "conc")
        target = tmp / "conc-src"
        # Touch an existing record rather than adding one: adding would change
        # the counts and trip the record-loss gate first, which now runs earlier.
        write(target / "UDO Project" / ".project-catalog" / "sessions" / "2026-08-01-s.md",
              "# touched by a live session\n")
        expect_refusal(
            lambda: U.import_handoff(bundle, target, SOURCE, assume_yes=True),
            "session running right now", "--force-concurrent")

    def t_undescribed_unclassified_refused():
        src = build_v2(tmp / "desc-src")
        write(src / "UDO Project" / "mystery.dat", "?\n")
        bundle, _m, _u = U.export_bundle(src, bundle_path=str(tmp / "desc-bundle"))
        expect_refusal(
            lambda: U.import_handoff(bundle, src, SOURCE, assume_yes=True, force_concurrent=True),
            "never classified", "NOTES.md", "--accept-undescribed")

    def t_describing_clears_the_gate():
        src = build_v2(tmp / "desc2-src")
        write(src / "UDO Project" / "mystery.dat", "?\n")
        bundle, _m, _u = U.export_bundle(src, bundle_path=str(tmp / "desc2-bundle"))
        notes = bundle / "NOTES.md"
        notes.write_text(notes.read_text() + "\nIt is a data file from the old pipeline.\n")
        rc = U.import_handoff(bundle, src, SOURCE, assume_yes=True, force_concurrent=True)
        assert rc == 0, f"import returned {rc}"
        landed = src / "UDO Project" / ".project-catalog" / "imported-unclassified"
        assert (landed / "UDO Project" / "mystery.dat").is_file(), sorted(
            p.as_posix() for p in landed.rglob("*"))

    def t_failed_validation_leaves_target_untouched():
        """The staging property. If the replacement does not validate, the
        project must be exactly as it was, not half-migrated."""
        src = build_v2(tmp / "atomic-src", sessions=4)
        bundle, _m, _u = U.export_bundle(src, bundle_path=str(tmp / "atomic-bundle"))
        before = tree_digest(src)
        real_validate = U.run_validate
        U.run_validate = lambda path: (1, "forced failure for the fixture")
        try:
            expect_refusal(
                lambda: U.import_handoff(bundle, src, SOURCE, assume_yes=True,
                                         force_concurrent=True),
                "failed validate.py", "nothing was moved")
        finally:
            U.run_validate = real_validate
        after = tree_digest(src, skip_prefixes=(".udo-backup-",))
        assert after == before, "target changed despite a failed staging validation"
        assert not list(src.glob(U.STAGING_PREFIX + "*")), "staging directory left behind"

    def t_successful_import_carries_records_and_keeps_user_files():
        src = build_v2(tmp / "happy-src", sessions=5, goal="CARRY ME")
        write(src / "app.py", "my own code\n")
        bundle, _m, _u = U.export_bundle(src, bundle_path=str(tmp / "happy-bundle"))
        rc = U.import_handoff(bundle, src, SOURCE, assume_yes=True, force_concurrent=True)
        assert rc == 0
        state = json.loads((src / "UDO Project" / "PROJECT_STATE.json").read_text())
        assert state["project_state"]["goal"] == "CARRY ME", state["project_state"]
        landed = sorted(p.name for p in
                        (src / "UDO Project" / ".project-catalog" / "sessions").glob("2026-08-*.md"))
        assert len(landed) == 5, landed
        assert (src / "app.py").read_text() == "my own code\n", "user file was disturbed"
        assert list(src.glob(U.PRE_IMPORT_PREFIX + "*")), "previous install was not set aside"

    def t_old_install_is_set_aside_not_deleted():
        src = build_v2(tmp / "aside-src", sessions=2)
        bundle, _m, _u = U.export_bundle(src, bundle_path=str(tmp / "aside-bundle"))
        U.import_handoff(bundle, src, SOURCE, assume_yes=True, force_concurrent=True)
        pre = next(iter(src.glob(U.PRE_IMPORT_PREFIX + "*")))
        assert (pre / "UDO Project" / "PROJECT_STATE.json").is_file(), sorted(
            p.as_posix() for p in pre.rglob("*"))

    for fn in [
        t_unknown_bundle_format_refused, t_tampered_file_refused, t_missing_file_refused,
        t_thin_bundle_over_fat_install_refused, t_record_loss_override_works,
        t_nested_install_refused, t_concurrency_refused,
        t_undescribed_unclassified_refused, t_describing_clears_the_gate,
        t_failed_validation_leaves_target_untouched,
        t_successful_import_carries_records_and_keeps_user_files,
        t_old_install_is_set_aside_not_deleted,
    ]:
        check(fn.__name__[2:], fn)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="udo-import-fixtures-"))
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
