from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "ci" / "validate_repository.py"
SPEC = importlib.util.spec_from_file_location("validate_repository", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class WorkflowValidationTests(unittest.TestCase):
    def validate(self, workflow: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "workflow.yml"
            path.write_text(workflow, encoding="utf-8")
            return VALIDATOR.validate_workflow(path)

    def test_accepts_sha_pinned_hardened_checkout(self) -> None:
        errors = self.validate(
            """jobs:
  check:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
        with:
          persist-credentials: false
"""
        )
        self.assertEqual(errors, [])

    def test_rejects_moving_action_and_runner(self) -> None:
        errors = self.validate(
            """jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v7
        with:
          persist-credentials: false
"""
        )
        self.assertTrue(any("moving runner" in error for error in errors))
        self.assertTrue(any("not pinned" in error for error in errors))

    def test_rejects_checkout_credentials(self) -> None:
        errors = self.validate(
            """jobs:
  check:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@0123456789abcdef0123456789abcdef01234567
"""
        )
        self.assertTrue(any("persist-credentials" in error for error in errors))

    def test_rejects_pull_request_target(self) -> None:
        errors = self.validate(
            """on:
  pull_request_target:
jobs:
  check:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps: []
"""
        )
        self.assertTrue(any("pull_request_target" in error for error in errors))


class ToolConfigValidationTests(unittest.TestCase):
    def test_requires_gitleaks_default_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitleaks.toml").write_text('title = "custom only"\n', encoding="utf-8")
            errors = VALIDATOR.validate_tool_configs(root)
        self.assertTrue(any("built-in detector" in error for error in errors))

    def test_rejects_broad_gitleaks_ignore_entries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".gitleaksignore").write_text("tests/fixtures/.*\n", encoding="utf-8")
            errors = VALIDATOR.validate_tool_configs(root)
        self.assertTrue(any("exact fingerprint" in error for error in errors))

    def test_requires_pre_commit_sha_pins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".pre-commit-config.yaml").write_text(
                "repos:\n  - repo: https://example.invalid/hooks\n    rev: v1.0.0\n",
                encoding="utf-8",
            )
            errors = VALIDATOR.validate_tool_configs(root)
        self.assertTrue(any("pre-commit repository" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
