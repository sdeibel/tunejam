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

from flask import Flask, Response, request, send_file, make_response
app = Flask(__name__)

@app.route('/')
def home():
  parts = []
  parts.append(CH("Hubbard Hall Tune Jam", 1))
  parts.append(CParagraph("Welcome!"))
  parts.append(CParagraph("This is under development.  Here are the existing pages you can try:"))
  parts.append(CParagraph([CText("Tune Jam - Music Index", href='/music'), CBreak()]))
  parts.append(CParagraph([CText("Tune Jam - Create Set Sheets", href='/sets'), CBreak()]))
  parts.append(CParagraph([CText("Tune Jam - Printing Tune Books", href='/print'), CBreak()]))
      
  return PageWrapper(parts)

@app.route('/music')
def music():
  parts = []
  parts.append(CH("Tune Index", 1))
  parts.append(CParagraph("This lists all the tunes in the database so far.  If there is a recording, "
                          "you can click on the speaker icon to hear it."))
  tunes = utils.GetTuneIndex(True)

  sections = tunes.keys()
  sections.sort()
  if 'incomplete'in sections:
    sections.remove('incomplete')
    sections.append('incomplete')
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
          CImage(src='/image/speaker_louder_32.png', hclass="play-tune-index",
                 href='/recording/%s' % tune, width=16, height=16),
        ]
      parts.append(CText(title, href="/tune/%s" % tune))
      parts.extend(play)
      parts.append(CBreak())
      
  parts.append(CBreak(2))
  return PageWrapper(parts)

