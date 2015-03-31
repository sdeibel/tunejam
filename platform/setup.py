# Script to download and install the website platform

import os
import sys
import shutil

kDownloads = [
  "https://www.python.org/ftp/python/2.7.9/Python-2.7.9.tgz", 
  "https://pypi.python.org/packages/source/s/setuptools/setuptools-14.0.tar.gz", 
  "https://pypi.python.org/packages/source/p/pip/pip-6.0.8.tar.gz", 
]

kBaseDir = '/Users/sdeibel/abc'

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
os.system('./pip install Flask')
os.system('./pip install reportlab')

os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
os.system('unzip -o abcm2ps-8.5.1-osx.zip')
fn1 = os.path.join(kBaseDir, 'src', 'platform', 'abcm2ps-8.5.1', 'abcm2ps')
fn2 = os.path.join(kBaseDir, 'bin', 'abcm2ps')
os.system('chmod +x %s' % fn2)

shutil.copyfile(fn1, fn2)

