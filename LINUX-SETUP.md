# Linux and macOS setup

Requirements: Git, Python 3.10+, GitHub CLI authenticated with `gh auth login`, and a
repository already pushed to GitHub.

```bash
python3 -m pip install --require-hashes --requirement requirements-dev.lock
pre-commit install
pre-commit run --all-files
python3 scripts/ci/run_all.py
```

After the first green GitHub run, preview branch protection:

```bash
bash scripts/setup-repo.sh
```

Apply it to the default branch, optionally adding an integration branch:

```bash
bash scripts/setup-repo.sh --apply
bash scripts/setup-repo.sh --apply --integration-branch develop
```

The default requires a pull request with zero approvals and applies protection to
administrators. Use `--allow-direct-push` or `--allow-admin-bypass` only as explicit escape
hatches. The script never creates or switches branches.