@app.route('/sets', methods=['GET', 'POST'])
@app.route('/sets/')
@app.route('/sets/<spec>')
def sets(spec=None):
  
  error = None
  preload_tunes = []

  if spec is not None:
    args = spec.split('&')
    tunes = []
    _print = False
    save = False
    edit = False
    title = ''
    subtitle = ''
    
    for arg in args:
      if arg == 'print=1':
        _print = True
      elif arg == 'save=1':
        save = True
      elif arg == 'edit=1':
        edit = True
      elif arg.startswith('title='):
        title = arg[len('title='):].strip()
      elif arg.startswith('subtitle='):
        subtitle = arg[len('subtitle='):].strip()
      elif arg:
        tunes.append(arg)
    
    if save and not title:
      error = "You need to set a title if you plan to save this set of tunes!  Go back to return to the selected tunes."
      
    elif tunes:
      
      import hashlib
      md5sum = hashlib.md5()
      for tune in tunes:
        md5sum.update(tune)
      name = 'C-' + md5sum.hexdigest()
      
      if save and title:
        date = time.strftime("%d %B %Y", time.localtime())
        book = '%s\n%s\n%s\nhttp://cambridgeny.net/music\n--\n' % (
          title, subtitle, date
        )
        page = []
        for tune in tunes:
          page.append(tune)
          if len(page) == 3:
            book += ' '.join(page) + '\n'
            page = []
        if page:
          book += ' '.join(page) + '\n'
          page = []
        f = open(os.path.join(utils.kSaveLoc, '%s.book' % name), 'w')
        f.write(book)
        f.close()
      
      if _print:
        return CreateTuneSetPDF(name, title, subtitle, tunes)
        
      elif edit:
        preload_tunes = tunes
        
      else:
        return CreateTuneSetHTML(tunes)

  filter = request.form.get('filter')
  if filter == 'all':
    filter = None
  
  parts = []
  # Extra JS libraries came from:
  #https://github.com/padolsey-archive/jquery.fn/tree/master/sortElements
  #https://raw.github.com/furf/jquery-ui-touch-punch/master/jquery.ui.touch-punch.min.js
  parts.append("""<link rel="stylesheet" href="//code.jquery.com/ui/1.11.4/themes/blitzer/jquery-ui.css">
<script src="//code.jquery.com/jquery-1.12.0.min.js"></script>
<script src="//code.jquery.com/ui/1.11.4/jquery-ui.min.js"></script>
<script src="/js/jquery.sortElements.js"></script>
<script src="/js/jquery.ui.touch-punch.min.js"></script> 
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
    tunes = tunes + "&print=1";
  }
  if ($("#save-checkbox").prop("checked")) {
    tunes = tunes + "&save=1";
  }
  if ($("#print-checkbox").prop("checked") || $("#save-checkbox").prop("checked")) {
    if ($("#title").val()) {
      tunes = tunes + "&title=" + $("#title").val();
    }
    if ($("#subtitle").val()) {
      tunes = tunes + "&subtitle=" + $("#subtitle").val();
    }
  }
  window.location.href= "/sets/" + tunes;
}
function FilterTunes() {
  var filter = $("#filterselect").val();
  var textfilter = $("#filtertext").val();
  var tunes = $("#alltunes").find("li");
  tunes.each(function (idx, li) {
    var item = $(li);
    var visible = 0;
    if (filter == "all") {
      visible = 1;
    }
    else if (filter == "ax4" ) {
      visible = (item.hasClass("reel") ||
                 item.hasClass("hornpipe") ||
                 item.hasClass("march") ||
                 item.hasClass("rag"));
    } else {
      visible = item.hasClass(filter);
    }
    if (textfilter != "") {
      if (item.text().toLowerCase().search(textfilter.toLowerCase()) == -1) {
        visible = 0;
      }
    }
    if (visible) {
      item.css("display", "");
    } else {
      item.css("display", "none");
    }
  });
}
function RandomThree() {
  var tunes = $("#alltunes").find("li");
  visible = [];
  for (i = 1; i < tunes.length; i++) {
    var item = tunes[i];
    var display = $(item).css("display");
    if (display != "none") {
      visible.push(item);
    }
  }

  var count = 0;
  while (count < 3 && visible.length > 0) {
    var idx = Math.floor(Math.random()*visible.length);
    var item = visible[idx];
    $(item).appendTo("#selectedtunes");
    visible.splice(idx, 1);
    count = count + 1;
  }
}
function FilterSubmit() {
  return false;
}
function ClearTunes() {
  $( "#selectedtunes").children().appendTo('#alltunes');
  $('li').sortElements(function(a, b){
      return a.innerHTML > b.innerHTML ? 1 : -1;
  });
  FilterTunes();
}
$(document).ready(function() {
    if($("#save-checkbox").is(":checked") || $("#print-checkbox").is(":checked")) {
        $('#saveitems').css("display", "");
    } else {
        $('#saveitems').css("display", "none");
    }

    $('#save-checkbox').change(function() {
        if($("#save-checkbox").is(":checked") || $("#print-checkbox").is(":checked")) {
            $('#saveitems').css("display", "");
        } else {
            $('#saveitems').css("display", "none");
        }
    });
    $('#print-checkbox').change(function() {
        if($("#save-checkbox").is(":checked") || $("#print-checkbox").is(":checked")) {
            $('#saveitems').css("display", "");
        } else {
            $('#saveitems').css("display", "none");
        }
    });
    FilterTunes();
});

</script>
<style>
#alltunes {
border:1px;
}
#selectedtunes {
border:1px;
height:400px;
}
td {
vertical-align:top;
}
div.scroll {
float:left;
height:400px;
width:350px;
overflow-y:scroll;
overflow-x:hidden;
border: 1px solid #666666;
padding: 8px;
-webkit-overflow-scrolling:touch;
}
p {
padding-left:0px;
padding-top:0.5em;
padding-bottom:0.5em;
}
</style>
""")
  
  parts.append(CH("Create a Tune Set", 1))
  if error:
    parts.append(CParagraph([CText("Error: ", bold=1), error], style="background-color:#FFFF00; padding-left:5px;"))
  parts.append(CParagraph("Drag one or more songs from the list "
                          "on the left to the list on the right, or press the 'Random 3' "
                          "button to select three random tuned.  Then "
                          "press Submit to generate the set.  Use "
                          "Clear at the bottom to start a new set:"))
  
  
  section_options = [
    ('all', 'All')
  ]

  keys = utils.kSectionTitles.keys()
  keys.append('ax4')
  keys.sort()
  if 'incomplete' in keys:
    keys.remove('incomplete')
  for key in keys:
    if key == 'ax4':
      title = "All 2/4 and 4/4 Time"
    else:
      title = utils.kSectionTitles[key]
    section_options.append((key, title))
    
  parts.append(CForm([
    CText("Filter:", bold=1),
    CSelect(section_options, current=filter, name='filter',
            onchange='FilterTunes()', id='filterselect'),
    CInput(type='TEXT', name='text_filter', onkeyup='FilterTunes()', id='filtertext'), 
    CInput(type='RESET', value='X', id='filter-reset', onclick='setTimeout(function() { FilterTunes(); })', style="border:0px; font-weight:bold;"),
    CNBSP(2), 
    CInput(type='BUTTON', value='-> Random 3', onclick='setTimeout(function() { RandomThree(); })'), 
  ], onsubmit="return FilterSubmit();", id="filter-form"))
  parts.append(CBreak())
  
  all_tunes = []
  selected_tunes = []
  tunes = utils.GetTuneIndex(False)
  for section in tunes:
    if section == 'incomplete':
      continue
    visible = True
    if filter == 'reel' and section not in ['reel', 'hornpipe', 'march', 'rag']:
      visible = False
    elif filter is not None and filter != section:
      visible = False
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      title += ' - %s - %s' % (obj.type.capitalize(), obj.GetKeyString())
      if tune in preload_tunes:
        use_list = selected_tunes
      else:
        use_list = all_tunes
      if visible:
        use_list.append((title, CItem(title, id='tune_%s' % tune.replace('_', '+'),
                                       hclass='ui-state-default %s' % section)))
      else:
        use_list.append((title, CItem(title, id='tune_%s' % tune.replace('_', '+'),
                                       hclass='ui-state-default %s' % section,
                                       style="display:none")))

  all_tunes.sort()
  all_tunes = [i[1] for i in all_tunes]
  
  selected_tunes = [i[1] for i in selected_tunes]
  
  tunes_list = CDiv(CList(all_tunes, id='alltunes', hclass='connectedSortable'), hclass='scroll')
  selected_list = CDiv(CList([selected_tunes], id='selectedtunes', hclass='connectedSortable'), hclass='scroll')
  
  parts.append(CTable(CTR([tunes_list, selected_list])))
  parts.append(CParagraph("On mobile devices, scroll with two fingers, or by dragging an item down, or by entering a text filter to shorten the list.", hclass="clear"))
  
  parts.append(CForm([
    CInput(type='checkbox', name="print", value="1", checked="", id="print-checkbox"),
    CText("Generate printable pages (PDF)"), 
    #CBreak(), 
    #CInput(type='checkbox', name="save", value="1", checked="", id="save-checkbox"),
    #CText("Save this set"),
    CTable([
      [
        CTD(CText("Title:", bold=1), style="width:8em; padding-top:5px;"), 
        CInput(type='TEXT', name='title', id='title', maxlength="65", style="width:40em"),
      ],
      [
        CTD(CText("Subtitle:", bold=1), style="width:8em;"), 
        CInput(type='TEXT', name='subtitle', id='subtitle', maxlength="65", style="width:40em"),
      ], 
    ], id='saveitems'), 
    CBreak(2), 
    CInput(type='button', value="Submit", onclick='SubmitTunes();'),
    CInput(type='button', value="Clear", onclick='ClearTunes();'), 
  ], id='tunesform'))

  saved = []
  for fn in os.listdir(utils.kSaveLoc):
    if fn.endswith('.book'):
      book = utils.CBook(os.path.join(utils.kSaveLoc, fn))
      saved.append((book.title, book))
  saved.sort()
  
  if saved:
    parts.extend([
      CBreak(), 
      CH("Saved Sets", 1)
    ])
    for title, book in saved:
      if book.subtitle:
        title = '%s - %s - %s' % (book.title, book.subtitle, book.date)
      else:
        title = '%s - %s' % (book.title, book.date)
      parts.extend([
        CBreak(), 
        CText(title, href='/saved/view/%s' % book.name),
        CNBSP(),
        CText('-'), 
        CNBSP(),
        CText('Print', href='/saved/print/%s' % book.name),
        CNBSP(),
        CText('Edit', href='/saved/edit/%s' % book.name), 
        CNBSP(),
        CText('Delete', href='/saved/delete/%s' % book.name), 
      ])
  
  return PageWrapper(parts)

