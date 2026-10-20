"""Validate the security invariants that make this template trustworthy."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ACTION_USE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
FULL_SHA_ACTION = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
MOVING_RUNNER = re.compile(r"^\s*runs-on:\s*\S+-latest\s*$", re.MULTILINE)
CONFLICT_MARKER = re.compile(r"^(?:<{7}(?: .*)?|={7}|>{7}(?: .*)?)$", re.MULTILINE)
PRIVATE_KEY = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
GITHUB_TOKEN = re.compile(r"\b(?:gh[opsu]_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{50,})\b")
TELEGRAM_TOKEN = re.compile(r"(?<![A-Za-z0-9_-])\d{8,12}:[A-Za-z0-9_-]{30,}")
PRE_COMMIT_REV = re.compile(r"^\s*rev:\s*([^\s#]+)", re.MULTILINE)
GITLEAKS_FINGERPRINT = re.compile(r"^[0-9a-f]{40}:.+:[a-z0-9-]+:\d+$")

REQUIRED_FILES = {
    ".github/dependabot.yml",
    ".github/workflows/security.yml",
    ".gitleaksignore",
    ".gitleaks.toml",
    ".pre-commit-config.yaml",
    "README.md",
    "requirements-dev.lock",
    "SECURITY.md",
}
FORBIDDEN_EXACT = {".env", ".npmrc", ".pypirc", "id_rsa", "id_ed25519"}
FORBIDDEN_SUFFIXES = (".key", ".pem", ".p12", ".pfx")
TEXT_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".go",
    ".h",
    ".hpp",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def tracked_files(root: Path) -> list[str]:
    git = shutil.which("git")
    if git is None:
        raise RuntimeError("git is required to validate tracked repository content")
    result = subprocess.run(  # noqa: S603 - resolved executable and fixed arguments
        [git, "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def validate_workflow(path: Path) -> list[str]:
    relative = path.as_posix()
    content = path.read_text(encoding="utf-8")
    errors: list[str] = []

    if "pull_request_target:" in content:
        errors.append(f"unsafe pull_request_target trigger: {relative}")
    if re.search(r"^\s*permissions:\s*(?:write-all|read-all)\s*$", content, re.MULTILINE):
        errors.append(f"broad permissions shortcut: {relative}")
    if MOVING_RUNNER.search(content):
        errors.append(f"moving runner label: {relative}")
    if "timeout-minutes:" not in content:
        errors.append(f"workflow jobs need explicit timeouts: {relative}")

    for action in ACTION_USE.findall(content):
        if action.startswith("./"):
            continue
        if not FULL_SHA_ACTION.fullmatch(action):
            errors.append(f"GitHub Action is not pinned to a full SHA: {action} in {relative}")

    checkout_count = len(re.findall(r"uses:\s*actions/checkout@", content))
    credential_hardening_count = len(
        re.findall(r"^\s*persist-credentials:\s*false\s*$", content, re.MULTILINE)
    )
    if checkout_count != credential_hardening_count:
        errors.append(
            f"every checkout must set persist-credentials: false in {relative} "
            f"({checkout_count} checkouts, {credential_hardening_count} hardened)"
        )
    return errors


def validate_tool_configs(root: Path) -> list[str]:
    errors: list[str] = []
    gitleaks = root / ".gitleaks.toml"
    if gitleaks.is_file():
        content = gitleaks.read_text(encoding="utf-8")
        if "[extend]" not in content or not re.search(
            r"^\s*useDefault\s*=\s*true\s*$", content, re.MULTILINE
        ):
            errors.append(".gitleaks.toml must extend the built-in detector rules")

    ignore = root / ".gitleaksignore"
    if ignore.is_file():
        for line_number, line in enumerate(ignore.read_text(encoding="utf-8").splitlines(), 1):
            value = line.strip()
            if value and not value.startswith("#") and not GITLEAKS_FINGERPRINT.fullmatch(value):
                errors.append(f".gitleaksignore:{line_number}: expected an exact fingerprint")

    pre_commit = root / ".pre-commit-config.yaml"
    if pre_commit.is_file():
        content = pre_commit.read_text(encoding="utf-8")
        for revision in PRE_COMMIT_REV.findall(content):
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                errors.append(f"pre-commit repository is not pinned to a full SHA: {revision}")
    return errors


def validate_repository(root: Path, paths: list[str] | None = None) -> list[str]:
    root = root.resolve()
    normalized = sorted(path.replace("\\", "/") for path in (paths or tracked_files(root)))
    tracked = set(normalized)
    errors: list[str] = []

    for required in sorted(REQUIRED_FILES - tracked):
        errors.append(f"required security file is missing or untracked: {required}")

    for relative in normalized:
        lowered = relative.lower()
        name = Path(lowered).name
        if name in FORBIDDEN_EXACT or lowered.endswith(FORBIDDEN_SUFFIXES):
            errors.append(f"forbidden credential-like tracked file: {relative}")
            continue

        absolute = root / relative
        if absolute.suffix.lower() not in TEXT_SUFFIXES or not absolute.is_file():
            continue
        try:
            content = absolute.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"expected UTF-8 text file: {relative}")
            continue

        if CONFLICT_MARKER.search(content):
            errors.append(f"unresolved merge marker: {relative}")
        if relative not in {".gitleaks.toml", ".secrets.baseline"}:
            if PRIVATE_KEY.search(content):
                errors.append(f"possible private key: {relative}")
            if GITHUB_TOKEN.search(content):
                errors.append(f"possible GitHub token: {relative}")
            if TELEGRAM_TOKEN.search(content):
                errors.append(f"possible Telegram token: {relative}")

    workflows = sorted((root / ".github" / "workflows").glob("*.y*ml"))
    if not workflows:
        errors.append("no GitHub Actions workflows found")
    for workflow in workflows:
        errors.extend(validate_workflow(workflow))
    errors.extend(validate_tool_configs(root))

    security = root / ".github" / "workflows" / "security.yml"
    if security.is_file():
        content = security.read_text(encoding="utf-8")
        if "name: Security / required" not in content:
            errors.append("stable required-check job is missing: Security / required")
        if "if: always()" not in content:
            errors.append("required-check aggregator must run with if: always()")
        if "permissions:\n  contents: read" not in content:
            errors.append("security workflow must default to contents: read")

    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    errors = validate_repository(root)
    if errors:
        print("Repository security contract failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Repository security contract passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
