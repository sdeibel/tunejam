#!/bin/bash
#
# Auto-commit and push changes in the data/ repo.
# Add to /etc/cron.hourly/musicsite.sh alongside crontask.py.
#
# Usage:
#   ./data-commit.sh          # commit and push if changes exist
#   ./data-commit.sh --test   # dry run (show what would happen)

DATA_DIR="$(dirname "$(cd "$(dirname "$0")" && pwd)")/data"

if [ ! -d "$DATA_DIR/.git" ]; then
  echo "data-commit: $DATA_DIR is not a git repo, skipping"
  exit 0
fi

cd "$DATA_DIR"

# Check for any changes (staged, unstaged, or untracked)
if git diff --quiet HEAD 2>/dev/null && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  exit 0
fi

if [ "$1" = "--test" ]; then
  echo "data-commit: would commit changes in $DATA_DIR:"
  git status --short
  exit 0
fi

git add -A
git commit -m "Auto-commit $(date '+%Y-%m-%d %H:%M')"
git push origin main 2>/dev/null || echo "data-commit: push failed (will retry next run)"
