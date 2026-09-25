import json
import os
import sys
import zipfile
from importlib.machinery import EXTENSION_SUFFIXES
from pathlib import Path

import pytest

from build_native import (
    audit_wheel,
    build_command,
    expected_versions,
    install_command,
    new_run_dir,
    run_logged,
)

PINS = {
    "numpy": "2.2.6",
    "scipy": "1.15.3",
    "pybind11": "2.9.2",
    "cmake": "3.31.10",
    "ninja": "1.13.2",
    "scikit-build-core": "1.0.3",
    "cmeel": "0.59.0",
    "cmeel-eigen": "3.4.0.2",
}


def test_explicit_versions_are_required():
    env = {
        "STUBGEN_" + k.upper().replace("-", "_") + "_VERSION": v
        for k, v in PINS.items()
    }
    assert expected_versions(env) == PINS
    del env["STUBGEN_NUMPY_VERSION"]
    with pytest.raises(RuntimeError, match="STUBGEN_NUMPY_VERSION"):
        expected_versions(env)


def test_run_directories_are_owned_unique_and_not_source(tmp_path):
    repo = tmp_path / "repo"
    prefix = tmp_path / "env"
    first = new_run_dir(prefix, repo)
    second = new_run_dir(prefix, repo)
    other = new_run_dir(tmp_path / "env-other", repo)
    assert first != second != other
    assert first.is_relative_to(prefix / "tmp/native")
    assert other.is_relative_to(tmp_path / "env-other/tmp/native")
    with pytest.raises(RuntimeError):
        new_run_dir(repo, repo)
    with pytest.raises(RuntimeError):
        new_run_dir(repo / "tests/py-demo", repo)
    linked = tmp_path / "linked-env"
    linked.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (linked / "tmp").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RuntimeError):
        new_run_dir(linked, repo)
    assert list(outside.iterdir()) == []


def test_commands_target_interpreter_tools_and_wheel_without_dependency_resolution(
    tmp_path,
):
    source, run = tmp_path / "fixture", tmp_path / "run"
    pb, eigen = tmp_path / "pb", tmp_path / "eigen"
    command = build_command("/env/bin/python", source, run, PINS, pb, eigen)
    assert command[:8] == [
        "uv",
        "build",
        "--wheel",
        "--no-build-isolation",
        "--no-cache",
        "--python",
        "/env/bin/python",
        "--out-dir",
    ]
    assert f"cmake.define.pybind11_DIR={pb}" in command
    assert f"cmake.define.Eigen3_DIR={eigen}" in command
    assert "cmake.define.STUBGEN_PYBIND11_VERSION=2.9.2" in command
    assert "cmake.version===3.31.10" in command
    assert "ninja.version===1.13.2" in command
    assert f"build-dir={run / 'cmake'}" in command
    assert command[-1] == str(source)
    wheel = run / "wheel/demo.whl"
    assert install_command("/env/bin/python", wheel) == [
        "uv",
        "pip",
        "install",
        "--python",
        "/env/bin/python",
        "--no-deps",
        "--reinstall-package",
        "py-demo",
        "--no-cache",
        str(wheel),
    ]


@pytest.mark.parametrize("status", [0, 7])
def test_real_process_status_and_output_are_retained(tmp_path, status):
    command = [
        sys.executable,
        "-c",
        f"print('process-output'); raise SystemExit({status})",
    ]
    log = tmp_path / "process.log"
    if status:
        with pytest.raises(RuntimeError, match="exit 7"):
            run_logged(command, cwd=tmp_path, log=log, env=dict(os.environ))
    else:
        run_logged(command, cwd=tmp_path, log=log, env=dict(os.environ))
    lines = log.read_text().splitlines()
    assert json.loads(lines[0]) == command
    assert lines[-1] == "process-output"


def test_failed_process_diagnostics_survive_log_reread_error(tmp_path, monkeypatch):
    command = [sys.executable, "-c", "print('process-output'); raise SystemExit(7)"]
    log = tmp_path / "process.log"
    read_text = Path.read_text

    def fail_log_read(path, *args, **kwargs):
        if path == log:
            raise OSError("injected log reread failure")
        return read_text(path, *args, **kwargs)

    with monkeypatch.context() as scoped:
        scoped.setattr(Path, "read_text", fail_log_read)
        with pytest.raises(RuntimeError, match="exit 7") as caught:
            run_logged(command, cwd=tmp_path, log=log, env=dict(os.environ))
    message = str(caught.value)
    assert repr(command) in message
    assert str(log) in message
    lines = log.read_text().splitlines()
    assert json.loads(lines[0]) == command
    assert lines[-1] == "process-output"


def test_timeout_and_log_creation_failure_are_errors(tmp_path):
    with pytest.raises(RuntimeError, match="timed out"):
        run_logged(
            [sys.executable, "-c", "import time; time.sleep(2)"],
            cwd=tmp_path,
            log=tmp_path / "timeout.log",
            env=dict(os.environ),
            timeout=0.05,
        )
    assert (tmp_path / "timeout.log").is_file()
    blocked = tmp_path / "blocked.log"
    blocked.mkdir()
    sentinel = tmp_path / "ran"
    with pytest.raises(OSError):
        run_logged(
            [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(sentinel)!r}).touch()",
            ],
            cwd=tmp_path,
            log=blocked,
            env=dict(os.environ),
        )
    assert not sentinel.exists()


@pytest.mark.parametrize(
    "extra",
    [
        None,
        "lib/libdemo.a",
        "include/demo/Foo.h",
        "build/lib/stale.py",
        "demo/unrelated.txt",
    ],
)
def test_wheel_payload_is_exactly_package_extension_and_metadata(tmp_path, extra):
    package = tmp_path / "demo"
    package.mkdir()
    (package / "__init__.py").write_bytes(b"VALUE = 1\n")
    wheel = tmp_path / "fixture.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("demo/__init__.py", b"VALUE = 1\n")
        archive.writestr(
            "demo/_bindings" + EXTENSION_SUFFIXES[0], b"test payload, not imported"
        )
        archive.writestr("py_demo-0.0.0.dist-info/METADATA", b"Name: py-demo\n")
        if extra:
            archive.writestr(extra, b"unwanted")
    if extra:
        with pytest.raises(RuntimeError, match="payload"):
            audit_wheel(wheel, package)
    else:
        audit_wheel(wheel, package)
    (package / "__init__.py").write_bytes(b"VALUE = 2\n")
    with pytest.raises(RuntimeError):
        audit_wheel(wheel, package)
