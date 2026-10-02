#!/bin/bash
#
# Backup/restore ignored runtime files in the sibling data/ repo.
# Sourced by deploy.sh and data-pull.sh so a data pull that drops these
# from the git tree does not wipe stamp files and logs on disk.
#
# Keep this list aligned with the runtime entries in data/.gitignore.
# config/email.conf is tracked in the data repo and is not listed here.

DATA_PRESERVE_FILES="
config/notifications.log
config/digest-last-check.txt
config/notifications-last-read.txt
config/notifications-last-sent.txt
config/books-last-regen.txt
log/logins.log
"

# Copy present preserve-files from DATA_DIR into a temp backup dir.
# Prints the backup dir path on stdout (empty if DATA_DIR is unusable).
data_preserve_backup() {
  local data_dir="$1"
  local bak rel src dest

  if [ ! -d "$data_dir" ]; then
    return 0
  fi

  bak="$(mktemp -d "${TMPDIR:-/tmp}/data-preserve.XXXXXX")"
  for rel in $DATA_PRESERVE_FILES; do
    src="$data_dir/$rel"
    if [ -f "$src" ]; then
      dest="$bak/$rel"
      mkdir -p "$(dirname "$dest")"
      cp -p "$src" "$dest"
    fi
  done
  echo "$bak"
}

# Restore backed-up files into DATA_DIR when missing after a pull/reset.
data_preserve_restore() {
  local data_dir="$1"
  local bak="$2"
  local rel src dest

  if [ ! -d "$data_dir" ]; then
    return 0
  fi

  if [ -n "$bak" ] && [ -d "$bak" ]; then
    for rel in $DATA_PRESERVE_FILES; do
      src="$bak/$rel"
      dest="$data_dir/$rel"
      if [ -f "$src" ] && [ ! -f "$dest" ]; then
        mkdir -p "$(dirname "$dest")"
        cp -p "$src" "$dest"
        echo "Restored $rel from pre-pull backup"
      fi
    done
    rm -rf "$bak"
  fi
}
