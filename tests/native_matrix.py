import argparse
import json
import re
import sys
from pathlib import Path

from snapshot_helpers import BRANCHES


def matrix_from_names(names: list[str]) -> dict[str, list[dict[str, str]]]:
    if not names:
        raise ValueError("No default native environments")
    if len(names) != len(set(names)):
        raise ValueError("Duplicate native environments")
    rows = []
    for name in names:
        match = re.fullmatch(r"py(3)(1[0-3])-pb([23])(0|[1-9]\d?)", name)
        if match is None or f"v{match[3]}.{int(match[4])}" not in BRANCHES:
            raise ValueError(f"Unsupported native environment: {name!r}")
        rows.append({"env": name, "python": f"{match[1]}.{match[2]}"})
    return {"include": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("names_file", type=Path)
    args = parser.parse_args()
    try:
        matrix = matrix_from_names(args.names_file.read_text().splitlines())
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(matrix, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
