#!/bin/bash
#
# Push, deploy to production, and pull data back to dev.
# Run from dev machine from the src/ directory.
#
# Steps:
#   1. git push (dev)
#   2. ssh to server and run deploy.sh (git pull + fix permissions)
#   3. data-pull.sh (sync production data back to dev)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SERVER="maint@cambridgeny.net"
REMOTE_SRC="/home/maint/music/src"

# ── Push local changes ────────────────────────────────────────

echo "Pushing to origin..."
git push
echo ""

# ── Deploy on server ──────────────────────────────────────────

echo "Deploying on server..."
ssh -t -A "$SERVER" "cd $REMOTE_SRC && ./deploy.sh"
echo ""

# ── Pull data back to dev ────────────────────────────────────

echo "Pulling production data to dev..."
"$SCRIPT_DIR/data-pull.sh"