@app.route('/tune/<tune>')
def tune(tune):
  parts = []
  parts.extend(CreateTuneHTML(tune))
  return PageWrapper(parts)

@app.route('/png/<tune>')
def png(tune):
  tune = utils.CTune(tune)
  png_file = tune.MakeNotesPNGFile(density=80)
  return send_file(png_file, mimetype='image/png')

def _get_all_books():
  import allbook
  import flipbook
  retval = [
    allbook.CAllBook(),
    allbook.CAllBookBySection(),
    allbook.CAllBookByTime(), 
    flipbook.CFlipBook(),
    flipbook.CFlipBookByTime(), 
    None, 
  ]
  custom_books = []
  files = os.listdir(utils.kDatabaseDir)
  for fn in files:
    if not fn.endswith('.book'):
      continue
    book = fn[:-len('.book')]
    custom_books.append(utils.CBook(book))
    
  def sort_custom(o1, o2):
    return cmp(o1.subtitle, o2.subtitle)
  custom_books.sort(sort_custom)
  retval.extend(custom_books)

  return retval
  
@app.route('/print')
@app.route('/print/<format>')
@app.route('/print/<format>/<bookname>')
def doprint(format=None, bookname=None):
  refresh = None
  parts = []
  if format is None:
    parts.extend([
      CH('Printable Books', 1), 
      CParagraph("The following printing options are available:"),
      CBreak(), 
    ])
    
    for book in _get_all_books():
      if book is None:
        parts.append(CBreak())
        continue
      if os.path.exists(os.path.join(utils.kDatabaseDir, book.name+'.lock')):
        url = None
        title = book.subtitle + ' - temporarily unavailable - rebuilding '
        img = CImage(src='/image/rebuilding.gif')
        refresh = 5
      else:
        url = '/print/%s' % book.url
        img = ''
        title = book.subtitle
      parts.extend([
        CText(title, href=url),
        img, 
        CBreak(),
      ])
    
  elif format == 'all-by-section':
    import allbook
    book = allbook.CAllBookBySection()
    pdf = book.GeneratePDF()
    return send_file(pdf, mimetype='application/pdf')
  
  elif format == 'all-by-time':
    import allbook
    book = allbook.CAllBookByTime()
    pdf = book.GeneratePDF()
    return send_file(pdf, mimetype='application/pdf')
  
  elif format == 'all':
    import allbook
    book = allbook.CAllBook()
    pdf = book.GeneratePDF()
    return send_file(pdf, mimetype='application/pdf')
  
  elif format == 'book':
    import setsheets
    book = utils.CBook(bookname)
    pdf = book.GeneratePDF(include_index=not bookname.startswith('draft'))
    return send_file(pdf, mimetype='application/pdf')
  
  elif format == 'flip':
    import flipbook
    book = flipbook.CFlipBook()
    pdf = book.GeneratePDF(type_in_header=True, include_index=True)
    return send_file(pdf, mimetype='application/pdf')
  
  elif format == 'flip-by-time':
    import flipbook
    book = flipbook.CFlipBookByTime()
    pdf = book.GeneratePDF(type_in_header=False, include_index=True)
    return send_file(pdf, mimetype='application/pdf')
  
  else:
    parts.append(CParagraph('Unknown print directive'))

  return PageWrapper(parts, refresh)

