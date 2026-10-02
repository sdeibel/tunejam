#!/bin/bash
#
# Pull latest data repo, discarding local changes to tracked files.
# Run from dev machine to sync with production content.
#
# Preserves ignored runtime logs/stamp files across reset.
# Recreates required empty data dirs (git clean would delete them).

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA_DIR="$(dirname "$SCRIPT_DIR")/data"

# shellcheck source=data-preserve.sh
. "$SCRIPT_DIR/data-preserve.sh"

# Writable dirs the app expects under data/ (see website/fixperms.py).
DATA_REQUIRED_DIRS="
events
events/archive
tokens
db
db/archive
tunes
tunes/archive
recordings
recordings/archive
log
config
config/publish-requests
config/editor-requests
config/profiles
config/notes
config/email-jobs
ai_cache
"

if [ ! -d "$DATA_DIR/.git" ]; then
  echo "data-pull: $DATA_DIR is not a git repo"
  exit 1
fi

echo "Fetching $DATA_DIR ..."
DATA_BAK="$(data_preserve_backup "$DATA_DIR")"
cd "$DATA_DIR"
git fetch origin

echo "Resetting to origin/master..."
git reset --hard origin/master

# Do not 'git clean -fd': it deletes required empty dirs and other
# untracked local state. Recreate the app's expected directories instead.
for rel in $DATA_REQUIRED_DIRS; do
  mkdir -p "$DATA_DIR/$rel"
done

data_preserve_restore "$DATA_DIR" "$DATA_BAK"
echo "Done. data/ is at $(git rev-parse --short HEAD) (matches origin/master)."
