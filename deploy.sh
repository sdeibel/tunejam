#!/bin/bash
#
# Deploy script for music.cambridgeny.net
# Run as maint user on production server from the src/ directory.
# Does git pull then fixes permissions on data directories that
# apache needs to write to.
#
# IMPORTANT: Update DATA_DIRS below whenever new writable data
# directories are added to the application.

set -e

TEST_MODE=false
if [ "$1" = "--test" ]; then
  TEST_MODE=true
fi

run() {
  if [ "$TEST_MODE" = true ]; then
    echo "  $*"
  else
    "$@"
  fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── Git pull ──────────────────────────────────────────────────

if [ "$TEST_MODE" = true ]; then
  echo "# Would run: git pull"
else
  echo "Pulling latest changes..."
  git pull
fi
echo ""

# ── Data directory permissions ────────────────────────────────
#
# Directories the web app writes to at runtime.  Group 'apache'
# includes both maint and apache users.  We need:
#   - directories: owned by maint:apache, mode 2775 (setgid so
#     new files inherit the group)
#   - files: owned by maint:apache, mode 0664
#
# Only invoke sudo if something actually needs fixing.

DATA_DIRS=(
  # PDF cache
  website/cache
  website/cache/tune
  website/cache/tuneset
  website/cache/book

  # User/event data
  website/saved-sets
  website/events
  website/events/archive
  website/tokens

  # Tune database (create/edit/archive)
  db
  db/archive
  tunes
  tunes/archive
  recordings
  recordings/archive

  # Logs
  log

  # Config and user data
  config
  config/publish-requests
  config/editor-requests
  config/profiles
  config/notes
)

needs_fix=false

for dir in "${DATA_DIRS[@]}"; do
  # Create missing directories
  if [ ! -d "$dir" ]; then
    needs_fix=true
    break
  fi
  # Check group ownership
  if [ "$(stat -c '%G' "$dir" 2>/dev/null || stat -f '%Sg' "$dir" 2>/dev/null)" != "apache" ]; then
    needs_fix=true
    break
  fi
  # Check setgid + group-writable on directory
  perms="$(stat -c '%a' "$dir" 2>/dev/null || stat -f '%OLp' "$dir" 2>/dev/null)"
  if [ "$perms" != "2775" ]; then
    needs_fix=true
    break
  fi
done

if [ "$needs_fix" = true ] || [ "$TEST_MODE" = true ]; then
  if [ "$TEST_MODE" = true ]; then
    echo "# Directory permissions commands:"
  else
    echo "Fixing data directory permissions (sudo required)..."
  fi
  for dir in "${DATA_DIRS[@]}"; do
    run sudo mkdir -p "$dir"
    run sudo chgrp apache "$dir"
    run sudo chmod 2775 "$dir"
  done
  if [ "$TEST_MODE" != true ]; then
    echo "Directory permissions fixed."
  fi
else
  echo "Data directory permissions OK."
fi

# Fix file permissions — always check since git pull can introduce files
# with wrong group/perms even when directories are already correct.
# xargs -r avoids invoking sudo when find matches nothing.
if [ "$TEST_MODE" = true ]; then
  echo ""
  echo "# File permissions commands (for files with wrong group/perms):"
fi
files_fixed=false
for dir in "${DATA_DIRS[@]}"; do
  if [ -d "$dir" ] || [ "$TEST_MODE" = true ]; then
    if [ "$TEST_MODE" = true ]; then
      echo "  find $dir -maxdepth 1 -type f \\( ! -group apache -o ! -perm -g+rw \\) -exec sudo chgrp apache {} + -exec sudo chmod 664 {} +"
    else
      bad_files="$(find "$dir" -maxdepth 1 -type f \( ! -group apache -o ! -perm -g+rw \) -print -quit 2>/dev/null)"
      if [ -n "$bad_files" ]; then
        if [ "$files_fixed" = false ]; then
          echo "Fixing file permissions..."
          files_fixed=true
        fi
        find "$dir" -maxdepth 1 -type f \( ! -group apache -o ! -perm -g+rw \) -print0 2>/dev/null | \
          xargs -0 -r sudo sh -c 'chgrp apache "$@" && chmod 664 "$@"' _
      fi
    fi
  fi
done
if [ "$TEST_MODE" != true ]; then
  if [ "$files_fixed" = true ]; then
    echo "File permissions fixed."
  else
    echo "File permissions OK."
  fi
fi

echo ""
echo "Deploy complete."
