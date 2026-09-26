import hashlib
import importlib.machinery
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from native_support import check_versions, require_origin

PACKAGES = (
    "numpy",
    "scipy",
    "pybind11",
    "cmake",
    "ninja",
    "scikit-build-core",
    "cmeel",
    "cmeel-eigen",
)


def expected_versions(environ) -> dict[str, str]:
    pins = {}
    for name in PACKAGES:
        key = "STUBGEN_" + name.upper().replace("-", "_") + "_VERSION"
        if not environ.get(key):
            raise RuntimeError(f"{key} must be set by tox")
        pins[name] = environ[key]
    return pins


def new_run_dir(prefix: Path, repo: Path) -> Path:
    prefix, repo = prefix.resolve(), repo.resolve()
    if repo.is_relative_to(prefix) or prefix.is_relative_to(repo / "tests"):
        raise RuntimeError("Native build prefix overlaps source roots")
    parent = prefix / "tmp/native"
    require_origin("native build directory", str(parent), prefix)
    parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=parent))


def build_command(
    python: str,
    source: Path,
    run_dir: Path,
    pins: dict[str, str],
    pybind_dir: Path,
    eigen_dir: Path,
) -> list[str]:
    command = [
        "uv",
        "build",
        "--wheel",
        "--no-build-isolation",
        "--no-cache",
        "--python",
        python,
        "--out-dir",
        str(run_dir / "wheel"),
    ]
    settings = {
        "build-dir": str(run_dir / "cmake"),
        "cmake.version": "==" + pins["cmake"],
        "ninja.version": "==" + pins["ninja"],
        "ninja.make-fallback": "false",
        "cmake.define.Python_EXECUTABLE": python,
        "cmake.define.pybind11_DIR": str(pybind_dir),
        "cmake.define.Eigen3_DIR": str(eigen_dir),
        "cmake.define.STUBGEN_PYBIND11_VERSION": pins["pybind11"],
    }
    for key, value in settings.items():
        command += ["--config-setting", f"{key}={value}"]
    return command + [str(source)]


def install_command(python: str, wheel: Path) -> list[str]:
    return [
        "uv",
        "pip",
        "install",
        "--python",
        python,
        "--no-deps",
        "--reinstall-package",
        "py-demo",
        "--no-cache",
        str(wheel),
    ]


def run_logged(
    command: list[str],
    *,
    cwd: Path,
    log: Path,
    env: dict[str, str],
    timeout: float = 600,
) -> None:
    print(f"Running {command!r}; log: {log}", flush=True)
    try:
        with log.open("xb") as stream:
            stream.write((json.dumps(command) + "\n").encode())
            stream.flush()
            result = subprocess.run(
                command,
                cwd=cwd,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Command timed out after {timeout}s; log: {log}; {command!r}"
        ) from exc
    if result.returncode:
        try:
            tail = "\n".join(log.read_text(errors="replace").splitlines()[-30:])
        except OSError as exc:
            tail = f"Could not read log tail: {exc}"
        raise RuntimeError(
            f"Command exit {result.returncode}; log: {log}; {command!r}\n{tail}"
        )


def audit_wheel(wheel: Path, package_source: Path) -> None:
    expected = {
        "demo/" + p.relative_to(package_source).as_posix(): p.read_bytes()
        for p in package_source.rglob("*.py")
    }
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or any(
            not n.startswith(("demo/", "py_demo-0.0.0.dist-info/"))
            or n.endswith((".a", ".lib", ".h", ".hpp", ".pyc"))
            for n in names
        ):
            raise RuntimeError("Unexpected fixture wheel payload")
        actual = {n: archive.read(n) for n in names if n.endswith(".py")}
        extension_names = {
            "demo/_bindings" + suffix
            for suffix in importlib.machinery.EXTENSION_SUFFIXES
        }
        extensions = [n for n in names if n in extension_names]
        payload = {n for n in names if not n.startswith("py_demo-0.0.0.dist-info/")}
        if (
            actual != expected
            or len(extensions) != 1
            or payload != set(expected) | set(extensions)
        ):
            raise RuntimeError(
                "Fixture wheel payload differs from source package/extension contract"
            )


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    source = repo / "tests/py-demo"
    run_dir = None
    evidence = {"python": sys.executable, "prefix": sys.prefix, "phase": "prepare"}
    try:
        run_dir = new_run_dir(Path(sys.prefix), repo)
        print(f"Native fixture evidence: {run_dir}", flush=True)
        pins = expected_versions(os.environ)
        before = {name: importlib.metadata.version(name) for name in PACKAGES}
        evidence.update(pins=pins, before=before)
        check_versions(pins, before)
        for name in PACKAGES:
            location = importlib.metadata.distribution(name).locate_file("")
            require_origin(name, str(location), Path(sys.prefix))
        pybind_dir = Path(
            importlib.metadata.distribution("pybind11").locate_file(
                "pybind11/share/cmake/pybind11"
            )
        )
        eigen_dir = Path(
            importlib.metadata.distribution("cmeel-eigen").locate_file(
                "cmeel.prefix/share/eigen3/cmake"
            )
        )
        for name, path, config in (
            ("pybind11", pybind_dir, "pybind11Config.cmake"),
            ("Eigen", eigen_dir, "Eigen3Config.cmake"),
        ):
            require_origin(name, str(path), Path(sys.prefix))
            if not (path / config).is_file():
                raise RuntimeError(f"Missing {name} CMake configuration: {path}")
        evidence.update(
            pins=pins,
            before=before,
            pybind_dir=str(pybind_dir),
            eigen_dir=str(eigen_dir),
        )
        env = dict(os.environ)
        for key in list(env):
            if key.startswith("SKBUILD_") or key in (
                "CMAKE_ARGS",
                "CMAKE_PREFIX_PATH",
                "CMAKE_TOOLCHAIN_FILE",
            ):
                env.pop(key)
        env["CMAKE_BUILD_PARALLEL_LEVEL"] = "2"
        evidence["phase"] = "build"
        (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        run_logged(
            build_command(sys.executable, source, run_dir, pins, pybind_dir, eigen_dir),
            cwd=repo,
            log=run_dir / "build.log",
            env=env,
        )
        wheels = list((run_dir / "wheel").glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"Expected one new fixture wheel, found {wheels}")
        wheel = wheels[0]
        evidence["phase"] = "wheel payload"
        audit_wheel(wheel, source / "demo")
        evidence.update(
            wheel=str(wheel),
            wheel_sha256=hashlib.sha256(wheel.read_bytes()).hexdigest(),
        )
        evidence["phase"] = "install"
        run_logged(
            install_command(sys.executable, wheel),
            cwd=repo,
            log=run_dir / "install.log",
            env=env,
        )
        after = {name: importlib.metadata.version(name) for name in PACKAGES}
        check_versions(pins, after)
        evidence.update(after=after, phase="complete")
        (run_dir / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        return 0
    except (
        OSError,
        RuntimeError,
        ValueError,
        importlib.metadata.PackageNotFoundError,
        zipfile.BadZipFile,
    ) as exc:
        print(f"Native fixture {evidence['phase']} failed: {exc}", file=sys.stderr)
        if run_dir is not None:
            evidence["error"] = str(exc)
            try:
                (run_dir / "evidence.json").write_text(
                    json.dumps(evidence, indent=2) + "\n"
                )
            except OSError as report_error:
                print(f"Could not save evidence: {report_error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
