import os
import sys

cmds = [
  'sudo chown -R apache.apache .', 
  'sudo chmod 664 `find . -type f`', 
  'sudo chmod 775 `find . -type d`', 
  'sudo chmod g+s `find . -type d`',   
]

fp = os.path.abspath(__file__)
cache_dir = os.path.join(os.path.dirname(fp), 'cache')
events_dir = os.path.join(os.path.dirname(fp), 'events')

all_dirs = [
  cache_dir,
  events_dir
]

def fix():
  for dirname in all_dirs:
    os.chdir(dirname)
    print("Fixing perms for %s" % dirname)
    for cmd in cmds:
      print(cmd)
      os.system(cmd)

if __name__ == '__main__':
  fix()
  
