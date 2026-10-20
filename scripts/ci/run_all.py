"""Run the template's deterministic local/CI verification from one command."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(root: Path, *command: str) -> None:
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(f"required command is not installed: {command[0]}")
    rendered = " ".join(command)
    print(f"+ {rendered}", flush=True)
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    environment["PYTHONUTF8"] = "1"
    subprocess.run(  # noqa: S603 - resolved executable and fixed project commands
        [executable, *command[1:]],
        cwd=root,
        check=True,
        env=environment,
    )


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    python = sys.executable
    run(root, python, "scripts/ci/validate_repository.py")
    run(root, python, "-m", "unittest", "discover", "-s", "tests", "-v")
    run(root, "ruff", "check", "scripts", "tests")
    run(root, "ruff", "format", "--check", "scripts", "tests")
    run(root, "zizmor", ".github/workflows")
    print("All deterministic template checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