@app.route('/saved/<action>/<book>')
def saved(action=None, book=None):
  parts = []
  if action is None or book is None:
    parts.append("Book list here")
    return PageWrapper(parts)

  fn = os.path.join(utils.kDatabaseDir, book+'.book')
  if not os.path.isfile(fn):
    fn = os.path.join(utils.kSaveLoc, book+'.book')
  if not os.path.isfile(fn):
    parts.append(CParagraph("Book %s does not exist" % book))
    return PageWrapper(parts)
    
  book = utils.CBook(fn)
  
  if action == 'view':
    parts.append(CreateTuneSetHTML(book.AllTunes()))
  elif action == 'print':
    pdf = book.GeneratePDF()
    return send_file(pdf, mimetype='application/pdf')
  elif action == 'edit':
    tunes = book.AllTunes()
    tunes = '&'.join(tunes)
    return sets(tunes+'&edit=1')
  elif action == 'delete':
    fn = os.path.join(utils.kSaveLoc, book.name+'.book')
    os.unlink(fn)
    return sets()
  else:
    parts.append(CParagraph("Invalid action %s" % action))
  
  return PageWrapper(parts)

@app.route('/recording/<tune>')
def recording(tune):
  if 'Safari' in request.headers.get('User-Agent'):
    return PageWrapper(['Sorry, cannot serve recordings to Safari without crashing the entire website!<br/><br/>This is a bug I\'m trying to fix...'])
  obj = utils.CTune(tune)
  obj.ReadDatabase()
  recording, mimetype, filename = obj.GetRecording()
  if recording is None:
    return Response()
  return send_file(filename, mimetype=mimetype)

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
clear:both;
white-space:nowrap;
font-size:3.5vw;
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
width:95%;
}
div.tune-break {
clear:both;
height:20px;
}
img.play-tune {
position:absolute;
right:0in;
padding-right:20px;
margin-top:5px;
max-width:5vw;
}
img.notes {
position:relative;
left:-0.1in;
top:0in;
max-width:48%;
min-width:2.5in;
}

