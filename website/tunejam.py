#!/home/maint/music/bin/python
#coding:utf-8
import sys, os
import time
from html import *
import tempfile
import datetime

if sys.platform == 'darwin':
  sys.path.append(os.path.dirname(os.path.dirname(__file__)))
else:
  sys.path.append('/home/maint/music/src')
  
import utils

from flask import Flask, Response, request, send_file, make_response, redirect
app = Flask(__name__)
app.secret_key = 'TunejamIsAtHubbardHallEachTuesday'
app.config['SESSION_TYPE'] = 'filesystem'

kMenu = [
  ('Home', '/', 'home'), 
  ('Index', '/index', 'index'),
  ('Sets', '/sets', 'sets'),
  ('Sessions', '/sessions', 'session'),
  ('Printing', '/print', 'print'),
]

@app.route('/')
def home():
  parts = []
  
  parts.extend([
    CH("Hubbard Hall Tune Jam", 1),
    CParagraph("Welcome!"),
    CParagraph("This website hosts a collection of tunes "
               "played by the Hubbard Hall Tune Jam Band, an informal group of musicians "
               "from the Cambridge NY area.  We meet every Tuesday from 5:30pm to 7:30pm "
               "in the Beacon Feed (aka Studio) building behind <a href='http://www.hubbardhall.org/'>"
               "Hubbard Hall</a> to play traditional and modern Irish, Scottish, Shetland, "
               "Quebecois, New England, and locally written music by ear.  The sessions are "
               "open to all levels of skill and all instruments, and are followed by a "
               "pot luck dinner."),
    CParagraph("The focus of the site is to facilitate learning tunes by ear, and playing "
               "them together at contra dances and other events.  For each "
               "tune, we have collected a short recording, a chord chart, and a written "
               "melody reminder containing the first few measures of each part."),
    CParagraph("There are currently a total of %i tunes on the site." % TuneCount()), 
    CH("The following resources are available:", 2),
    CList([
      CItem([CText("Tune Index", href='/index'), CNBSP(),
             CText(" -- A list of all the available tunes, organized by type.")]), 
      CItem([CText("Set Sheets", href='/sets'), CNBSP(),
             CText(" -- Create your own sets of tunes, for screen display or printing.")]), 
      CItem([CText("Sessions", href='/sessions'), CNBSP(),
             CText(" -- Sharable set lists that auto-update on each participating device.")]),
      CItem([CText("Printable Books", href='/print'), CNBSP(),
             CText(" -- Premade books in several formats, with index.")]), 
      CItem([CText("Email List", href='http://cambridgeny.net/mailman/listinfo/tunejam'), CNBSP(),
             CText(" -- The Hubbard Hall Tune Jam email list.")]),
    ]),
    CBreak(), 
    CParagraph("This website was designed and built by Stephan Deibel, with content "
               "contributed by Bliss and Robbie McIntosh.")
  ])
      
  return PageWrapper(parts, 'home')

@app.route('/index')
def music():
  parts = []
  parts.append(CH("Tune Index", 1))
  parts.append(CParagraph("This lists all the %i tunes in the database so far.  If there is a recording, " % TuneCount() + 
                          "you can click on the speaker icon to hear it.  Click on the tune name "
                          "to view the chords and melody reminders."))
  tunes = utils.GetTuneIndex(True)

  sections = tunes.keys()
  sections.sort()
  if 'incomplete'in sections:
    sections.remove('incomplete')
    sections.append('incomplete')
  for section in sections:
    parts.append(CH(utils.kSectionTitles[section], 2))
    if section == 'incomplete':
      parts.append(CParagraph("The tunes in this section do not yet have completed chords and/or "
                              "melody reminders."))
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
  return PageWrapper(parts, 'index')

