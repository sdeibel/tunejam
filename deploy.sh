#!/bin/bash
#
# Deploy script for music.cambridgeny.net
# Run as maint user on production server from the src/ directory.
# Does git pull then fixes permissions via fixperms.py.
#
# IMPORTANT: When adding new writable data directories, update
# DATA_DIRS in website/fixperms.py (the single source of truth).

set -e

TEST_MODE=false
if [ "$1" = "--test" ]; then
  TEST_MODE=true
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Git pull ──────────────────────────────────────────────────

if [ "$TEST_MODE" = true ]; then
  echo "# Would run: git pull"
else
  echo "Pulling latest changes..."
  old_hash="$(md5sum deploy.sh 2>/dev/null || md5 -q deploy.sh 2>/dev/null)"
  git pull
  new_hash="$(md5sum deploy.sh 2>/dev/null || md5 -q deploy.sh 2>/dev/null)"
  if [ "$old_hash" != "$new_hash" ] && [ "${DEPLOY_RESTARTED:-}" != "1" ]; then
    echo "deploy.sh was updated — restarting..."
    DEPLOY_RESTARTED=1 exec "$0" "$@"
  fi
fi
echo ""

# ── Fix permissions ───────────────────────────────────────────

if [ "$TEST_MODE" = true ]; then
  /home/maint/music/bin/python2.7 website/fixperms.py --test
else
  /home/maint/music/bin/python2.7 website/fixperms.py
fi

echo ""
echo "Deploy complete."