/* Chord tables */
table.chords {
position:relative;
top:0in;
right:0in;
font-size:3vw;
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

/* Adjust CSS for narrow devices */
@media only screen and (max-width: 489px) {
img.notes {
width:100%;
max-width:100%;
min-width:100%;
margin-top:5px;
}
table.chords {
clear:both;
left:0in;
right:none;
font-size:5.5vw;
width:95%;
float:left;
}
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

def PageWrapper(body, refresh=None):
  
  # Build html head
  title = "Tune Jam"
  year = time.strftime("%Y", time.localtime())
  head = [
    CTitle(title),
    CMeta("text/html; charset=utf-8", http_equiv="Content-Type"),
    CMeta("Copyright (c) 1999-%s Stephan Deibel" % year, name="Copyright"),
    '<link rel="stylesheet" type="text/css" href="/css/screen" media="screen" />', 
    '<link rel="stylesheet" type="text/css" href="/css/print" media="print" />', 
  ]
  if refresh is not None:
    head.append(CMeta(str(refresh), http_equiv="refresh"))

  head = CHead(head)

  body_div = CBody([CDiv(body, id="body")])
  
  html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">"""
  html += str(CHTML([head, body_div], xmlns="http://www.w3.org/1999/xhtml"))
  
  return html
  
def CreateTuneSetHTML(tunes):
  
  parts = []
  
  parts.append("""<style>
#body {
margin-top:0px;
}  
</style>""")
  printing = False
  for i, tune in enumerate(tunes):
    if i > 0:
      parts.append(CDiv(hclass='tune-break'))
    parts.extend(CreateTuneHTML(tune))
  parts.append(CDiv(hclass='tune-break'))
  
  return PageWrapper(parts)

def CreateTuneSetPDF(name, title, subtitle, tunes):
  book = utils.CSetBook(name, title, subtitle, tunes)
  pdf = book.GeneratePDF(include_index=False)
  return send_file(pdf, mimetype='application/pdf')
  
def CreateTuneHTML(name):
  
  obj = utils.CTune(name)
  try:
    obj.ReadDatabase()
    title = obj.title
  except SystemExit:
    title = "Unknown Tune"

  key_str = obj.GetKeyString()

  recording, mimetype, filename = obj.GetRecording()
  if recording is not None:
    play = CImage(src='/image/speaker_louder_32.png', hclass="play-tune",
                  href='/recording/%s' % name)
  else:
    play = CImage(src='/image/speaker_louder_disabled_32.png', hclass="play-tune")

  notes = '<img src="/png/%s"/ class="notes">' % name
  chords = ChordsToHTML(obj.chords)
  
  tune = CDiv([
    CH([
      title + ' - ' + obj.type.capitalize() + ' - ' + key_str,
      play, 
    ], 1, hclass='tune-title'), 
    notes,
    chords,
  ], hclass='tune')
  
  return [tune]
  
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

  # Kill any old processes (only in outer process)
  if 'TUNEJAM_KILLED_PROCESSES' not in os.environ:
    os.environ['TUNEJAM_KILLED_PROCESSES'] = '1'
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
      time.sleep(3.0)
      
  # Kick off background task process to regenerate books so they
  # are cached and load quickly for users
  if utils.kUseCache:
    def regenerate_books():
      all_books = _get_all_books()
      for book in all_books:
        if book is None:
          continue
        f = open(os.path.join(utils.kDatabaseDir, book.name+'.lock'), 'w')
        f.write('lock-%s' % str(os.getpid()))
        f.close()
      for book in all_books:
        if book is None:
          continue
        book.GeneratePDF()
        try:
          os.unlink(os.path.join(utils.kDatabaseDir, book.name+'.lock'))
        except OSError:
          pass
      return True
    def books_done(result):
      pass
    import multiprocessing
    pool = multiprocessing.Pool(1)
    job = pool.apply_async(regenerate_books, callback=books_done)
  
  # Get a list of all the files to watch to trigger restart (so the
  # PDF books get rebuilt)
  watch_files = []
  files = os.listdir(utils.kDatabaseDir)
  for fn in files:
    if fn.endswith('.book'):
      watch_files.append(os.path.join(utils.kDatabaseDir, fn))
  for section, section_name in utils.kSections:
    if section == 'incomplete':
      continue
    try:
      files = os.listdir(os.path.join(utils.kDatabaseDir, section))
    except OSError:
      continue
    for fn in files:
      if fn.endswith('.spec'):
        watch_files.append(os.path.join(utils.kDatabaseDir, section, fn))
  
  # Start new server
  from os import environ
  if 'WINGDB_ACTIVE' in environ:
    app.debug = False
  if sys.platform == 'darwin':
    host = None
  else:
    host = 'music.cambridgeny.net'
  app.run(host=host, port=60080, use_reloader=True, extra_files=watch_files)

