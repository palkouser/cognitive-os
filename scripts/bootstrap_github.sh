#!/usr/bin/env bash
set -euo pipefail

repo="palkouser/cognitive-os"
milestone="Sprint 0 – Project Foundation"

if [[ "${1:-}" != "--apply" ]]; then
  printf 'This script creates GitHub labels, a milestone, and historical issues.\n'
  printf 'Run %s --apply after the first manual push and green CI.\n' "$0"
  exit 2
fi

command -v gh >/dev/null || { printf 'gh is required\n' >&2; exit 1; }
gh auth status
gh repo view "$repo" >/dev/null

create_label() {
  gh label create "$1" --repo "$repo" --color "$2" --description "$3" --force
}

create_label "sprint:0" "5319E7" "Sprint 0 project foundation"
create_label "sprint:1" "7057FF" "Sprint 1 runtime minimization"
create_label "type:setup" "0E8A16" "Setup and environment"
create_label "type:docs" "0075CA" "Documentation"
create_label "type:test" "BFDADC" "Tests"
create_label "type:security" "D93F0B" "Security"
create_label "type:ci" "FBCA04" "Continuous integration"
create_label "area:upstream" "C5DEF5" "Upstream integration"
create_label "area:tooling" "1D76DB" "Developer tooling"
create_label "priority:p0" "B60205" "Critical priority"
create_label "priority:p1" "D93F0B" "High priority"
create_label "blocked" "000000" "Blocked"

milestone_number="$(gh api "repos/$repo/milestones?state=all" \
  | jq -r --arg title "$milestone" '.[] | select(.title == $title) | .number' \
  | head -n 1)"
if [[ -z "$milestone_number" ]]; then
  milestone_number="$(gh api --method POST "repos/$repo/milestones" \
    -f title="$milestone" \
    -f description="Reproducible and documented Cognitive OS development foundation." \
    -f state="open" --jq '.number')"
fi

issues=(
  "S0-00 – Verify machine and storage baseline"
  "S0-01 – Install required host tools"
  "S0-02 – Configure Python 3.12 and uv"
  "S0-03 – Create LightAgent baseline and repository remotes"
  "S0-04 – Establish project and data directories"
  "S0-05 – Configure VS Code workspace"
  "S0-06 – Configure Codex project instructions"
  "S0-07 – Establish license and donor policy"
  "S0-08 – Create ADR system and initial decisions"
  "S0-09 – Establish dependency baseline"
  "S0-10 – Run baseline smoke and regression tests"
  "S0-11 – Establish quality and security baseline"
  "S0-12 – Create GitHub Actions CI"
  "S0-13 – Create GitHub planning metadata"
  "S0-14 – Close and tag Sprint 0 baseline"
)

for title in "${issues[@]}"; do
  number="$(gh issue list --repo "$repo" --state all --limit 100 --json number,title \
    | jq -r --arg title "$title" '.[] | select(.title == $title) | .number' | head -n 1)"
  if [[ -z "$number" ]]; then
    url="$(gh issue create --repo "$repo" --title "$title" \
      --body "Completed before the first remote publication. Evidence is stored under docs/baseline." \
      --label "sprint:0,type:setup" --milestone "$milestone")"
    number="${url##*/}"
  fi
  if [[ "$title" != "S0-14 – Close and tag Sprint 0 baseline" ]]; then
    gh issue close "$number" --repo "$repo" \
      --comment "Completed and documented in the Sprint 0 baseline." >/dev/null
  fi
done

carry_title="Restore editable installation and normalize package layout"
carry_number="$(gh issue list --repo "$repo" --state all --limit 100 --json number,title \
  | jq -r --arg title "$carry_title" '.[] | select(.title == $title) | .number' | head -n 1)"
if [[ -z "$carry_number" ]]; then
  gh issue create --repo "$repo" --title "$carry_title" \
    --body-file docs/sprints/sprint-01/carry-over.md \
    --label "sprint:1,area:upstream,priority:p1"
fi

printf 'GitHub Sprint 0 metadata bootstrap complete. Milestone: %s\n' "$milestone_number"
