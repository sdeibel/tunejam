#!/home/maint/music/bin/python2.7

# Crontasks for the CGI production version of the website

import os
import sys
sys.path.append('/home/maint/music/src')

import tunejam
import utils

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
    lock_file = os.path.join(utils.kDatabaseDir, book.name+'.lock')
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
    lock_file = os.path.join(utils.kDatabaseDir, book.name+'.lock')
    try:
      os.unlink(lock_file)
    except OSError:
      pass


#########################################################################
if __name__ == '__main__':
  regenerate_books(force='--force' in sys.argv)
  import fixperms
  fixperms.fix()
  