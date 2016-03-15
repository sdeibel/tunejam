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
sessions_dir = os.path.join(os.path.dirname(fp), 'sessions')

all_dirs = [
  cache_dir,
  sessions_dir
]

def fix():
  for dirname in all_dirs:
    os.chdir(dirname)
    for cmd in cmds:
      os.system(cmd)

if __name__ == '__main__':
  fix()
  
