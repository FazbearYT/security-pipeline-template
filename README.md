# Secure pipeline template

A conservative security baseline for Python, Go, and C/C++ repositories on GitHub.
It is designed to be copied into a real project and then adapted to that project's
build and dependency model.

## What is enforced

- full-history secret scanning with Gitleaks;
- Semgrep SAST with a pinned engine and current registry rules;
- Trivy dependency, secret, and IaC scanning;
- a CycloneDX SBOM retained as a workflow artifact;
- CodeQL for GitHub Actions plus detected Python, Go, and compiled C/C++ sources;
- SHA-pinned GitHub Actions, fixed runner images, explicit timeouts, read-only
  default permissions, and checkout credentials disabled;
- one stable branch-protection context: `Security / required`;
- a local repository contract that checks the same workflow invariants before push;
- weekly Dependabot updates for the Actions supply chain.

The pipeline deliberately does not create issues or rewrite branches. Findings remain
in the workflow log and CodeQL alerts, keeping the default token permissions minimal.

## Adopt the template

1. Copy `.github/`, `.gitleaks.toml`, `.gitleaksignore`, `.pre-commit-config.yaml`,
   `pyproject.toml`, both `requirements-dev*` files, `scripts/ci/`, and `tests/`.
   Clear the template-specific fingerprint lines from `.gitleaksignore` when the target
   repository does not share this template's legacy Git history.
2. Merge the ignore rules you need into the target repository's `.gitignore`.
3. In `.github/dependabot.yml`, enable only package ecosystems that have manifests.
4. For a non-standard C/C++ build, replace the CodeQL `Autobuild` step with the real
   build command. Header-only repositories are intentionally not treated as compiled C++.
5. Run the local checks from [TESTING.md](TESTING.md).
6. Push once, wait for `Security / required`, then apply branch protection with the
   platform-specific setup script. Both scripts are dry-run unless `--apply`/`-Apply`
   is supplied.

## Design boundaries

- This is a security baseline, not the project's functional CI. Keep build, unit-test,
  packaging, and release checks in the project CI and aggregate them separately.
- A green scan does not prove that software is secure. Threat modeling, review, runtime
  hardening, and incident response remain project responsibilities.
- Semgrep's `p/default` and `p/secrets` rules intentionally track current public rules. The engine,
  Actions, and runner image are pinned; rule updates are reviewed through CI behavior.
- `ignore-unfixed: true` makes Trivy's blocking gate actionable. Use scheduled reporting
  if you also want visibility into vulnerabilities that have no available fix.
- `requirements-dev.txt` contains the human-maintained direct pins;
  `requirements-dev.lock` freezes the transitive toolchain with package hashes.

See [SECURITY.md](SECURITY.md) for reporting and remediation guidance.
