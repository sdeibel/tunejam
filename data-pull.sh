#!/bin/bash
#
# Pull latest data repo, discarding any local changes.
# Run from dev machine to sync with production content.

DATA_DIR="$(dirname "$(cd "$(dirname "$0")" && pwd)")/data"

if [ ! -d "$DATA_DIR/.git" ]; then
  echo "data-pull: $DATA_DIR is not a git repo"
  exit 1
fi

cd "$DATA_DIR"
echo "Resetting $DATA_DIR to match remote..."
git fetch origin
git reset --hard origin/master
git clean -fd
echo "Done."
