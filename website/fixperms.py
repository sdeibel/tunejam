import os
import sys

cmds = [
  'sudo chown -R apache.apache .', 
  'sudo chmod 664 `find . -type f`', 
  'sudo chmod 775 `find . -type d`', 
  'sudo chmod g+s `find . -type d`',   
]

fp = os.path.fullpath(__file__)
cache_dir = os.path.join(os.path.dirname(fp), 'cache')

def fix():
  os.chdir(cache_dir)
  for cmd in cmds:
    os.system(cmd)

if __name__ == '__main__':
  fix()
  
