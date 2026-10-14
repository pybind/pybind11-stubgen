import json
import subprocess
import sys
from pathlib import Path

import pytest

from native_matrix import matrix_from_names

EXPECTED_NAMES = [
    "py310-pb30",
    "py311-pb30",
    "py312-pb30",
    "py313-pb30",
    "py310-pb213",
    "py311-pb213",
    "py312-pb213",
    "py313-pb213",
    "py313-pb29",
    "py313-pb211",
    "py313-pb212",
]


def test_explicit_profile_inventory_and_interpreters():
    matrix = matrix_from_names(EXPECTED_NAMES)
    assert matrix == {
        "include": [
            {"env": "py310-pb30", "python": "3.10"},
            {"env": "py311-pb30", "python": "3.11"},
            {"env": "py312-pb30", "python": "3.12"},
            {"env": "py313-pb30", "python": "3.13"},
            {"env": "py310-pb213", "python": "3.10"},
            {"env": "py311-pb213", "python": "3.11"},
            {"env": "py312-pb213", "python": "3.12"},
            {"env": "py313-pb213", "python": "3.13"},
            {"env": "py313-pb29", "python": "3.13"},
            {"env": "py313-pb211", "python": "3.13"},
            {"env": "py313-pb212", "python": "3.13"},
        ]
    }


@pytest.mark.parametrize(
    "names",
    [
        [],
        ["py313-pb30"] * 2,
        ["py313-unit"],
        ["py39-pb30"],
        ["py313-pb99"],
        ["py313-pb30-naa"],
        ["py313-pb300"],
        ["py313-pb209"],
        [""],
        [" py313-pb30"],
    ],
)
def test_rejects_missing_duplicate_or_unsupported_profiles(names):
    with pytest.raises(ValueError):
        matrix_from_names(names)


def test_cli_json_and_nonzero_failure(tmp_path):
    script = Path(__file__).resolve().parents[1] / "native_matrix.py"
    names = tmp_path / "names.txt"
    names.write_text("py313-pb30\n")
    result = subprocess.run(
        [sys.executable, str(script), str(names)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == '{"include":[{"env":"py313-pb30","python":"3.13"}]}\n'
    assert json.loads(result.stdout) == {
        "include": [{"env": "py313-pb30", "python": "3.13"}]
    }
    names.write_text("py313-pb30\npy313-pb30\n")
    result = subprocess.run(
        [sys.executable, str(script), str(names)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "Duplicate" in result.stderr
