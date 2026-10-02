#!/bin/bash
#
# Pull latest data repo, discarding any local changes.
# Run from dev machine to sync with production content.
# Preserves ignored runtime files (email.conf, logs, stamp files)
# across reset/clean so secrets are not wiped.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"

# shellcheck source=data-preserve.sh
. "$SCRIPT_DIR/data-preserve.sh"

if [ ! -d "$DATA_DIR/.git" ]; then
  echo "data-pull: $DATA_DIR is not a git repo"
  exit 1
fi

echo "Resetting $DATA_DIR to match remote..."
DATA_BAK="$(data_preserve_backup "$DATA_DIR")"
cd "$DATA_DIR"
git fetch origin
git reset --hard origin/master
git clean -fd
data_preserve_restore "$DATA_DIR" "$DATA_BAK"
echo "Done."