@app.route('/sets', methods=['GET', 'POST'])
@app.route('/sets/')
@app.route('/sets/<spec>')
@app.route('/sets/sid/<sid>')
@app.route('/sets/sid/<sid>/edit/<spec>')
def sets(spec=None, sid=None):
  
  editor = CheckPassword()
  
  error = None
  preload_tunes = []

  if sid is not None:
    s = utils.CSession(sid)
    s.ReadSession()
    
  if spec is not None:
    args = spec.split('&')
    tunes = []
    _print = False
    save = False
    edit = '/edit/' in request.url and spec is not None
    title = ''
    subtitle = ''
    pagetype = 'both'
    
    # XXX This is a mess and needs to be cleaned up
    for arg in args:
      if arg == 'print=1':
        _print = True
      elif arg == 'save=1':
        save = True
      elif arg.startswith('title='):
        title = arg[len('title='):].strip()
      elif arg.startswith('subtitle='):
        subtitle = arg[len('subtitle='):].strip()
      elif arg.startswith('pagetype='):
        pagetype = arg[len('pagetype='):].strip()
      elif arg.startswith('session='):
        sid = arg[len('session='):].strip()
        s = utils.CSession(sid)
        s.ReadSession()
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
        book = '%s\n%s\n%s\nhttp://cambridgeny.net/index\n--\n' % (
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
        parts = CreateTuneSetHTML(tunes, pagetype)

        if sid is not None:
          parts.insert(0, CText("Set from Session: %s" % s.title, bold=1))
          parts.extend([
            CBreak(2),
            CText("Return to session %s" % s.title, href='/session/%s' % sid, hclass='bottom-menu-left'),
          ])
          if editor:
            parts.extend([
              CText("Delete this set", href='/session/%s/delete/%s' % (sid, '&'.join(tunes)), hclass='bottom-menu-right'),
            ])
          parts.append(CBreak(2))
          
        return PageWrapper(parts)

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
function SubmitTunes(sid, old_set) {
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
  if ($("input:radio[name=pagetype]:checked").val() == "notes") {
    tunes = tunes + "&pagetype=notes";
  }
  else if ($("input:radio[name=pagetype]:checked").val() == "chords") {
    tunes = tunes + "&pagetype=chords";
  }
  if (sid == "") {
    window.location.href= "/sets/" + tunes;
  } else if (old_set == "") {
    window.location.href= "/session/" + sid + "/add/" + tunes;
  } else {
    window.location.href= "/session/" + sid + "/add/" + tunes + "/replace/" + old_set;
  }
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
        $('#include-radios').css("display", "none");
        } else {
            $('#saveitems').css("display", "none");
        $('#include-radios').css("display", "");
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
                          "button to select three random tunes.  Then "
                          "press Submit to generate the set:"))
  
  
  section_options = [
    ('all', 'All')
  ]

  keys = utils.kSectionTitles.keys()
  keys.append('ax4')
  keys.sort()
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
  tunes = utils.GetTuneIndex(include_incomplete=True)
  for section in tunes:
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
        continue
      if visible:
        all_tunes.append((title, CItem(title, id='tune_%s' % tune.replace('_', '+'),
                                       hclass='ui-state-default %s' % section)))
      else:
        all_tunes.append((title, CItem(title, id='tune_%s' % tune.replace('_', '+'),
                                       hclass='ui-state-default %s' % section,
                                       style="display:none")))
  selected_tunes = []
  for tune in preload_tunes:
    obj = utils.CTune(tune)
    obj.ReadDatabase()
    title = '%s - %s - %s' % (obj.title, obj.type.capitalize(), obj.GetKeyString())
    selected_tunes.append(CItem(title, id='tune_%s' % tune.replace('_', '+'),
                                 hclass='ui-state-default %s' % obj.type))

  all_tunes.sort()
  all_tunes = [i[1] for i in all_tunes]
  
  tunes_list = CDiv(CList(all_tunes, id='alltunes', hclass='connectedSortable'), hclass='scroll')
  selected_list = CDiv(CList([selected_tunes], id='selectedtunes', hclass='connectedSortable'), hclass='scroll')
  
  parts.append(CTable([
    CTR([CText("Available:"), CText("Selected:")]), 
    CTR([tunes_list, selected_list])
  ]))
  parts.append(CParagraph("On mobile devices, scroll with two fingers, or by dragging an item down, or by entering a text filter to shorten the list.", hclass="clear"))
  
  # Creating set outside of session
  if sid is None:
    parts.append(CForm([
      CInput(type='checkbox', name="print", value="1", checked="", id="print-checkbox"),
      CText("Generate printable pages (PDF)"), 
      CDiv([
      CText("Include:"), CNBSP(1), 
      CInput(type='radio', name='pagetype', value='chords', checked=''), 
      CText("Chords"), CNBSP(), 
      CInput(type='radio', name='pagetype', value='notes', checked=''),
      CText("Notes"), CNBSP(), 
      CInput(type='radio', name='pagetype', value='both', checked='1'),
      CText("Both"), 
      CBreak(),
      ], id='include-radios'), 
      #CBreak(), 
      #CInput(type='checkbox', name="save", value="1", checked="", id="save-checkbox"),
      #CText("Save this set"),
      CTable([
        [
          CTD(CText("Title:", bold=1), style="width:5em; padding-top:5px;"), 
          CInput(type='TEXT', name='title', id='title', maxlength="65", style="width:40em"),
        ],
        [
          CTD(CText("Subtitle:", bold=1), style="width:5em;"), 
          CInput(type='TEXT', name='subtitle', id='subtitle', maxlength="65", style="width:40em"),
        ], 
      ], id='saveitems'), 
      CBreak(), 
      CInput(type='button', value="Create Set", onclick="SubmitTunes('', '');"),
      CInput(type='button', value="Clear Selected", onclick='ClearTunes();'), 
    ], id='tunesform'))
    
  # Adding a spec to a session
  elif spec is None:
    parts.append(CForm([
      CInput(type='button', value="Add Set", onclick="SubmitTunes('%s', '');" % sid),
      CInput(type='button', value="Clear Selected", onclick='ClearTunes();'), 
    ], id='sessionsetform'))
  
  # Editing a spec in a session
  else:
    parts.append(CForm([
      CInput(type='button', value="Update Set", onclick="SubmitTunes('%s', '%s');" % (sid, spec)),
      CInput(type='button', value="Clear Selected", onclick='ClearTunes();'), 
    ], id='sessionsetform'))
    
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
  
  if sid is not None:
    parts.extend([
      CBreak(2),
      CText("Return to session %s" % s.title, href='/session/%s' % sid), 
      CBreak(2)
    ])
    section = 'session'
  else:
    section = 'sets'
    
  return PageWrapper(parts, section)

