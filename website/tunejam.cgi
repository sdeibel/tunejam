#!/home/maint/music/bin/python2.7

# To use this script, Apache needs to be configured with the following:

#<VirtualHost *:80>
#  ServerName music.cambridgeny.net
#  DocumentRoot /home/maint/music/src/html
#  ErrorLog logs/music-error.log
#  CustomLog logs/music-access.log combined
#
#  RewriteEngine On
#  RewriteLog logs/music-rewrite.log
#  RewriteLogLevel 0
#  RewriteRule ^/$ /cgi-bin/tunejam.cgi/ [PT]
#  RewriteRule ^/(.+)/?$ /cgi-bin/tunejam.cgi/$1 [PT]
#
#  ScriptAlias /cgi-bin/ /home/maint/music/src/website/
#
#</VirtualHost>

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

class ScriptNameStripper(object):
  def __init__(self, app):
    self.app = app
  def __call__(self, environ, start_response):
    environ['SCRIPT_NAME'] = ''
    return self.app(environ, start_response)

app = ScriptNameStripper(app)

try:
  CGIHandler().run(app)
except Exception, e:
  print traceback.format_exc([10]) 
  print 'Problem in cgiappserver-prod with CGIHandler().run(): %s' % e 