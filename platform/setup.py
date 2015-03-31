# Script to download and install the website platform

import os
import sys
import shutil

kDownloads = [
  "https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz", 
  "https://pypi.python.org/packages/source/s/setuptools/setuptools-14.0.tar.gz", 
  "https://pypi.python.org/packages/source/p/pip/pip-6.0.8.tar.gz", 
]

curdir = os.getcwd()
if not curdir.endswith('/platform'):
  print("Run this from the platform directory with 'python setup.py'")
  sys.exit(1)

kBaseDir = os.path.dirname(os.path.dirname(curdir))

for download in kDownloads:
  cmd = 'curl -O %s' % download
  os.system(cmd)
  cmd = 'tar xzf %s' % os.path.basename(download)
  os.system(cmd)

os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'Python-2.7.9'))
os.system('./configure --prefix=%s' % kBaseDir)
os.system('make')
os.system('make install')

os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'setuptools-14.0'))
os.system('%s/bin/python setup.py install' % kBaseDir)

os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'pip-6.0.8'))
os.system('%s/bin/python setup.py install' % kBaseDir)

os.chdir(os.path.join(kBaseDir, 'bin'))
os.system('./pip --trusted-host pypi.python.org install Flask')
os.system('./pip --trusted-host pypi.python.org install reportlab')

os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
os.system('tar xzf abcm2ps-8.7.2.tar.gz')
os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'abcm2ps-8.7.2'))
os.system('./configure --prefix=%s' % kBaseDir)
os.system('make')
os.system('make install')

if sys.platform != 'darwin':
  os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
  os.system('sudo rpm -Uvh webcore-fonts-3.0-1.noarch.rpm')

  os.chdir(os.path.join(kBaseDir, 'src', 'website'))
  os.system('chmod +x website.wsgi')
  
