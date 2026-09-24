import sys

from snapshot_helpers import (
    HarnessError,
    check_snapshot,
    diagnostics,
    format_stubs,
    read_tree,
    run_command,
)


def test_demo_stubs(
    demo_case, tmp_path, update_snapshots, artifacts_dir, report_update
):
    case = demo_case
    expected = case.stubs_root / case.stub_profile
    output = tmp_path / "output"
    with diagnostics(
        tmp_path,
        artifacts=artifacts_dir,
        reference_roots=(case.stubs_root, case.errors_root),
        case_id=case.id,
        check_name="stubs",
        expected=expected,
    ):
        run_command(
            [
                sys.executable,
                "-I",
                "-m",
                "pybind11_stubgen",
                "demo",
                "--output-dir",
                str(output),
                f"--{case.numpy_format}",
                r"--ignore-invalid-expressions=\(anonymous namespace\)::(Enum|Unbound)|<demo\._bindings\.flawed_bindings\..*",
                "--enum-class-locations=ConsoleForegroundColor:demo._bindings.enum",
                "--print-value-comments",
                r"--print-safe-value-reprs=Foo\(\d+\)",
                "--exit-code",
            ],
            cwd=tmp_path,
            log=tmp_path / "stubgen",
            expected_status=0,
        )
        if "demo/__init__.pyi" not in read_tree(output):
            raise HarnessError(
                "Successful demo generation did not produce demo/__init__.pyi"
            )
        format_stubs(output, case.repo, tmp_path, case.python_version)
        actual = read_tree(output)
        if "demo/__init__.pyi" not in actual:
            raise HarnessError("Normalized output lost demo/__init__.pyi")
        changed = check_snapshot(
            case.stubs_root, case.stub_profile, actual, update=update_snapshots
        )
        if update_snapshots:
            report_update(
                f"{case.id}: {expected} -> {expected.resolve()}; changed: {changed}"
            )
