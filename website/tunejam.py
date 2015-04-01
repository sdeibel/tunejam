#!/home/maint/music/bin/python
import sys, os
import time
from html import *
import tempfile

if sys.platform == 'darwin':
  sys.path.append(os.path.dirname(os.path.dirname(__file__)))
else:
  sys.path.append('/home/maint/music/src')
  
import utils

from flask import Flask, Response, request, send_file
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
  parts.append(CParagraph([CText("Tune Jam - Music Index", href='/music'), CBreak()]))
  parts.append(CParagraph([CText("Tune Jam - Create Set Sheets", href='/sets'), CBreak()]))
      
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
      recording, mimetype, filename = obj.GetRecording()
      play = []
      if recording is not None:
        play = [
          CImage(src='/image/speaker_louder_32.png', hclass="play-tune",
                 href='/recording/%s' % tune, width=16, height=16),
        ]
      parts.append(CText(title, href="/tune/%s" % tune))
      parts.extend(play)
      parts.append(CBreak())
      
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
<script src="/js/jquery.sortElements.js"></script>
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
  if ($("#print-checkbox").prop("checked")) {
    tunes = tunes + "&print=1"
  }
  window.location.href= "/sets/" + tunes;
}
function ClearTunes() {
  $( "#selectedtunes").children().appendTo('#alltunes');
  $('li').sortElements(function(a, b){
      return a.innerHTML > b.innerHTML ? 1 : -1;
  });
}
</script>
<style>
#alltunes {
border:1px;
}
#selectedtunes {
border:1px;
width:100%;
height:400px;
}
td {
vertical-align:top;
}
div.scroll {
height:400px;
width:500px;
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
      title = "Reels, Marches, Hornpipes, and Rags"
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
    if filter == 'reel' and section in ['reel', 'hornpipe', 'march', 'rag']:
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
    CInput(type='checkbox', name="print", value="1", checked="", id="print-checkbox"),
    CText("Size for printing"), 
    CBreak(2), 
    CInput(type='button', value="Submit", onclick='SubmitTunes();'),
    CInput(type='button', value="Clear", onclick='ClearTunes();'), 
  ], id='tunesform'))
  
  return page_wrapper(parts)

def tuneset(spec):
  
  parts = []
  
  parts.append("""<style>
#body {
margin-top:0px;
}  
</style>""")
  tunes = spec.split('&')
  printing = False
  if tunes[-1] == 'print=1':
    tunes = tunes[:-1]
    hclass = 'tune-container-print'
  else:
    hclass = 'tune-container'
  for i, tune in enumerate(tunes):
    if hclass.endswith('-print'):
      parts.append(CDiv(_tune(tune, printing=True), hclass=hclass+'-%i' % (i % 3)))
    else:
      parts.append(CDiv(_tune(tune), hclass=hclass))
  
  return page_wrapper(parts)

@app.route('/tune/<tune>')
def tune(tune):
  parts = []
  parts.extend(_tune(tune))
  return page_wrapper(parts)

@app.route('/recording/<tune>')
def recording(tune):
  obj = utils.CTune(tune)
  obj.ReadDatabase()
  recording, mimetype, filename = obj.GetRecording()
  if recording is None:
    return Response()
  return send_file(filename, mimetype=mimetype)

