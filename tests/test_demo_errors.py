import sys

from snapshot_catalog import check_case, load_catalog
from snapshot_helpers import (
    diagnostics,
    run_command,
    validate_error_run,
)


def test_demo_errors(
    demo_case, tmp_path, update_snapshots, artifacts_dir, report_update
):
    case = demo_case
    expected = case.catalog_path
    output = tmp_path / "output"
    filename = "demo.errors.stderr.txt"
    with diagnostics(
        tmp_path,
        artifacts=artifacts_dir,
        reference_roots=(expected, case.stubs_root, case.errors_root),
        case_id=case.id,
        check_name="errors",
        expected=expected,
        reference_details=load_catalog(case.repo).context(case.id, "errors"),
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
        message = check_case(
            case.repo,
            case.id,
            "errors",
            {filename: stderr},
            update=update_snapshots,
            only=frozenset({filename}),
        )
        if update_snapshots:
            report_update(message)
