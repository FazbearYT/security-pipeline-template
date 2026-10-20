# Windows setup

Requirements: Git, Python 3.10+, GitHub CLI authenticated with `gh auth login`, and a
repository already pushed to GitHub.

```powershell
py -3 -m pip install --require-hashes --requirement requirements-dev.lock
pre-commit install
pre-commit run --all-files
python scripts/ci/run_all.py
```

After the first green GitHub run, preview branch protection:

```powershell
.\scripts\setup-repo.ps1
```

Apply it to the default branch:

```powershell
.\scripts\setup-repo.ps1 -Apply
```

To protect an additional integration branch:

```powershell
.\scripts\setup-repo.ps1 -IntegrationBranch develop -Apply
```

The script never creates or switches branches. It requires `Security / required`, requires
a pull request (zero approvals, suitable for a solo repository), blocks force pushes and
deletion, applies protection to administrators, and enables Dependabot alerts. The explicit
escape hatches are `-AllowDirectPush` and `-AllowAdminBypass`.