def _tune(name, printing=False):
  
  if printing:
    sfx = '-print'
  else:
    sfx = ''
    
  obj = utils.CTune(name)
  try:
    obj.ReadDatabase()
    title = obj.title
  except SystemExit:
    title = "Unknown Tune"

  key_str = obj.GetKeyString()

  chords = ChordsToHTML(obj.chords)
  recording, mimetype, filename = obj.GetRecording()
  
  tune = CDiv([
    CH([
      title + ' - ' + obj.type.capitalize() + ' - ' + key_str,
    ], 1, hclass='tune-title'+sfx), 
    CDiv(obj.MakeNotesSVG(), hclass='notes'+sfx),
    CDiv(chords, hclass='chords'+sfx),
  ], hclass='tune')
  
  parts = []

  if not printing:
    if recording is not None:
      play_div = CDiv([
        CImage(src='/image/speaker_louder_32.png', hclass="play-tune",
               href='/recording/%s' % name),
      ])
    else:
      play_div = CDiv([
        CImage(src='/image/speaker_louder_disabled_32.png', hclass="play-tune")
      ])
  else:
    play_div = ''
      
  tune_with_break = CDiv([
    CDiv(hclass='tune-break'),
    play_div, 
    tune, 
    # Trickery to work around browser bugginess where it sizes
    # according to unscaled chords table (we scale by 2.2; see css)
    CDiv([CDiv(chords, style="width:100%"),
          CDiv(chords, style="width:100%")], hclass='trans'), 
  ], hclass='tune-with-break')

  parts.append(tune_with_break)
  
  return parts
  
@app.route('/image/<image>')
def image(image):
  img_file = os.path.join(utils.kImageDir, image)
  return send_file(img_file, mimetype='image/png')
  
@app.route('/js/<filename>')
def js(filename):
  js_file = os.path.join(utils.kJSDir, filename)
  return send_file(js_file, mimetype='text/javascript')
  
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
h1.tune-title {
white-space:nowrap;
}
h1.tune-title-print {
white-space:nowrap;
font-size:19pt;
margin-left:-0.25in;
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
width:8.5in;
}
p {
padding-left:145px;
}
div.tune-container-print-0 {
position:absolute;
top:0.0in;
left:0.5in;
height:3.5in;
max-height:3.5in;
min-height:3.5in;
width:7.5in;
max-width:7.5in;
min-width:7.5in;
page-break-before:always;
}
div.tune-container-print-1 {
position:absolute;
top:4.0in;
left:0.5in;
height:3.5in;
max-height:3.5in;
min-height:3.5in;
width:7.5in;
max-width:7.5in;
min-width:7.5in;
}
div.tune-container-print-2 {
position:absolute;
top:8.0in;
left:0.5in;
height:3.5in;
max-height:3.5in;
min-height:3.5in;
width:7.5in;
max-width:7.5in;
min-width:7.5in;
}
div.tune {
position:relative;
}
div.tune-with-break img {
position:absolute;
right:1.0in;
z-index:100;
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
transform: scale(1.2, 1.2) translate(9%,7%);
}
div.notes-print {
position:absolute;
left:0in;
top:0in;
margin-left:-0.25in
}
div.chords {
position:absolute;
right:0.5in;
width:3.5in;
top:0.5in;
transform: scale(2.2, 2.2) translate(25%,15%);
padding-right:0.25in;
}
div.chords-print {
position:absolute;
right:0.5in;
width:3.5in;
top:0.5in;
transform: scale(1.8, 1.8) translate(17%,15%);
padding-right:0.25in;
}
div.trans {
opacity:0;
display:table;
}

/* Chord tables */
table.chords {
border:0px;  /* For Chrome and Safari */
border-left:2px solid #000;
border-right:2px solid #000;
margin-left:4px;
margin-top:20px;
float:right;
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
img.play-tune {
display:none;
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
    
if __name__ == '__main__':

  # Kill any old processes
  fn = tempfile.mktemp()
  os.system('ps aux | grep tunejam.py > %s' % fn)
  f = open(fn)
  lines = f.readlines()
  f.close()
  found_process = False
  for line in lines:
    pid = line.split()[1]
    try:
      pid = int(pid)
      if pid != os.getpid() and not 'grep' in line:
        print("killing pid %i" % pid)
        os.system('kill -TERM %i' % pid)
        found_process = True
    except:
      pass
  if found_process:
    time.sleep(1.0)

  # Start new server
  from os import environ
  if 'WINGDB_ACTIVE' in environ:
    app.debug = False
  if sys.platform == 'darwin':
    host = None
  else:
    host = 'music.cambridgeny.net'
  app.run(host=host, port=60080, use_reloader=True)

