#!/usr/bin/env bash
set -Eeuo pipefail

APPLY=false
ALLOW_DIRECT_PUSH=false
ALLOW_ADMIN_BYPASS=false
INTEGRATION_BRANCH=""

while (($#)); do
  case "$1" in
    --apply) APPLY=true ;;
    --allow-direct-push) ALLOW_DIRECT_PUSH=true ;;
    --allow-admin-bypass) ALLOW_ADMIN_BYPASS=true ;;
    --integration-branch)
      shift
      [[ $# -gt 0 ]] || { echo "--integration-branch requires a value" >&2; exit 2; }
      INTEGRATION_BRANCH="$1"
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v gh >/dev/null || { echo "GitHub CLI is required" >&2; exit 1; }
git rev-parse --is-inside-work-tree >/dev/null
gh auth status >/dev/null

REPOSITORY=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef --jq .defaultBranchRef.name)
BRANCHES=("$DEFAULT_BRANCH")
if [[ -n "$INTEGRATION_BRANCH" && "$INTEGRATION_BRANCH" != "$DEFAULT_BRANCH" ]]; then
  BRANCHES+=("$INTEGRATION_BRANCH")
fi

echo "Repository: $REPOSITORY"
echo "Branches: ${BRANCHES[*]}"
echo "Required check: Security / required"
if $APPLY; then echo "Mode: APPLY"; else echo "Mode: DRY RUN"; fi

for branch in "${BRANCHES[@]}"; do
  gh api "repos/$REPOSITORY/branches/$branch" >/dev/null \
    || { echo "Remote branch does not exist: $branch" >&2; exit 1; }

  reviews='{"required_approving_review_count":0,"dismiss_stale_reviews":true}'
  if $ALLOW_DIRECT_PUSH; then
    reviews=null
  fi
  enforce_admins=true
  if $ALLOW_ADMIN_BYPASS; then
    enforce_admins=false
  fi
  payload=$(printf '{"required_status_checks":{"strict":true,"contexts":["Security / required"]},"enforce_admins":%s,"required_pull_request_reviews":%s,"restrictions":null,"allow_force_pushes":false,"allow_deletions":false}' "$enforce_admins" "$reviews")

  if $APPLY; then
    printf '%s' "$payload" | gh api --method PUT "repos/$REPOSITORY/branches/$branch/protection" --input - >/dev/null
    echo "Protected: $branch"
  else
    echo "Would protect: $branch"
  fi
done

if $APPLY; then
  gh api --method PUT "repos/$REPOSITORY/vulnerability-alerts" >/dev/null
  gh api --method PUT "repos/$REPOSITORY/automated-security-fixes" >/dev/null
  echo "Dependabot alerts and automated security fixes enabled."
else
  echo "No remote state changed. Re-run with --apply after the first green workflow."
fi
