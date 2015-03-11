import time
from html import *

from flask import Flask
app = Flask(__name__)

def page_wrapper(body):
  
  # Build html head
  title = "Tune Jam"
  year = time.strftime("%Y", time.localtime())
  head = CHead([CTitle(title),
                CMeta("text/html; charset=utf-8", http_equiv="Content-Type"),
                CMeta("Copyright (c) 1999-%s Stephan Deibel" % year, name="Copyright"),
                '<link rel="stylesheet" type="text/css" href="/css" media="screen"/>'
              ])

  body_div = CBody([CDiv(body, id="body")])
  
  html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">"""
  html += str(CHTML([head, body_div], xmlns="http://www.w3.org/1999/xhtml"))
  
  return html
  
@app.route('/')
def home():
  return page_wrapper([
    CParagraph('Hello World!'),
    CParagraph("Test again")
  ])

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
