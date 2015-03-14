import sys, os
import time
from html import *

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

from flask import Flask, Response
app = Flask(__name__)

def page_wrapper(body):
  
  # Build html head
  title = "Tune Jam"
  year = time.strftime("%Y", time.localtime())
  head = CHead([CTitle(title),
                CMeta("text/html; charset=utf-8", http_equiv="Content-Type"),
                CMeta("Copyright (c) 1999-%s Stephan Deibel" % year, name="Copyright"),
                '<link rel="stylesheet" type="text/css" href="/css" media="screen" />', 
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

  keys = obj.key
  keys = keys.split('/')
  key_str = []
  for key in keys:
    if key.endswith('m'):
      key_str.append(key[:-1] + " Minor")
    elif key.endswith('mix'):
      key_str.append(key[:-3] + " Modal")
    else:
      key_str.append(key + " Major")
  key_str = ' / '.join(key_str)
  parts.append(CH(title + ' - ' + section.capitalize() + ' - ' + key_str, 1))

  parts.append(ChordsToHTML(obj.chords))
  
  return page_wrapper(parts)
  
@app.route('/css')
def css():
  css = """
/* Overall defaults */
* {
margin:0;
padding:0;
font-family: varela_round, "Trebuchet MS", Arial, Verdana, sans-serif;
line-height:140%;
list-style:none;
}
table {
border:0px;  /* For Chrome and Safari */
border-left:2px solid #000;
border-right:2px solid #000;
margin-left:4px;
margin-top:10px;
}
a {
outline-style:none;
}
#body {
margin:20px;
}
p {
padding-left:145px;
}
tr.even {
background:#CCCCCC;
}
td {
padding-right:20px;
padding-left:20px;
font-size:250%;
}
td.last {
text-align:right;
padding-right:3px;
}
td.first {
padding-left:3px;
}
h1 {
word-wrap:break-word;
}
h2 {
padding-top:10px;
padding-bottom:5px;
}
"""
  return Response(css, mimetype='text/css')

def ChordsToHTML(chords):
    
    if not isinstance(chords, list):
        chords = utils.ParseChords(chords)
        
    html = []
    part_class = 'even'
    for i, part in enumerate(chords):
        row = []
        for i, measure in enumerate(part):
            if measure != '|:' and not row:
                row.append(CTD('', hclass='first'))
            if measure == '|:':
                row.append(CTD(' :', hclass='first'))
            elif measure == ':|':
                row.append(CTD(': ', hclass='last'))
            else:
                hclass = None
                if not row:
                    hclass = 'first'
                row.append(CTD(measure, hclass=hclass))
            if len(row) == 5 and (i + 1 >= len(part) or part[i+1] != ':|'):
                row.append('')
                html.append(CTR(row, hclass=part_class))
                row = []
            elif len(row) == 6:
                html.append(CTR(row, hclass=part_class))
                row = []
        if row:
            html.append(CTR(row, hclass=part_class))
            
        if part_class == 'even':
            part_class = 'odd'
        else:
            part_class = 'even'
        
    html = CTable(html, width=None, hclass="chords")
    
    return html
    
if __name__ == '__main__':
  from os import environ
  if 'WINGDB_ACTIVE' in environ:
    app.debug = False
  app.run(port=8000, use_reloader=True)

