#!/home/maint/music/bin/python2.7

# Fix group ownership and permissions on all data directories.
#
# Directories: apache group, mode 2775 (setgid so new files inherit group)
# Files: apache group, mode 0664
#
# Called from deploy.sh after git pull and from crontask.py for periodic
# fixes.  Can also be run standalone.
#
# When running as root (e.g., from cron), commands run directly.
# When running as a regular user (e.g., from deploy.sh), uses sudo.
#
# IMPORTANT: Update DATA_DIRS below whenever new writable data directories
# are added to the application.

import os
import sys

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(SRC_DIR), 'data')

# Directories under src/ that apache needs to write to
SRC_DATA_DIRS = [
  'website/cache',
  'website/cache/tune',
  'website/cache/tuneset',
  'website/cache/book',
  'website/css',
]

# Directories under data/ that apache needs to write to
DATA_DATA_DIRS = [
  'events',
  'events/archive',
  'tokens',
  'db',
  'db/archive',
  'tunes',
  'tunes/archive',
  'recordings',
  'recordings/archive',
  'log',
  'config',
  'config/publish-requests',
  'config/editor-requests',
  'config/profiles',
  'config/notes',
  'config/email-jobs',
]

def fix(log=True, dry_run=False):
  """Fix group ownership and permissions on all data directories and files."""
  if sys.platform == 'darwin':
    if log:
      print("Skipping permission fix on macOS")
    return

  dirs = ([os.path.join(SRC_DIR, d) for d in SRC_DATA_DIRS] +
          [os.path.join(DATA_DIR, d) for d in DATA_DATA_DIRS])
  sudo = '' if os.geteuid() == 0 else 'sudo '

  def run(cmd):
    if dry_run:
      print("  %s" % cmd)
    else:
      os.system(cmd)

  # Create missing directories and fix directory permissions
  if log and not dry_run:
    print("Fixing directory permissions...")
  run(sudo + 'mkdir -p ' + ' '.join(dirs))
  run(sudo + 'chgrp apache ' + ' '.join(dirs))
  run(sudo + 'chmod 2775 ' + ' '.join(dirs))

  # Fix file permissions (only touches files that need it)
  if log and not dry_run:
    print("Fixing file permissions...")
  for d in dirs:
    run('find %s -maxdepth 1 -type f '
        '\\( ! -group apache -o ! -perm -g+rw \\) -print0 2>/dev/null | '
        'xargs -0 -r %ssh -c \'chgrp apache "$@" && chmod 664 "$@"\' _' % (d, sudo))

  if log and not dry_run:
    print("Permissions fixed.")

if __name__ == '__main__':
  dry_run = '--test' in sys.argv
  if dry_run:
    print("# Permission fix commands:")
  fix(log=True, dry_run=dry_run)
