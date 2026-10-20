# Testing the template

## Fast local verification

Python 3.10 or newer is sufficient for the template's own checks:

```shell
python scripts/ci/run_all.py
```

The runner executes the repository contract, unit tests, Ruff, and Zizmor. The validator
fails on unpinned Actions, moving runner labels, unsafe
`pull_request_target`, checkout credentials, missing timeouts, credential-like tracked
files, merge markers, and the absence of the stable `Security / required` job.

## Pre-commit

```shell
python -m pip install --require-hashes --requirement requirements-dev.lock
pre-commit install
pre-commit run --all-files
```

Python and C/C++ hooks only run when matching files exist. The Go hooks require a local
Go toolchain and only run when Go files are present.

## Workflow audit

The pinned development dependency includes Zizmor:

```shell
zizmor .github/workflows/security.yml
```

Before enabling branch protection, push to a disposable branch and verify all jobs.
The final job must be exactly `Security / required`. A skipped CodeQL matrix is expected
when the repository has no supported source files; all other jobs must succeed.

## Safe negative test

Do not commit a real credential. To exercise the secret scanner, create a disposable
branch and use one of Gitleaks' documented synthetic test values, verify that the run
fails, then delete the branch. Never put a live token into Git, even briefly.
