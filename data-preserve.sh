#!/bin/bash
#
# Backup/restore ignored runtime files in the sibling data/ repo.
# Sourced by deploy.sh and data-pull.sh so a data pull that drops these
# from the git tree does not wipe live secrets and stamp files on disk.
#
# Keep this list aligned with the runtime entries in data/.gitignore.

DATA_PRESERVE_FILES="
config/email.conf
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
# Falls back to the last git revision that still had email.conf if needed.
data_preserve_restore() {
  local data_dir="$1"
  local bak="$2"
  local rel src dest del_commit

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

  # Last-resort recovery for the SMTP secret if backup was empty/missing.
  if [ ! -f "$data_dir/config/email.conf" ] && [ -d "$data_dir/.git" ]; then
    del_commit="$(git -C "$data_dir" log -1 --diff-filter=D --format=%H -- config/email.conf 2>/dev/null || true)"
    if [ -n "$del_commit" ]; then
      mkdir -p "$data_dir/config"
      if git -C "$data_dir" show "${del_commit}^:config/email.conf" > "$data_dir/config/email.conf" 2>/dev/null; then
        echo "Restored config/email.conf from git history (${del_commit}^)"
      else
        rm -f "$data_dir/config/email.conf"
      fi
    fi
  fi
}
