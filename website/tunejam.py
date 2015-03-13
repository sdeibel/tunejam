import sys, os
import time
from html import *

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

from flask import Flask
app = Flask(__name__)

def page_wrapper(body):
  
  # Build html head
  title = "Tune Jam"
  year = time.strftime("%Y", time.localtime())
  head = CHead([CTitle(title),
                CMeta("text/html; charset=utf-8", http_equiv="Content-Type"),
                CMeta("Copyright (c) 1999-%s Stephan Deibel" % year, name="Copyright"),
                '<link rel="stylesheet" type="text/css" href="/css" media="screen" />'
              ])

  body_div = CBody([CDiv(body, id="body")])
  
  html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">"""
  html += str(CHTML([head, body_div], xmlns="http://www.w3.org/1999/xhtml"))
  
  return html
  
@app.route('/')
def home():
  parts = []
  parts.append(CH("Cambridge NY", 1))
  parts.append(CParagraph("Welcome!"))
  parts.append(CParagraph([CText("Tune Jam", href='/music'), CBreak()]))
      
  return page_wrapper(parts)

  
@app.route('/music')
def music():
  parts = []
  parts.append(CH("Tune Index", 1))
  tunes = utils.GetTuneIndex()

  sections = tunes.keys()
  sections.sort()
  for section in sections:
    parts.append(CH(utils.kSectionTitles[section], 2))
    for title, tune in tunes[section]:
      parts.extend([CText(title, href="/tune/%s/%s" % (section, tune)), CBreak()])
      
  return page_wrapper(parts)

@app.route('/tune/<section>/<tune>')
def tune(section, tune):
  parts = []
  
  obj = utils.CTune(tune)
  try:
    obj.ReadDatabase()
    title = obj.title
  except SystemExit:
    title = "Unknown Tune"
  
  parts.append(CH(title + ' - ' + section.capitalize(), 1))

  return page_wrapper(parts)
  
@app.route('/css')
def css():
  return """
#body {
background:#FF0000;
border:10px;
}
p {
padding-left:145px;
}
"""

if __name__ == '__main__':
  from os import environ
  if 'WINGDB_ACTIVE' in environ:
    app.debug = False
  app.run(port=8000, use_reloader=True)
