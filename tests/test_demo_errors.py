import sys

from snapshot_helpers import (
    check_snapshot,
    diagnostics,
    run_command,
    validate_error_run,
)


def test_demo_errors(
    demo_case, tmp_path, update_snapshots, artifacts_dir, report_update
):
    case = demo_case
    expected = case.errors_root / case.error_profile
    output = tmp_path / "output"
    filename = "demo.errors.stderr.txt"
    with diagnostics(
        tmp_path,
        artifacts=artifacts_dir,
        reference_roots=(case.stubs_root, case.errors_root),
        case_id=case.id,
        check_name="errors",
        expected=expected / filename,
    ):
        result = run_command(
            [
                sys.executable,
                "-I",
                "-m",
                "pybind11_stubgen",
                "demo",
                "--output-dir",
                str(output),
                "--exit-code",
            ],
            cwd=tmp_path,
            log=tmp_path / "stubgen",
            expected_status=1,
        )
        stderr = validate_error_run(result, output)
        (tmp_path / "normalized.stderr").write_bytes(stderr)
        changed = check_snapshot(
            case.errors_root,
            case.error_profile,
            {filename: stderr},
            update=update_snapshots,
            only=frozenset({filename}),
        )
        if update_snapshots:
            report_update(
                f"{case.id}: {expected} -> {expected.resolve()}; changed: {changed}"
            )
