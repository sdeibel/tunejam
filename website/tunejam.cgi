#!/home/maint/music/bin/python2.7
from wsgiref.handlers import CGIHandler
from tunejam import app

CGIHandler().run(app)
