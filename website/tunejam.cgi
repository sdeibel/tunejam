#!/home/maint/music/bin/python2.7

#from wsgiref.handlers import CGIHandler
#from tunejam import app

#CGIHandler().run(app)

# This line enables CGI error reporting
import cgitb
cgitb.enable()

from wsgiref.handlers import CGIHandler
import traceback

app = None
try:
  import tunejam
  app = tunejam.app
except Exception, e:
  print traceback.format_exc([10])
  print 'Problem in cgiappserver-prod with moc import: %s' % e 

#class ScriptNameStripper(object):
  #def __init__(self, app):
    #self.app = app
  #def __call__(self, environ, start_response):
    #environ['SCRIPT_NAME'] = ''
    #return self.app(environ, start_response)

#app = ScriptNameStripper(app)

try:
  CGIHandler().run(app)
except Exception, e:
  print traceback.format_exc([10]) 
  print 'Problem in cgiappserver-prod with CGIHandler().run(): %s' % e 