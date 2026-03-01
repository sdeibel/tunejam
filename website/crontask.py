#!/home/maint/music/bin/python2.7

# Crontasks for the CGI production version of the website
#
# Designed to run hourly via /etc/cron.hourly/musicsite.sh.
# Book regeneration is throttled to once per day (use --force to bypass).
# Notification digest is throttled to every 12 hours (inside
# _SendNotificationDigest itself).

import os
import sys
import time
sys.path.append('/home/maint/music/src')

import tunejam
import utils

kConfigDir = os.path.join(utils.kDataDir, 'config')
kBookRegenLastRun = os.path.join(kConfigDir, 'books-last-regen.txt')
kBookRegenIntervalSeconds = 24 * 3600  # Once per day

def _get_last_book_regen():
  if not os.path.exists(kBookRegenLastRun):
    return 0.0
  try:
    with open(kBookRegenLastRun, 'r') as f:
      return float(f.read().strip())
  except:
    return 0.0

def _set_last_book_regen(ts):
  with open(kBookRegenLastRun, 'w') as f:
    f.write(str(ts))

def regenerate_books(force=False, log=True):
  """Regenerate books as needed"""

  # Get valid lock file pid; returns None if pid does not exist
  def get_lock_pid(lock_file):
    if not os.path.exists(lock_file):
      return None

    f = open(lock_file, 'r')
    txt = f.read()
    f.close()
    if not txt.startswith('lock-'):
      return None

    try:
      pid = int(text[len('lock-'):].strip())
    except:
      return None

    try:
      os.kill(int(pid), 0)
      return pid
    except OSError, exc:
      return None

  all_books = tunejam.get_all_books()

  # Write all lock files first
  for book in all_books:
    if book is None:
      continue

    # There may already be another process rebuilding the books
    lock_file = os.path.join(utils.kCacheLoc, book.name+'.lock')
    pid = get_lock_pid(lock_file)
    if pid is None and os.path.exists(lock_file):
      os.unlink(lock_file)

    # Write lock file
    f = open(lock_file, 'w')
    f.write('lock-%s' % str(os.getpid()))
    f.close()

  # Regenerate all books as needed
  for book in all_books:
    if book is None:
      continue

    # Regenerate the book
    target, up_to_date = book._GetCacheFile('.pdf')
    if not up_to_date:
      if log:
        print("Regenerating book %s" % target)
      book.GeneratePDF(generate=True)
    else:
      if log:
        print("Book %s was up to date" % target)

    # Remove the lock file
    lock_file = os.path.join(utils.kCacheLoc, book.name+'.lock')
    try:
      os.unlink(lock_file)
    except OSError:
      pass


#########################################################################
if __name__ == '__main__':
  force = '--force' in sys.argv
  digest_only = '--digest-only' in sys.argv

  if digest_only:
    # Only send notification digest (used by Send Now button and before_request hook)
    try:
      tunejam._SendNotificationDigest()
    except Exception as e:
      import traceback
      print("Notification digest failed: %s" % e)
      traceback.print_exc()
    sys.exit(0)

  # Regenerate books (once per day, unless --force)
  last_regen = _get_last_book_regen()
  elapsed = time.time() - last_regen
  if force or elapsed >= kBookRegenIntervalSeconds:
    regenerate_books(force=force)
    _set_last_book_regen(time.time())
  else:
    hours_ago = elapsed / 3600
    print("Book regeneration: skipping (last run %.1f hours ago)" % hours_ago)

  # Send notification digest (12-hour throttle is inside the function)
  try:
    tunejam._SendNotificationDigest()
  except Exception as e:
    import traceback
    print("Notification digest failed: %s" % e)
    traceback.print_exc()

  import fixperms
  fixperms.fix()
