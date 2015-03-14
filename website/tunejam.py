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
                '<link rel="stylesheet" type="text/css" href="/css" media="print" />', 
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
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      title += ' - ' + obj.GetKeyString()
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

  key_str = obj.GetKeyString()
  parts.append(CH(title + ' - ' + section.capitalize() + ' - ' + key_str, 1))

  parts.append(CDiv(NotesToXHTML(obj), hclass='notes'))
  parts.append(CDiv(ChordsToHTML(obj.chords), hclass='chords'))
  
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
h1 {
word-wrap:break-word;
}
h2 {
padding-top:10px;
padding-bottom:5px;
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
div.notes {
position:absolute;
float:left;
margin-top:-.5in;
}
div.chords {
position:absolute;
float:right;
margin-left:4.5in;
}

/* Chord tables */
table.chords {
border:0px;  /* For Chrome and Safari */
border-left:2px solid #000;
border-right:2px solid #000;
margin-left:4px;
margin-top:20px;
transform: scale(2.2, 2.2) translate(25%,25%);
}
tr.even {
background:#DDDDDD;
}
td {
padding-right:1.0em;
}
td.last-chord {
padding-right:0.5em;
}
td.last {
text-align:right;
padding-right:3px;
}
td.first {
padding-left:3px;
padding-right:0.5em;
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
                elif len(row) == 4:
                    hclass = 'last-chord'
                row.append(CTD(measure, hclass=hclass))
            if len(row) == 5 and (i + 1 >= len(part) or part[i+1] != ':|'):
                row.append(CTD('', hclass='last'))
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
    
def NotesToXHTML(tune):

  if not isinstance(tune, utils.CTune):
    tune = utils.CTune(tune)
    
  try:
    tune.ReadDatabase()
  except:
    return None
  
  abc = tune.MakeNotes()
  svg = utils.ABCToPostscript(abc, svg=True)
  
  f = open(svg)
  svg = f.read()
  f.close()
  
  return svg

if __name__ == '__main__':
  from os import environ
  if 'WINGDB_ACTIVE' in environ:
    app.debug = False
  app.run(port=8000, use_reloader=True)

