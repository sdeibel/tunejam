#!/bin/bash
#
# One-time migration: move content directories from src/ to data/
#
# Run as maint on production:
#   cd /home/maint/music/src
#   ./migrate-to-data.sh
#
# This script:
#   1. Moves content directories from src/ to data/
#   2. Moves website/events and website/tokens to data/
#   3. Removes migrated files from the src git index and commits
#   4. Initializes a new git repo in data/, pushes to GitHub
#   5. Fixes permissions
#
# After running, you must manually update Apache config — the script
# prints the exact edits and commands at the end.

set -e

DATA_REPO="git@github.com:sdeibel/tunejam-data.git"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$BASE_DIR/data"
SRC_DIR="$SCRIPT_DIR"

echo "Migration: src/ content → data/"
echo "  SRC_DIR:  $SRC_DIR"
echo "  DATA_DIR: $DATA_DIR"
echo "  REPO:     $DATA_REPO"
echo ""

# ── Safety checks ─────────────────────────────────────────────

if [ -d "$DATA_DIR/db" ]; then
  echo "ERROR: $DATA_DIR/db already exists. Migration may have already run."
  exit 1
fi

if [ ! -d "$SRC_DIR/db" ]; then
  echo "ERROR: $SRC_DIR/db does not exist. Nothing to migrate."
  exit 1
fi

# ── Create data directory ─────────────────────────────────────

echo "Creating $DATA_DIR ..."
mkdir -p "$DATA_DIR"

# ── Move content directories ─────────────────────────────────

echo "Moving content directories..."

# Top-level content dirs in src/
for dir in db tunes recordings config log; do
  if [ -d "$SRC_DIR/$dir" ]; then
    echo "  mv $dir → data/$dir"
    mv "$SRC_DIR/$dir" "$DATA_DIR/$dir"
  else
    echo "  SKIP $dir (not found)"
  fi
done

# Directories under website/
for dir in events tokens; do
  if [ -d "$SRC_DIR/website/$dir" ]; then
    echo "  mv website/$dir → data/$dir"
    mv "$SRC_DIR/website/$dir" "$DATA_DIR/$dir"
  else
    echo "  SKIP website/$dir (not found)"
  fi
done

echo ""

# ── Remove migrated files from src git index and commit ───────

echo "Removing migrated files from src git index..."
cd "$SRC_DIR"
for dir in db tunes recordings config log; do
  git rm -r --cached "$dir" 2>/dev/null || true
done
for dir in website/events website/tokens; do
  git rm -r --cached "$dir" 2>/dev/null || true
done
git add -A
git commit -m "Remove migrated content directories (moved to data/ repo)"
echo ""

# ── Initialize data git repo and push ─────────────────────────

echo "Initializing git repo in $DATA_DIR ..."
cd "$DATA_DIR"
git init
cat > .gitignore << 'GITIGNORE'
.DS_Store
*.pyc
__pycache__/
GITIGNORE
git add -A
git commit -m "Initial commit: migrated content from src/"

echo ""
echo "Pushing data repo to $DATA_REPO ..."
git remote add origin "$DATA_REPO"
git push -u origin main

echo ""

# ── Fix permissions ───────────────────────────────────────────

echo "Fixing permissions..."
cd "$SRC_DIR"
"$BASE_DIR/bin/python2.7" website/fixperms.py

echo ""

# ── Done ──────────────────────────────────────────────────────

echo "=========================================="
echo "Migration complete!"
echo ""
echo "Remaining manual steps:"
echo ""
echo "  1. Push the src repo cleanup:"
echo "     cd $SRC_DIR && git push"
echo ""
echo "  2. Set up auto-commit cron:"
echo "     chmod +x $SRC_DIR/data-commit.sh"
echo "     Add to /etc/cron.hourly/musicsite.sh:"
echo "       /home/maint/music/src/data-commit.sh"
echo ""
echo "  3. Update Apache config:"
echo "     Copy the pre-edited conf files from tmp/ on your dev machine:"
echo "       scp tmp/httpd.conf      server:/etc/httpd/conf/httpd.conf"
echo "       scp tmp/httpd-le-ssl.conf server:/etc/httpd/conf/httpd-le-ssl.conf"
echo "     Then validate and reload:"
echo "       httpd -t && sudo systemctl reload httpd"
echo ""
echo "  4. Test the site — browse tunes, play a recording, create an event"
echo ""
echo "To ROLLBACK:"
echo "  cd $DATA_DIR"
echo "  for d in db tunes recordings config log; do mv \$d $SRC_DIR/; done"
echo "  for d in events tokens; do mv \$d $SRC_DIR/website/; done"
echo "  cd $SRC_DIR && git reset HEAD~1"
echo "  # Then revert Apache config changes and reload httpd"
