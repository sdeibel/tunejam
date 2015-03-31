#!/home/maint/music/bin/python
import sys
from wsgiref.handlers import CGIHandler
sys.path.append('/home/maint/music/src/website')
sys.path.append('/home/maint/music/src')
from tunejam import app
CGIHandler().run(app)
