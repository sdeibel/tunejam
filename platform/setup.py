# Script to download and install the website platform

import os
import sys
import shutil

curdir = os.getcwd()
if not curdir.endswith('/platform'):
  print("Run this from the platform directory with 'python setup.py'")
  sys.exit(1)

kBaseDir = os.path.dirname(os.path.dirname(curdir))
print "kBaseDir=", kBaseDir
ok = raw_input('OK? (default=yes)')
if ok.lower().startswith('n'):
  sys.exit(1)

# Python base
kDownloads = [
  "https://www.python.org/ftp/python/2.7.11/Python-2.7.11.tgz", 
  "https://pypi.python.org/packages/source/s/setuptools/setuptools-20.0.tar.gz", 
  "https://pypi.python.org/packages/source/p/pip/pip-8.0.2.tar.gz", 
]

for download in kDownloads:
  cmd = 'curl -O %s' % download
  os.system(cmd)
  cmd = 'tar xzf %s' % os.path.basename(download)
  os.system(cmd)

os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'Python-2.7.11'))
os.system('./configure --prefix=%s' % kBaseDir)
os.system('make')
os.system('make install')

# Patch broken Python 2.7.11 code (needed on the server)
broken_file = os.path.join(kBaseDir, 'lib', 'python2.7', 'ssl.py')
f = open(broken_file)
txt = f.read()
f.close()
txt = txt.replace(', HAS_ALPN', '#, HAS_ALPN')
txt = txt.replace(' or not _ssl.HAS_ALPN:', ':# or not _ssl.HAS_ALPN:')
f = open(broken_file, 'w')
f.write(txt)
f.close()

os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'setuptools-20.0'))
os.system('%s/bin/python setup.py install' % kBaseDir)

os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'pip-8.0.2'))
os.system('%s/bin/python setup.py install' % kBaseDir)

# Flask for website
os.chdir(os.path.join(kBaseDir, 'bin'))
os.system('./pip --trusted-host pypi.python.org install Flask')

# Reportlab for generating printable docs
os.system('./pip --trusted-host pypi.python.org install reportlab')

# abcm2ps to convert ABC to EPS
os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
os.system('tar xzf abcm2ps-8.11.0.tar.gz')
os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'abcm2ps-8.11.0'))
os.system('./configure --prefix=%s' % kBaseDir)
os.system('make')
os.system('make install')

if sys.platform != 'darwin':

  # Need extra fonts on Linux
  os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
  os.system('sudo rpm -Uvh webcore-fonts-3.0-1.noarch.rpm')

  # Used to generate EPS and PNG files
  os.system('sudo yum install ghostscript')
  os.system('sudo yum install ImageMagick')
  
if sys.platform == 'darwin':
  
  # Used by ImageMagick to convert from EPS file format
  os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
  os.system('tar xzf ghostscript-9.18.tar.gz')
  os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'ghostscript-9.18'))
  os.system('./configure --prefix=%s' % kBaseDir)
  os.system('make')
  os.system('make install')

  # Used to convert notes from EPS to PNG so reportlab can embed them
  os.chdir(os.path.join(kBaseDir, 'src', 'platform'))
  os.system('tar xzf ImageMagick.tar.gz')
  os.chdir(os.path.join(kBaseDir, 'src', 'platform', 'ImageMagick-6.9.3-3'))
  os.system('./configure --prefix=%s' % kBaseDir)
  os.system('make')
  os.system('make install')


