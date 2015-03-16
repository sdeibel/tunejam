import sys, os
import time
from html import *

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import utils

from flask import Flask, Response, request
app = Flask(__name__)

def page_wrapper(body):
  
  # Build html head
  title = "Tune Jam"
  year = time.strftime("%Y", time.localtime())
  head = CHead([CTitle(title),
                CMeta("text/html; charset=utf-8", http_equiv="Content-Type"),
                CMeta("Copyright (c) 1999-%s Stephan Deibel" % year, name="Copyright"),
                '<link rel="stylesheet" type="text/css" href="/css/screen" media="screen" />', 
                '<link rel="stylesheet" type="text/css" href="/css/print" media="print" />', 
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
      parts.extend([CText(title, href="/tune/%s" % tune), CBreak()])
      
  return page_wrapper(parts)

@app.route('/sets', methods=['GET', 'POST'])
@app.route('/sets/<spec>')
def sets(spec=None):
  
  if spec is not None:
    return tuneset(spec)

  filter = request.form.get('filter')
  if filter == 'all':
    filter = None
  
  parts = []
  parts.append("""<link rel="stylesheet" href="//code.jquery.com/ui/1.11.4/themes/smoothness/jquery-ui.css">
<script src="//code.jquery.com/jquery-1.10.2.js"></script>
<script src="//code.jquery.com/ui/1.11.4/jquery-ui.js"></script>
 <script>
$(function() {
  $( "#alltunes, #selectedtunes" ).sortable({
    connectWith: ".connectedSortable"
  }).disableSelection();
});
function SubmitTunes() {
  var tunes = $( "#selectedtunes" ).sortable( "serialize", {key:"tune"});
  tunes = tunes.replace(/\+/g, "_");
  tunes = tunes.replace(/tune=/g, "");
  window.location.href= "/sets/" + tunes;
}
</script>
<style>
#alltunes {
width=45%;
border:1px;
}
#selectedtunes {
width=45%;
border:1px;
width:100%;
height:300px;
}
td {
vertical-align:top;
width:45%
}
div.scroll {
height:300px;
overflow:auto;
border: 1px solid #666666;
padding: 8px;
}
p {
padding-left:0px;
padding-top:0.5em;
padding-bottom:0.5em;
}
</style>
""")
  
  parts.append(CH("Create a Tune Set", 1))
  parts.append(CParagraph("Drag one or more songs from the list "
                          "on the left to the list on the right:"))
  
  
  section_options = [
    ('all', 'All')
  ]

  keys = utils.kSectionTitles.keys()
  keys.sort()
  for key in keys:
    if key == 'reel':
      title = "Reels, Marches, and Hornpipes"
    else:
      title = utils.kSectionTitles[key]
    section_options.append((key, title))
    
  parts.append(CForm([
    CText("Filter:", bold=1),
    CSelect(section_options, current=filter, name='filter',
            onchange='this.form.submit()')
  ], action="/sets", method='POST'))
  parts.append(CBreak())
  
  all_tunes = []
  tunes = utils.GetTuneIndex()
  for section in tunes:
    if filter == 'reel' and section in ['reel', 'hornpipe', 'march']:
      pass
    elif filter is not None and filter != section:
      continue
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      title += ' - %s - %s' % (obj.type.capitalize(), obj.GetKeyString())
      all_tunes.append((title, CItem(title, id='tune_%s' % tune.replace('_', '+'), hclass='ui-state-default')))

  all_tunes.sort()
  all_tunes = [i[1] for i in all_tunes]
  
  tunes_list = CDiv(CList(all_tunes, id='alltunes', hclass='connectedSortable'), hclass='scroll')
  selected_list = CDiv(CList([], id='selectedtunes', hclass='connectedSortable'), hclass='scroll')
  
  parts.append(CTable(CTR([tunes_list, selected_list])))
  parts.append(CBreak())
  
  parts.append(CForm([
    CInput(type='button', value="Submit", onclick="SubmitTunes();"),
    CInput(type='button', value="Clear", onclick='window.location.reload(false)'), 
  ]))
  
  return page_wrapper(parts)

def tuneset(spec):
  
  parts = []
  
  parts.append("""<style>
#body {
margin-top:0px;
}  
</style>""")
  tunes = spec.split('&')
  for i, tune in enumerate(tunes):
    parts.append(CDiv(_tune(tune), hclass='tune-%i' % i))
  
  return page_wrapper(parts)

@app.route('/tune/<tune>')
def tune(tune):
  parts = _tune(tune)
  return page_wrapper(parts)

def _tune(tune):
  
  obj = utils.CTune(tune)
  try:
    obj.ReadDatabase()
    title = obj.title
  except SystemExit:
    title = "Unknown Tune"

  key_str = obj.GetKeyString()

  chords = ChordsToHTML(obj.chords)
  
  tune = CDiv([
    CH(title + ' - ' + obj.type.capitalize() + ' - ' + key_str, 1),
    CDiv(NotesToXHTML(obj), hclass='notes'),
    CDiv(chords, hclass='chords'),
    # Trickery to work around browser bugginess where it sizes
    # according to unscaled chords table (we scale by 2.2; see css)
    CDiv([chords, chords], hclass='trans'), 
  ], hclass='tune')
  
  tune_with_break = CDiv([
    CDiv(hclass='tune-break'),
    tune, 
  ], hclass='tune-with-break')

  return [tune_with_break]
  
@app.route('/css/<media>')
def css(media):
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
div.tune {
position:relative;
}
div.tune-break {
height:2.5em;
}
div.tune-with-break {
page-break-inside:avoid;
}
div.notes {
position:absolute;
left:0in;
top:0in;
transform: scale(1.2, 1.2) translate(10%,7%);
}
div.chords {
position:absolute;
left:5.5in;
top:0.5in;
}
div.trans {
opacity:0;
display:table;
transform: scale(2.2, 2.2) translate(25%,25%);
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
line-height:120%;
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
  
  if media == 'print':
    css += """
/*Preferable but does not work in Firefox 36.0.1 (the latest)*/
/*@page {
margin:0.5in;
}*/
#body {
margin:0.5in;
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

