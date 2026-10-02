#!/bin/bash
#
# Push local data repo commits to origin/master.
# Run from the src/ directory (or anywhere); operates on sibling data/.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"

if [ ! -d "$DATA_DIR/.git" ]; then
  echo "data-push: $DATA_DIR is not a git repo"
  exit 1
fi

cd "$DATA_DIR"
echo "Data repo status:"
git status -sb
echo ""

if [ -n "$(git status --porcelain)" ]; then
  echo "data-push: working tree has local changes; commit or discard them first."
  exit 1
fi

ahead="$(git rev-list --count origin/master..HEAD 2>/dev/null || echo 0)"
behind="$(git rev-list --count HEAD..origin/master 2>/dev/null || echo 0)"

if [ "$behind" != "0" ]; then
  echo "data-push: local master is behind origin/master by $behind commit(s)."
  echo "Run ./data-pull.sh first, then retry."
  exit 1
fi

if [ "$ahead" = "0" ]; then
  echo "Nothing to push — already up to date with origin/master."
  exit 0
fi

echo "Pushing $ahead commit(s) to origin/master..."
git push origin master
echo "Done."