@app.route('/tune/<tune>')
def tune(tune):
  parts = []
  parts.extend(CreateTuneHTML(tune))
  return PageWrapper(parts)

@app.route('/png/<tune>')
def png(tune):
  tune = utils.CTune(tune)
  png_file = tune.MakeNotesPNGFile(density=600)
  return send_file(png_file, mimetype='image/png')

def get_all_books():
  import allbook
  import flipbook
  retval = [
    allbook.CAllBook(),
    allbook.CAllBookBySection(),
    allbook.CAllBookByTime(),
    None, 
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
      CParagraph("The following printable books are available in PDF format:"),
    ])
    
    for book in get_all_books():
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

  return PageWrapper(parts, 'print', refresh=refresh)

@app.route('/saved/<action>/<book>')
def saved(action=None, book=None):
  parts = []
  if action is None or book is None:
    parts.append("Book list here")
    return PageWrapper(parts, 'sets')

  fn = os.path.join(utils.kDatabaseDir, book+'.book')
  if not os.path.isfile(fn):
    fn = os.path.join(utils.kSaveLoc, book+'.book')
  if not os.path.isfile(fn):
    parts.append(CParagraph("Book %s does not exist" % book))
    return PageWrapper(parts, 'sets')
    
  book = utils.CBook(fn)
  
  if action == 'view':
    parts.append(CreateTuneSetHTML(book.AllTunes()))
  elif action == 'print':
    pdf = book.GeneratePDF(generate=True)
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
    parts.append(CParagraph("Invalid action %s" % action, 'sets'))
  
  return PageWrapper(parts)

@app.route('/recording/<tune>')
def recording(tune):
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
}
p {
font-size:110%;
padding-top:0.5em;
padding-bottom:0.5em;
}
span, a, li, b, i {
font-size:110%;
}
#header {
overflow:hidden;
}
#main-menu {
padding-top:0.4em;
padding-bottom:0.8em;
}
.menu-item {
text-decoration:none;
color:#005511;
padding-bottom:0.5em;
}
.menu-item-current {
color:#dd1111;
text-decoration:none;
border-bottom: 1px solid #ff0000;
}
#set-menu {
width:100%;
border:1px solid #ff0000;
}
.bottom-menu-left {
}
.bottom-menu-right {
float:right;
}
@media only screen and (max-width: 589px) {
.bottom-menu-left {
float:left;
clear:both;
}
.bottom-menu-right {
clear:both;
float:left;
padding-top:30px;
padding-bottom:20px;
}
}
ul {
list-style-type:none;
padding-left:0.1em;
}
h1 {
color:#044300;
}
h1.tune-title {
clear:both;
white-space:nowrap;
font-size:3.5vw;
color:#000000;
}
h1.long-tune-title {
clear:both;
white-space:nowrap;
font-size:2.6vw;
color:#000000;
}
h1.extra-long-tune-title {
clear:both;
white-space:nowrap;
font-size:2.5vw;
color:#000000;
}
h2 {
padding-top:0.7em;
padding-bottom:0.5em;
color:#004400;
}
a {
outline-style:none;
}
#body {
margin:12px;
max-width:1079px;
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
max-width:45%;
min-width:2.5in;
}
img.notes-only {
width:100%;
max-width:100%;
min-width:100%;
margin-top:5px;
}

