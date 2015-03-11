# Script to download and install the website platform

import os

kDownloads = [
  "https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz", 
  "https://pypi.python.org/packages/source/s/setuptools/setuptools-14.0.tar.gz", 
  "https://pypi.python.org/packages/source/p/pip/pip-6.0.8.tar.gz", 
]

dirname = os.getcwd()

for download in kDownloads:
  cmd = 'curl -O %s' % download
  os.system(cmd)
  cmd = 'tar xzf %s' % os.path.basename(download)
  os.system(cmd)

os.chdir(os.path.join(dirname, 'Python-2.7.9'))
os.system('./configure --prefix=%s' % dirname)
os.system('make')
os.system('make install')

os.chdir(os.path.join(dirname, 'setuptools-14.0'))
os.system('%s/bin/python setup.py install' % dirname)

os.chdir(os.path.join(dirname, 'pip-6.0.8'))
os.system('%s/bin/python setup.py install' % dirname)

os.chdir(os.path.join(dirname, 'bin'))
os.system('./pip install Flask')




