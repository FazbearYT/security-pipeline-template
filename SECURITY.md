# Security policy

## Reporting a vulnerability

Use GitHub private vulnerability reporting when it is enabled. Otherwise contact the
repository owner privately. Do not open a public issue containing an exploit, secret,
personal data, or an unpatched vulnerability.

Include the affected revision, impact, reproduction steps, and any proposed mitigation.
Do not include live credentials. The maintainer should acknowledge the report, assess
severity, prepare a fix, and coordinate disclosure before publishing details.

## Secret exposure response

Treat a committed credential as compromised even if the commit was never merged:

1. revoke or rotate it at the issuing service;
2. remove it from the current tree;
3. assess Git history, workflow logs, caches, artifacts, forks, and releases;
4. rewrite history only after coordinating with every clone and protected branch;
5. rerun the full-history scan and document the incident without copying the secret.

Deleting the current file or closing an alert does not invalidate the credential.

## Pipeline trust model

The template uses least-privilege workflow permissions, immutable Action SHAs,
`persist-credentials: false`, fixed runner versions, explicit job timeouts, and a single
required result. Dependency and Action updates must arrive through reviewed pull requests.

Repositories adopting this template must also protect their stable branches, require the
`Security / required` context, prevent force pushes and deletion, and add functional CI
checks appropriate to the application. Release workflows need a separate threat model and
must not inherit write permissions from this scanning workflow.