/* Chord tables */
table.chords {
position:relative;
top:0in;
right:0in;
font-size:2.8vw;
border:0px;  /* For Chrome and Safari */
border-left:2px solid #000;
border-right:2px solid #000;
margin-left:4px;
margin-top:20px;
float:right;
}
table.chords-only {
clear:both;
left:0in;
right:none;
font-size:5.0vw;
width:95%;
float:left;
margin-top:2vw;
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

@app.route('/sessions')
@app.route('/sessions/delete/<delete>')
@app.route('/sessions/undelete/<undelete>')
def sessions(delete=None, undelete=None):
  
  editor = CheckPassword()
   
  if delete and editor:
    utils.DeleteSession(delete)
    return redirect('/sessions', code=303)
  if undelete and editor:
    utils.DeleteSession(undelete, undelete=True)
    return redirect('/sessions', code=303)
  
  utils.PurgeDeletedSessions()
  
  parts = []
  parts.append(CH("Sessions", 1))
  
  parts.append("Sessions make it easier to play together as a group.  The group "
               "leader creates the session, adds sets to it, and specifies which set "
               "is currently being played.  Other musicians can watch the session "
               "and all the participating devices (ipads, phones, laptops, etc) will update "
               "as the session changes.")

  sessions = utils.ReadSessions()
  sessions.sort(key=lambda s:s.title)

  parts.append(CParagraph(CText("The following sessions are active:", bold=1)))

  if sessions:
    for session in sessions:
      parts.extend([
        CText(session.title, href='/session/%s' % session.name), 
        CBreak(), 
      ])
  else:
    parts.append(CParagraph(CText("There are no active sessions right now.", italic=1)))
    
  if not editor:
    parts.append(LoginButton('/sessions'))
    return PageWrapper(parts, 'session')

  parts.append(CForm([
    CBreak(), 
    CText("Create a New Session:", bold=1),
    CBreak(1),
    CText("Title:"), CInput(type='TEXT', name='title', id='session-title', size=100, maxlength=200), 
    CBreak(2),
    CInput(type='SUBMIT', value='Create'), 
  ], action='/session', method='POST', id="session-form"))
  
  parts.append(CBreak())
  
  inactive = utils.ReadSessions(deleted=True)
  if inactive:
    parts.append(CParagraph(CText("Recently deleted sessions:", bold=1)))
    for session in inactive:
      expires = time.strftime('%x %X', time.localtime(session.GetExpiration()))
      parts.extend([
        CSpan(session.title+' - Expires '+expires+' - '),
        CText("Undelete", href='/sessions/undelete/%s' % session.name),
        CBreak(), 
      ])
  
  parts.append(LogoutButton('/sessions'))
  parts.append(CBreak())
  
  return PageWrapper(parts, 'session')

@app.route('/session', methods=['POST'])
@app.route('/session/<sid>')
@app.route('/session/<sid>/add/<add>')
@app.route('/session/<sid>/add/<add>/replace/<old>')
@app.route('/session/<sid>/delete/<delete>')
@app.route('/session/<sid>/current/<curr>')
def session(sid=None, add=None, delete=None, curr=None, old=None):

  editor = CheckPassword()
  
  def get_set_title(s):
    titles = []
    for tid in s.split('&'):
      tune = utils.CTune(tid)
      tune.ReadDatabase()
      titles.append(tune.title)
    titles = ' - '.join(titles)
    return titles
  
  if request.environ['REQUEST_METHOD'] == 'POST':
    title = request.form['title']
    sid = utils.CreateSession(title)
    
  session = utils.CSession(sid)
  session.ReadSession()
  
  if add is not None and editor:
    if old is not None:
      pos = session.sets.index(old)
      session.sets[pos] = add
    else:
      session.sets.append(add)
    session.WriteSession()
    return redirect('/session/%s' % sid, code=303)
  
  if delete is not None and editor:
    session.sets.remove(delete)
    if session.current_set == delete:
      session.current_set = ''
    session.WriteSession()
    return redirect('/session/%s' % sid, code=303)
    
  if curr is not None and editor:
    session.current_set = curr
    session.WriteSession()
    return redirect('/session/%s' % sid, code=303)
    
  if session.title:
    title = session.title
  else:
    title = "Deleted"
    
  parts = []
  parts.append(CH("Session: %s" % session.title, 1))
  parts.append(CParagraph(""))
  
  if not session.title:
    parts.extend([
      CParagraph("This session has been deleted"),
      CBreak(2), 
      CText('Return to session list', href='/sessions'),
    ])
    return PageWrapper(parts, 'session')
    
  parts.extend(SessionReloader(sid))
  
  if not session.current_set:
    c = 'None'
  else:
    c = get_set_title(session.current_set)

  parts.extend([
    CText("Now Playing: ", bold=1), 
    CSpan(c),
    CBreak(), 
    CText("Watch Current Set:", bold=1),
    CNBSP(),
    CText("Notes", href='/watch/notes/%s' % sid), 
    CNBSP(), 
    CText("Chords", href='/watch/chords/%s' % sid), 
    CNBSP(), 
    CText("Both", href='/watch/%s' % sid),
    CBreak(), 
  ])
  
  parts.append(CH("Available Sets:", 2))
  if not session.sets:
    parts.append(CText("No sets have been defined for this session", italic=1))
  else:
    if editor:
      parts.append(CParagraph("Click on a red dot change the current set.  View a set with "
                              "melody reminders, chords, or both.  To delete a set, view it "
                              "and use the link at the bottom of its page."))
    else:
      parts.append(CParagraph("View a particular set with melody reminders, chords, or both:"))

    for s in session.sets:
      titles = get_set_title(s)
      
      url = '/sets/%s' % s
      if s == session.current_set:
        parts.append(CImage(src='/image/check-mark.png', style="height:1.0em"))
      elif editor:
        parts.append(CImage(src='/image/red-square.png', href="/session/%s/current/%s" % (sid, s),
                            style="height:1.0em"))
      else:
        parts.append(CImage(src='/image/red-square.png', style="height:1.0em"))
        
      parts.extend([
        CNBSP(2), 
        CText("Notes", href=url+'&pagetype=notes&session=%s' % sid), 
        CNBSP(), 
        CText("Chords", href=url+'&pagetype=chords&session=%s' % sid), 
        CNBSP(), 
        CText("Both", href=url+'&session=%s' % sid),
        CNBSP(2), 
        CSpan(titles), 
      ])
      
      if editor:
        parts.extend([
          CText(' - '),
          CText("Edit", href='/sets/sid/%s/edit/%s' % (sid, s)),
          CText(' - '), 
          CText("Delete", href='/session/%s/delete/%s' % (sid, s)),
        ])
      
      parts.append(CBreak())
    
  if editor:
    parts.append(CBreak(2))
    parts.append(CForm([
      CInput(type="SUBMIT", value="Add a Set"), 
    ], action='/sets/sid/%s' % sid, method='GET', id="add-set-form"))
  
  parts.extend([
    CBreak(), 
    CText('Return to session list', href='/sessions'),
    CBreak(), 
  ])
  if editor:
    parts.extend([               
      CText('Delete this session', href='/sessions/delete/%s' % session.name),
      LogoutButton('/session/%s' % session.name),
    ])
  else:
    parts.append(CBreak())
    parts.append(LoginButton('/session/%s' % session.name))

  return PageWrapper(parts, 'session')

@app.route('/watch/<sid>')
@app.route('/watch/<type>/<sid>')
def watch(sid, type=None):
  
  if type is None:
    type = 'both'
    
  session = utils.CSession(sid)
  session.ReadSession()

  if session.title:
    title = session.title
  else:
    title = "Deleted"
    
  parts = []
  
  parts.extend(SessionReloader(sid))
  
  parts.append(CText("Watching Session: %s" % title, bold=1))
  parts.append(CBreak(2))
  
  if not session.title:
    parts.append(CText("This session has been deleted", italic=1))
  elif not session.current_set:
    parts.append(CText("Please wait for a current set to be established", italic=1))
  else:
    tunes = session.current_set.split('&')
    
    import hashlib
    md5sum = hashlib.md5()
    for tune in tunes:
      md5sum.update(tune)
    name = 'C-' + md5sum.hexdigest()
    
    parts.extend(CreateTuneSetHTML(tunes, type))
  
  if not session.title:
    parts.append(CBreak(2))
    parts.append(CText("Return to session list", href="/sessions"))
  else:
    parts.append(CBreak(2))
    parts.append(CText("Return to set list", href="/session/%s" % sid))
  parts.append(CBreak())
  
  return PageWrapper(parts)

@app.route('/authorize/<path:target>')
def authorize(target):

  editor = CheckPassword()
  if editor:
    return redirect('/'+target, code=303)
    
  parts = []

  parts.extend([
    CH("Please Enter Password", 2), 
    CParagraph("You need to prove you're human to use this part of the site.  The password is 'tunejam'."),
    CForm([
      CText("Password:"),
      CInput(type="HIDDEN", name='target', value=target), 
      CInput(type='PASSWORD', name='pw', size=30, maxlength=60, autofocus=1), 
      CBreak(2),
      CInput(type='SUBMIT', value='Submit'), 
    ], action='/login', method='POST'), 
  ])
  
  return PageWrapper(parts, 'session')

@app.route('/login', methods=['POST'])
def login():

  from flask import session
  
  pw = request.form['pw'].lower()
  target = request.form['target']
  
  if 'tune'not in pw or 'jam' not in pw:
    parts = CheckPassword()
    return PageWrapper(parts, 'session')
  
  session['password'] = pw
  
  return redirect(target, code=303)

@app.route('/logout/<path:target>')
def logout(target):
  Logout()
  return redirect('/'+target, code=303)

@app.route('/ajax/session/<sid>/current')
def ajax_session_current(sid):
  s = utils.CSession(sid)
  s.ReadSession()
  return s.current_set + '&' + str(len(s.sets))

def CheckPassword():
  
  from flask import session
  pw = session.get('password', '').lower()
  if 'tune' in pw and 'jam' in pw:
    return True
  else:
    return False

def Logout():
  
  from flask import session
  if 'password' in session:
    del session['password']
  
def SessionReloader(sid):

  s = utils.CSession(sid)
  s.ReadSession()
  
  parts = []
  
  parts.append("""<script src="//code.jquery.com/jquery-1.12.0.min.js"></script>
<script src="//code.jquery.com/ui/1.11.4/jquery-ui.min.js"></script>
""")
  
  parts.extend([
    """<script>
function CheckSession() {
  $.ajax({
    url: "/ajax/session/%s/current",
    cache: false,
    success: function(txt){
      if (txt.trim() != "%s") {
        location.reload();
      }
    }
  });
}
$(document).ready(function() {
   setInterval(CheckSession, 5000);
});
</script>""" % (sid, s.current_set + '&' + str(len(s.sets)))
             
  ])
  
  return parts

def LoginButton(target):
  
  return CForm([
      CBreak(),
      CText("Log in to create or edit sessions", bold=1),
      CBreak(2), 
      CInput(type='SUBMIT', value="Login"),
      CBreak(2), 
    ], action='/authorize%s' % target, method='GET')
  
def LogoutButton(target):
  
  return CForm([
      CBreak(2),
      CInput(type='SUBMIT', value="Logout"),
      CBreak(2), 
    ], action='/logout%s' % target, method='GET')
  
def PageWrapper(body, section=None, refresh=None):
  
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

  if section is not None:
    
    items = []
    for title, url, msection in kMenu:
      if msection == section:
        iclass = 'menu-item-current'
      else:
        iclass = 'menu-item'
      items.append(CText(title, href=url, hclass=iclass))
      items.append(CNBSP())
  
    body = [
      CDiv([CImage(src='/image/header.jpg')], id='header'), 
      CDiv(items, id='main-menu')
    ] + body + [
      CBreak(2), 
      CHR(),
      CText('Maintained by Stephan Deibel'),
    ]
  
  body_div = CBody([CDiv(body, id="body")])
  
  html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">"""
  html += str(CHTML([head, body_div], xmlns="http://www.w3.org/1999/xhtml"))
  
  return html
  
def CreateTuneSetHTML(tunes, pagetype='both'):
  
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
    parts.extend(CreateTuneHTML(tune, pagetype))
  parts.append(CDiv(hclass='tune-break'))
  
  return parts

def CreateTuneSetPDF(name, title, subtitle, tunes):
  book = utils.CSetBook(name, title, subtitle, tunes)
  pdf = book.GeneratePDF(include_index=False, generate=True)
  return send_file(pdf, mimetype='application/pdf')
  
def CreateTuneHTML(name, pagetype='both'):
  
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

  if pagetype == 'both':
    if not obj.chords and not obj.notes:
      notes = ''
      chords = CDiv(CText("Notes and chords are not yet available for this tune", bold=1, italic=1),
                    style="padding-top:10px")
    else:
      if obj.notes:
        notes = '<img src="/png/%s"/ class="notes">' % name
      else:
        notes = CText("Notes are not yet available for this tune", bold=1)
      if obj.chords:
        chords = ChordsToHTML(obj.chords)
      else:
        chords = ChordsToHTML('Chords not yet available')
  elif pagetype == 'notes':
    if obj.notes:
      notes = '<img src="/png/%s"/ class="notes-only">' % name
    else:
      notes = CDiv(CText("Notes are not yet available for this tune", bold=1, italic=1),
                   style="padding-top:10px")
    chords = ''
  elif pagetype == 'chords':
    notes = ''
    if obj.chords:
      chords = ChordsToHTML(obj.chords, tclass='chords-only')
    else:
      chords = CDiv(CText("Chords are not yet available for this tune", bold=1, italic=1),
                   style="padding-top:10px")

  if len(title) > 50:
    tclass = 'extra-long-tune-title'
  elif len(title) > 35:
    tclass = 'long-tune-title'
  else:
    tclass = 'tune-title'
    
  tune = CDiv([
    CH([
      title + ' - ' + obj.type.capitalize() + ' - ' + key_str,
      play, 
    ], 1, hclass=tclass), 
    notes,
    chords,
  ], hclass='tune')
  
  return [tune]
  
def ChordsToHTML(chords, tclass='chords'):
    
    if not isinstance(chords, list):
        chords = utils.ParseChords(chords)
        
    html = []
    part_class = 'even'
    max_line_len = 0
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
                max_line_len = max(max_line_len, len(row))
                html.append(CTR(row, hclass=part_class))
                row = []
            elif len(row) == 6:
                max_line_len = max(max_line_len, len(row))
                html.append(CTR(row, hclass=part_class))
                row = []
        if row:
            html.append(CTR(row, hclass=part_class))
            
        if part_class == 'even':
            part_class = 'odd'
        else:
            part_class = 'even'
        
    for row in html:
      while len(row.body) < max_line_len:
        row.append(CTD(''))
        
    html = CTable(html, width=None, hclass=tclass)
    
    return html
  
gTuneCountCache = [0]
def TuneCount():

  if gTuneCountCache[0] != 0:
    return gTuneCountCache[0]
  
  tunes = utils.GetTuneIndex(True)
  tune_count = 0
  for section in tunes:
    tune_count += len(tunes[section])

  gTuneCountCache[0] = tune_count
  return tune_count

TuneCount._cache_count = None
    
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
      
  kWatchFiles = False  
  if kWatchFiles:
    
    # Kick off background task process to regenerate books so they
    # are cached and load quickly for users
    if utils.kUseCache:
      import crontask
      def books_done(result):
        pass
      import multiprocessing
      pool = multiprocessing.Pool(1)
      job = pool.apply_async(crontask.regenerate_books, callback=books_done)
    
    # Get a list of all the files to watch to trigger restart (so the
    # PDF books get rebuilt)
    watch_files = set()
    for book in get_all_books():
      if book is None:
        continue
      watch_files.update(utils.GetWatchFiles(book))
  
  else:
    watch_files = []
    
  # Start new server
  from os import environ
  if 'WINGDB_ACTIVE' in environ:
    app.debug = False
  if sys.platform == 'darwin':
    host = '0.0.0.0'
  else:
    host = 'music.cambridgeny.net'
  app.run(host=host, port=60080, use_reloader=True, extra_files=list(watch_files))

