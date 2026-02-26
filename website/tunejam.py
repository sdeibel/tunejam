#!/home/maint/music/bin/python
#coding:utf-8
import sys, os
import time
import struct
from html import *
import tempfile
import datetime
import random
import collections
import hashlib
import smtplib
from email.mime.text import MIMEText

try:
  import wingdbstub
except:
  pass

if sys.platform == 'darwin':
  sys.path.append(os.path.dirname(os.path.dirname(__file__)))
else:
  sys.path.append('/home/maint/music/src')
  
import utils

from datetime import timedelta
from flask import Flask, Response, request, send_file, make_response, redirect, session, jsonify, abort
app = Flask(__name__)
app.secret_key = 'TunejamIsAtHubbardHallEachTuesday'
app.config['SESSION_TYPE'] = 'filesystem'
app.permanent_session_lifetime = timedelta(days=30)

kSiteVersion = '3.0'

# Email config file path (src/config/email.conf)
kEmailConf = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'email.conf')

# Token storage directory (auto-created)
kTokenDir = os.path.join(os.path.dirname(__file__), 'tokens')
if not os.path.exists(kTokenDir):
  os.makedirs(kTokenDir)

# Login log
kLogDir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'log')
if not os.path.exists(kLogDir):
  os.makedirs(kLogDir)
kLoginLog = os.path.join(kLogDir, 'logins.log')

# Session and token lifetimes
kSessionLifetimeDays = 30
kTokenExpirySeconds = 3600
kLoginLogMaxBytes = 1024 * 1024  # 1MB
kMaxEmailsPerHour = 3
kMaxGlobalEmailsPerHour = 60

# Capability constants
kCapManageEvents = 'manage_events'
kCapEditTunes = 'edit_tunes'
kCapManageCache = 'manage_cache'

# Permission levels
kPermissions = {
  'regular': {kCapManageEvents},
  'admin': {kCapManageEvents, kCapEditTunes, kCapManageCache},
}

kMenu = [
  ('Home', '/', 'home'), 
  ('Index', '/index', 'index'),
  ('Sets', '/sets', 'sets'),
  ('Events', '/events', 'event'),
  ('Books', '/print', 'print'),
  ('Sessions', '/sessions', 'session'),
  ('Local', '/index/sheet', 'local'),
  ('Dev', '/dev', 'dev')
]

@app.route('/')
def home():
  parts = []
  
  total_tunes = TuneCount(include_incomplete=True)
  total_complete = TuneCount(include_incomplete=False)
  total_incomplete = total_tunes - total_complete
  
  parts.extend([
    CH("Cambridge NY Traditional Music", 1),
    CParagraph("Welcome!"),
    CParagraph("This website hosts a collection of traditional tunes played by musicians "
               "around Cambridge NY. The focus of the site is to facilitate learning tunes by ear, and playing "
               "them together at sessions, contra dances, fund-raisers, and other events.  "),
    CParagraph("For each tune, we have collected a short recording, a chord chart, and a written "
               "melody reminder containing the first few measures of each part.  Where "
               "available, we've also listed author, origin, a brief history of the tune, and "
               "links to additional information."),
    CParagraph("There are currently a total of <a href='/index/title'>%i completed tunes</a> on the site.  In addition, <a href='/dev'>%i " % (total_complete, total_incomplete) +
               "partial listings</a> have been entered."), 
    CH("&#9834; The following resources are available:", 2),
    CList([
      CItem([CText("Tune Index", href='/index'), CNBSP(),
             CText(" -- A list of all the tunes, sortable by <a href='/index/title'>title<a>, "
                   "<a href='/index/meter'>time signature<a>, <a href='/index/type'>type<a>, "
                   "<a href='/index/author'>author<a>, and <a href='/index/origin'>origin<a>.")]), 
      CItem([CText("Set Sheets", href='/sets'), CNBSP(),
             CText(" -- Create your own sets of tunes, for screen display or printing.")]), 
      CItem([CText("Events", href='/events'), CNBSP(),
             CText(" -- Sharable set lists that auto-update on each participating device.")]),
      CItem([CText("Printable Books", href='/print'), CNBSP(),
             CText(" -- Premade books in several formats, with index.")]), 
      CItem([CText("Sessions", href='/sessions'), CNBSP(),
             CText(" -- A listing of area traditional music sessions.")]),
      CItem([CText("Local Tunes", href='/index/sheet'), CNBSP(),
             CText(" -- Sheet music for locally written tunes.")]),
      CItem([CText("Development Page", href='/dev'), CNBSP(),
             CText(" -- How to help improve this site.")]), 
    ]),
    CBreak(), 
    CParagraph("This website was designed and built by Stephan Deibel, with content "
               "contributed by Bliss and Robbie McIntosh.")
  ])
      
  return PageWrapper(parts, 'home')

@app.route('/sessions')
def sessions():
  parts = []
    
  parts.extend([
    CH("Cambridge NY Area Sessions", 1),
    CParagraph("This is a list of the regularly occurring traditional music sessions within about "
               "45 minutes of Cambridge NY that share significant overlap with the tune "
               "repertoire hosted on this website:"), 
    CList([
      CItem([CText('&#9834; '), CText("Hubbard Hall Tune Jam", href='/'), CNBSP(), CText('--'), CNBSP(), 
             CText("Every Tuesday 5:30pm-7:30pm in the Beacon Feed (aka Studio) building "
                   "behind <a href='http://www.hubbardhall.org/'>Hubbard Hall</a> in Cambridge NY.  The "
                   "group focuses on learning traditional and modern Irish, Scottish, Shetland, "
                   "Quebecois, New England, and locally written music by ear (this website was created "
                   "for this purpose).  Open to all levels of skill and all instruments, and each meeting is followed "
                   "by a pot luck dinner.  Join the <a href='http://cambridgeny.net/mailman/listinfo/tunejam'>"
                   "email list</a> for more information and announcements."),
             CBreak(2), 
             ]), 
      CItem([CText('&#9834; '), CText("Saratoga Pan-Celtic Session", href='https://www.facebook.com/Saratoga-Pan-Celtic-Session-135466146471469/'), CNBSP(), CText('--'), CNBSP(),
             CText("Almost every Wednesday 7pm-11pm at The Parting Glass in Saratoga NY. "
                    "This is a fun, open group of mostly amateur musicians that enjoy playing "
                    "Quebecois, Scottish and Cape Breton, as well as Irish fiddle tunes."), 
             CBreak(2), 
             ]), 
      CItem([CText('&#9834; '), CText("North Adams Session", href='https://thesession.org/sessions/3549'), CNBSP(), CText('--'), CNBSP(),
             CText("Every Saturday 10:30am until 2 or 3pm at the Lickety Split Coffee Shop "
                   "inside Mass MoCA. They play mostly Contra and New England fiddle music. "
                   "Sheet music is OK. Beginners may find it challenging but all are welcome."), 
             CBreak(2), 
             ]), 
    ]),
    CParagraph("See also <a href='https://thesession.org/sessions'>thesession.org</a>")
  ])
      
  return PageWrapper(parts, 'session')

def _index_header(itype):
  
  parts = []

  if HasCapability(kCapEditTunes):
    parts.append(CDiv('<a href="/tune/new" class="green-button">New Tune</a>', style='float:right'))

  parts.append(CText('&#9834; Sort Index By:', bold=1))
  parts.append(CNBSP())
  parts.append(CText('Title', href='/index/title', bold=itype=='title'))
  parts.append(CNBSP())
  parts.append(CText('Time Signature', href='/index/meter', bold=itype=='meter'))
  parts.append(CNBSP())
  parts.append(CText('Type', href='/index/type', bold=itype=='type'))
  parts.append(CNBSP())
  parts.append(CText('Author', href='/index/author', bold=itype=='author'))
  parts.append(CNBSP())
  parts.append(CText('Origin', href='/index/origin', bold=itype=='origin'))
  parts.append(CNBSP())
  parts.append(CText('Key', href='/index/key', bold=itype=='key'))
  parts.append(CBreak(2))

  sorting = itype
  if itype == 'key':
    parts.append(CH("Index by Key", 1))
    sorting = 'key'
  elif itype == 'meter':
    parts.append(CH("Index by Time Signature", 1))
    sorting = 'time signature'
  elif itype == 'author':
    parts.append(CH("Index by Author", 1))
  elif itype == 'title':
    parts.append(CH("Index by Title", 1))
  elif itype == 'origin':
    parts.append(CH("Index by Origin", 1))
  else:
      parts.append(CH("Index by Type", 1))
    
  parts.append(CParagraph("This lists the %i completed tunes in the database so far, sorted by %s. "
                          "If there is a recording, you can click on the speaker icon to hear it. "
                          "Click on the tune name to view the chords and melody reminders." % (TuneCount(False), sorting)))

  return parts
  
@app.route('/index/type')
def index_type():
  session['index_sort'] = 'type'
  tunes = utils.GetTuneIndex(False)

  parts = _index_header('type')

  sections = tunes.keys()
  sections.sort()
  for section in sections:
    parts.append(CH(utils.kSectionTitles[section], 2, hclass='index-section'))
    group_items = []
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.GetKeyString()
      title_html = _index_title_html(obj, title)
      group_items.extend(title_html)
    parts.append(CDiv(group_items, hclass='index-group'))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'index', eye_candy_image='index-type')

@app.route('/index/meter')
def index_meter():
  session['index_sort'] = 'meter'

  parts = _index_header('meter')

  tunes = utils.GetTuneIndex(False)

  sections = tunes.keys()
  time_sigs = collections.defaultdict(set)
  for section in sections:
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.GetKeyString()
      title_html = _index_title_html(obj, title)
      meter = obj.meter
      if meter in ('2/4', '4/4', 'C'):
        meter = "C, 2/4, and 4/4"
      time_sigs[meter].add((title, tuple([str(t) for t in title_html])))
      
  times = time_sigs.keys()
  times.sort()
  for t in time_sigs:
    parts.append(CH(t, 2, hclass='index-section'))
    group_items = []
    tunes = time_sigs[t]
    for title, title_html in sorted(tunes):
      group_items.extend(title_html)
    parts.append(CDiv(group_items, hclass='index-group'))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'index', eye_candy_image='index-time')

@app.route('/index/origin')
def index_origin():
  session['index_sort'] = 'origin'

  parts = _index_header('origin')

  tunes = utils.GetTuneIndex(False)

  sections = tunes.keys()
  origins = collections.defaultdict(set)
  for section in sections:
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.Type() + ' - ' + obj.GetKeyString()
      title_html = _index_title_html(obj, title)
      origin = obj.origin
      if not origin:
        origin = 'To Be Determined'
      origins[origin].add((title, tuple([str(t) for t in title_html])))
      
  for origin in sorted(origins):
    parts.append(CH(origin, 2, hclass='index-section'))
    group_items = []
    for title, title_html in sorted(origins[origin]):
      group_items.extend(title_html)
    parts.append(CDiv(group_items, hclass='index-group'))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'index', eye_candy_image='index-origin')

@app.route('/index/key')
def index_key():
  session['index_sort'] = 'key'

  parts = _index_header('key')

  tunes = utils.GetTuneIndex(False)

  keys = collections.defaultdict(set)
  sections = tunes.keys()
  for section in sections:
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.Type()
      title_html = _index_title_html(obj, title)
      key_str = obj.GetKeyString()
      if '/' in obj.key:
        key_str = 'Multiple Keys'
      keys[key_str].add((title, tuple([str(t) for t in title_html])))

  def key_sort(k):
    if k == 'Multiple Keys':
      return 'zzz'
    return k.replace('Minor', '1').replace('Major', '2').replace('Modal', '3')
  for key in sorted(keys, key=key_sort):
    parts.append(CH(key, 2, hclass='index-section'))
    group_items = []
    for title, title_html in sorted(keys[key]):
      group_items.extend(title_html)
    parts.append(CDiv(group_items, hclass='index-group'))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'index', eye_candy_image='index-key')

@app.route('/index')
@app.route('/index/title')
def index_title():
  if request.path in ('/index', '/index/'):
    saved = session.get('index_sort')
    if saved and saved != 'title':
      return redirect('/index/' + saved, code=302)
  session['index_sort'] = 'title'

  parts = _index_header('title')

  tunes = utils.GetTuneIndex(False)

  titles = []
  sections = tunes.keys()
  all_tunes = set()
  for section in sections:
    for title, tune in tunes[section]:
      all_tunes.add((title, tune))
      
  for title, tune in sorted(all_tunes):
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.Type() + ' - ' + obj.GetKeyString()
      title_html = _index_title_html(obj, title)
      titles.append((title, title_html))
      
  titles.sort()
  group_items = []
  for title, title_html in titles:
    group_items.extend(title_html)
  parts.append(CDiv(group_items, hclass='index-group'))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'index', eye_candy_image='index-title')

@app.route('/index/author')
def index_author():
  session['index_sort'] = 'author'

  parts = _index_header('author')

  tunes = utils.GetTuneIndex(False)

  authors = collections.defaultdict(set)
  sections = tunes.keys()
  for section in sections:
    for title, tune in tunes[section]:
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      author = obj.author
      if not author:
        author = "To Be Determined"
      else:
        aparts = author.split()
        author = aparts[-1]
        if len(aparts) >= 2:
          author += ', ' + ' '.join(aparts[:-1])
      title += ' - ' + obj.Type() + ' - ' + obj.GetKeyString()
      title_html = _index_title_html(obj, title)
      authors[author].add((title, tuple([str(t) for t in title_html])))
      
  for author in sorted(authors):
    parts.append(CH(author, 2, hclass='index-section'))
    group_items = []
    for title, title_html in sorted(authors[author]):
      group_items.extend(title_html)
    parts.append(CDiv(group_items, hclass='index-group'))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'index', eye_candy_image='index-author')

def _index_title_html(obj, title):
  title_html = []
  title_html.append(CText(title, href="/tune/%s" % obj.name))
  title_html.extend(obj.GetActionIcons(index=True))
  title_html.append(CBreak())
  return title_html

@app.route('/index/sheet')
@app.route('/index/sheet/<stype>')
def index_sheet(stype='title'):
  if request.path in ('/index/sheet', '/index/sheet/'):
    saved = session.get('sheet_sort')
    if saved and saved != 'title':
      return redirect('/index/sheet/' + saved, code=302)
  session['sheet_sort'] = stype

  parts = [
    CH("Sheet Music for Locally Written Tunes", 1),
    CParagraph("This site is mostly about learning by ear, but we have some sheet music "
               "for locally written tunes, available both for screen display and printing, "
               "and in the ABC encoding:"),
  ]

  parts.append(CText('&#9834; Sort By:', bold=1))
  parts.append(CNBSP())
  parts.append(CText('Title', href='/index/sheet/title', bold=stype=='title'))
  parts.append(CNBSP())
  parts.append(CText('Author', href='/index/sheet/author', bold=stype=='author'))
  parts.append(CNBSP())
  parts.append(CText('Key', href='/index/sheet/key', bold=stype=='key'))
  parts.append(CBreak(2))

  tunes = utils.GetTuneIndex(True)

  sections = tunes.keys()
  all_tunes = set()
  for section in sections:
    for title, tune in tunes[section]:
      all_tunes.add((title, tune))

  def _sheet_title_html(obj, title):
    return [
      CText(title, href="/sheet/view/%s" % obj.name),
    ] + obj.GetActionIcons(index=True) + [
      CBreak(),
    ]

  if stype == 'author':
    authors = collections.defaultdict(list)
    for title, tune in sorted(all_tunes):
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      notes = obj.ReadSheetMusic()
      if not notes:
        continue
      author = obj.author
      if not author:
        author = "To Be Determined"
      else:
        aparts = author.split()
        author = aparts[-1]
        if len(aparts) >= 2:
          author += ', ' + ' '.join(aparts[:-1])
      title += ' - ' + obj.Type() + ' - ' + obj.GetKeyString()
      authors[author].append((title, _sheet_title_html(obj, title)))
    for i, author in enumerate(sorted(authors)):
      if i > 0:
        parts.append(CBreak())
      parts.append(CH(author, 3))
      parts.append(CBreak())
      for title, title_html in sorted(authors[author]):
        parts.extend(title_html)

  elif stype == 'key':
    keys = collections.defaultdict(list)
    for title, tune in sorted(all_tunes):
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      notes = obj.ReadSheetMusic()
      if not notes:
        continue
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.Type()
      key_str = obj.GetKeyString()
      if '/' in obj.key:
        key_str = 'Multiple Keys'
      keys[key_str].append((title, _sheet_title_html(obj, title)))
    def key_sort(k):
      if k == 'Multiple Keys':
        return 'zzz'
      return k.replace('Minor', '1').replace('Major', '2').replace('Modal', '3')
    for i, key in enumerate(sorted(keys, key=key_sort)):
      if i > 0:
        parts.append(CBreak())
      parts.append(CH(key, 3))
      parts.append(CBreak())
      for title, title_html in sorted(keys[key]):
        parts.extend(title_html)

  else:  # title
    for title, tune in sorted(all_tunes):
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      notes = obj.ReadSheetMusic()
      if not notes:
        continue
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.Type() + ' - ' + obj.GetKeyString()
      parts.extend(_sheet_title_html(obj, title))

  parts.append(CBreak(2))

  parts.append(CParagraph(["&#9834; Also available: ", CText("Printable Local Tunes Sheet Music Book", href='/sheet/all')]))

  return PageWrapper(parts, 'local')

@app.route('/dev')
def dev():
  parts = []
  parts.append(CH("Listings that Need Work", 1))
  parts.append(CParagraph("This page provides some useful resources for contributing "
                          "materials to this site, and also lists the tunes that are "
                          "missing notes, chords, a recording, origin, history, or "
                          "(for local tunes only) sheet music."))
  parts.append(CH("&#9834; Resources", 2))
  parts.append(CParagraph(
    "In addition to consulting printed material, interviewing authors, and searching "
    "the web, the following resources were particularly useful "
    "in researching the tune histories that are provided on this site:"
  ))
  parts.append(CList(
    [
      [CText("Traditional Tune Archive", href="https://tunearch.org/"), CNBSP(),
       CText('offers the most detailed and complete research.')], 
      [CText("The Session", href="https://thesession.org/"), CNBSP(),
       CText('generally lists more versions; commentary is only sometimes useful.')], 
      [CText("Folk Tune Finder", href="https://www.folktunefinder.com/"),CNBSP(),
       CText('is useful for finding tunes by name or by entering notes, but does not contain history.')], 
      [CText("EasyABC", href="https://sourceforge.net/projects/easyabc/"), CNBSP(),
       CText('makes it possible to play audio for the ABC notation found on the above sites.')],
      [CText("Historical Tune Books", href="http://folkopedia.efdss.org/wiki/List_of_historical_tunebooks,_some_of_which_are_available_on_the_internet"), CNBSP(),
       CText('is a list of historical tune books, some of which are available online.')],
    ]
  ))
  parts.append(CParagraph(
    "Since tunes are often known under several names, searching each of these (and the "
    "web in general) using all the names often produces results where a single search "
    "will not."
  ))
  tunes = utils.GetTuneIndex(True)

  titles = {}
  def sorted_by_title(s):
    retval = []
    for n in s:
      title_txt, title_html = titles[n]
      retval.append((title_txt, title_html))
    return sorted(retval)
  
  sections = tunes.keys()
  sections.sort()
  no_recording = set()
  no_local = set()
  no_origin = set()
  no_history = set()

  if 'incomplete'in sections:
    sections.remove('incomplete')
    sections.append('incomplete')
  for section in sections:
    if section == 'incomplete':
      parts.append(CH("&#9834; " + utils.kSectionTitles[section], 2))
      parts.append(CParagraph("Please help complete these listings by emailing the missing notes (first "
                              "2-3 measures of each part) or chords to "
                              "<a href='mailto:submit@music.cambridgeny.net'>submit@music.cambridgeny.net</a>"))
      parts.append(CBreak())
    for title, tune in sorted(tunes[section]):
      obj = utils.CTune(tune)
      obj.ReadDatabase()
      if obj.author and obj.author.lower() not in ('traditional', 'unknown'):
        title += ' (by {})'.format(obj.author)
      title += ' - ' + obj.GetKeyString()
      recording, mimetype, filename = obj.GetRecording()
      tune_title = []
      tune_title.append(CText(title, href="/tune/%s" % tune))
      tune_title.extend(obj.GetActionIcons(index=True))
      tune_title.append(CBreak())
      titles[obj.name] = (title, tune_title)
      
      if section == 'incomplete':
        parts.extend(tune_title)
      if not recording:
        no_recording.add(obj.name)
      if obj.origin:
        origin = obj.origin.lower()
      else:
        origin = ''
      if ('cambridge ny' in origin or 'cambridge, ny' in origin) and obj.ReadSheetMusic() is None:
        no_local.add(obj.name)
      if not obj.history:

        no_history.add(obj.name)
      if not obj.origin or 'unknown' in obj.origin.lower():
        no_origin.add(obj.name)

  if no_recording:
    parts.append(CH("&#9834; Tunes with No Recording", 2))
    parts.append(CParagraph("Please help complete these listings by creating a slow and "
                            "clear recording of the melody, played once or twice, and emailing it to "
                            "<a href='mailto:submit@music.cambridgeny.net'>submit@music.cambridgeny.net</a>"))
    parts.append(CBreak())
    for title, item in sorted_by_title(no_recording):
      for part in item:
        parts.append(part)
        
  if no_origin:
    parts.append(CH("&#9834; Tunes with Unknown Origin", 2))
    parts.append(CParagraph("If you have a documented original provenance for any of these tunes, please email "
                            "<a href='mailto:submit@music.cambridgeny.net'>submit@music.cambridgeny.net</a>"))
    parts.append(CBreak())
    for title, item in sorted_by_title(no_origin):
      for part in item:
        parts.append(part)
        
  if no_history:
    parts.append(CH("&#9834; Tunes with No Known History", 2))
    parts.append(CParagraph("If you have documented history for any of these tunes, please email "
                            "<a href='mailto:submit@music.cambridgeny.net'>submit@music.cambridgeny.net</a>"))
    parts.append(CBreak())
    for title, item in sorted_by_title(no_history):
      for part in item:
        parts.append(part)
        
  if no_local:
    parts.append(CH("&#9834; Local Tunes Missing Sheet Music", 2))
    parts.append(CParagraph("If you have sheet music for any of these tunes, please email "
                            "<a href='mailto:submit@music.cambridgeny.net'>submit@music.cambridgeny.net</a>"))
    parts.append(CBreak())
    for title, item in sorted_by_title(no_local):
      for part in item:
        parts.append(part)
        
  
  parts.append(CH("&#9834; Source Code", 2))
  parts.append(CParagraph("You can set up your own local copy of this website, which runs on "
                          "Flask and Python on Linux or macOS.  The source code and all the tune files are "
                          "<a href='https://github.com/sdeibel/tunejam'>available on github</a>.  You'll "
                          "need to clone the repository and run the platform setup script "
                          "src/platform/setup.py or its equivalent to set up the dependencies. "
                          "Then use src/website/tunejam.py as the main entry point to start "
                          "the site running in Flask."))
  parts.append(CParagraph("Please <a href='mailto:submit@music.cambridgeny.net'>"
                          "contact me</a> for help. I am currently the only developer, and would "
                          "improve packaging and docs if anyone else wants to join in the effort."))

  editor = HasCapability(kCapManageCache)
  if editor:
    parts.append(CH("&#9834; Cache Management", 2))
    parts.append(CParagraph("Clear cached generated files to force regeneration:"))
    parts.append(CList([
      CItem([CText("Clear Tune Cache", href='/dev/clear-cache/tune'),
             CText(" -- Individual tune artifacts (notes, chords, sheet music images)")]),
      CItem([CText("Clear Tune Set Cache", href='/dev/clear-cache/tuneset'),
             CText(" -- Tune set page PDFs")]),
      CItem([CText("Clear Book Cache", href='/dev/clear-cache/book'),
             CText(" -- Full book PDFs")]),
      CItem([CText("Clear All Caches", href='/dev/clear-cache/all'),
             CText(" -- All of the above")]),
      CItem([CText("Rebuild All Books", href='/dev/rebuild-books'),
             CText(" -- Regenerate all book PDFs (runs in background)")]),
    ]))
  else:
    parts.append(CBreak())
    parts.append(LoginButton('/dev', label="Admin login required"))

  parts.append(CBreak(2))
  return PageWrapper(parts, 'dev')

@app.route('/dev/clear-cache/<cache_type>')
def clear_cache(cache_type):
  import shutil

  editor = HasCapability(kCapManageCache)
  if not editor:
    return redirect('/authorize/dev', code=303)

  cleared = []
  cache_dirs = {
    'tune': os.path.join(utils.kCacheLoc, 'tune'),
    'tuneset': os.path.join(utils.kCacheLoc, 'tuneset'),
    'book': os.path.join(utils.kCacheLoc, 'book'),
  }

  if cache_type == 'all':
    targets = ['tune', 'tuneset', 'book']
  elif cache_type in cache_dirs:
    targets = [cache_type]
  else:
    return redirect('/dev', code=303)

  for t in targets:
    d = cache_dirs[t]
    if os.path.exists(d):
      for fn in os.listdir(d):
        fp = os.path.join(d, fn)
        if os.path.isfile(fp):
          os.remove(fp)
      cleared.append(t)

  parts = [
    CH("Cache Cleared", 2),
    CParagraph("Cleared cache: %s" % ', '.join(cleared)),
    CBreak(),
    CText("Return to Dev page", href='/dev'),
    CBreak(2),
  ]
  return PageWrapper(parts, 'dev')

@app.route('/dev/rebuild-books')
def rebuild_books():
  import threading
  import crontask

  editor = HasCapability(kCapManageCache)
  if not editor:
    return redirect('/authorize/dev', code=303)

  thread = threading.Thread(target=crontask.regenerate_books)
  thread.daemon = True
  thread.start()

  parts = [
    CH("Rebuilding Books", 2),
    CParagraph("All books are being regenerated in the background. "
               "This may take several minutes."),
    CBreak(),
    CText("Return to Dev page", href='/dev'),
    CBreak(2),
  ]
  return PageWrapper(parts, 'dev')

@app.route('/sets', methods=['GET', 'POST'])
@app.route('/sets/')
@app.route('/sets/<spec>')
@app.route('/sets/sid/<sid>')
@app.route('/sets/sid/<sid>/edit/<spec>')
def sets(spec=None, sid=None):

  editor = HasCapability(kCapManageEvents)
  
  error = None
  preload_tunes = []

  if sid is not None:
    s = utils.CEvent(sid)
    s.ReadEvent()
    
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
      elif arg.startswith('event='):
        sid = arg[len('event='):].strip()
        s = utils.CEvent(sid)
        s.ReadEvent()
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
          current_set = '&'.join(tunes)
          if pagetype == 'both':
            pt_suffix = '&event=%s' % sid
          else:
            pt_suffix = '&pagetype=%s&event=%s' % (pagetype, sid)

          # Find previous/next sets in the event
          prev_set = None
          next_set = None
          if current_set in s.sets:
            idx = s.sets.index(current_set)
            if idx > 0:
              prev_set = s.sets[idx - 1]
            if idx < len(s.sets) - 1:
              next_set = s.sets[idx + 1]

          prev_link = None
          next_link = None
          if prev_set is not None:
            prev_link = CText("<< Previous Set", href='/sets/%s%s' % (prev_set, pt_suffix))
          if next_set is not None:
            next_link = CText("Next Set >>", href='/sets/%s%s' % (next_set, pt_suffix))

          event_link = '/event/%s' % sid

          # Top: event title as link, prev/next left/right justified
          top_nav_items = []
          if prev_link is not None:
            top_nav_items.append(CDiv(prev_link, style="float:left"))
          if next_link is not None:
            top_nav_items.append(CDiv(next_link, style="float:right"))
          top_nav = CDiv(top_nav_items, style="overflow:auto")

          header = CText("Set from Event: <a href='%s'>%s</a>" % (event_link, s.title), bold=1)
          parts.insert(0, header)
          parts.insert(1, CBreak())
          parts.insert(2, top_nav)
          parts.insert(3, CBreak(2))

          # Bottom: prev/next left/right, return and delete centered
          bottom_center = [CText("Return to event %s" % s.title, href=event_link)]
          if editor:
            bottom_center.extend([
              CNBSP(3), CText('|'), CNBSP(3),
              CText("Delete this set", href='/event/%s/delete/%s' % (sid, current_set)),
            ])

          bottom_items = []
          if prev_link is not None:
            bottom_items.append(CDiv(CText("<< Previous Set", href='/sets/%s%s' % (prev_set, pt_suffix)),
                                     style="float:left"))
          if next_link is not None:
            bottom_items.append(CDiv(CText("Next Set >>", href='/sets/%s%s' % (next_set, pt_suffix)),
                                     style="float:right"))
          bottom_items.append(CDiv(bottom_center, style="text-align:center"))

          parts.extend([CBreak(2), CDiv(bottom_items, style="overflow:auto"), CBreak(2)])
          
        return PageWrapper(parts)

  filter = request.form.get('filter')
  if filter == 'all':
    filter = None
  
  parts = []
  # Jquery and jquery-ui came from:
  # http://jquery.com/download/ (version 3.7.0)
  # http://jqueryui.com/download/all (version 1.13.2)
  # Extra JS libraries came from:
  # https://github.com/padolsey-archive/jquery.fn/tree/master/sortElements
  # https://raw.github.com/furf/jquery-ui-touch-punch/master/jquery.ui.touch-punch.min.js
  parts.append("""<link rel="stylesheet" href="/js/ui/jquery-ui.css">
<script src="/js/jquery-3.7.0.min.js"></script>
<script src="/js/ui/jquery-ui.min.js"></script>
<script src="/js/jquery.sortElements.js"></script>
<script src="/js/jquery.ui.touch-punch.min.js"></script> 
<script>
var isTouchDevice = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
$(function() {
  if (isTouchDevice) {
    // On touch devices, use tap to move items between lists
    $(document).on("click", "#alltunes li", function() {
      $(this).appendTo("#selectedtunes");
    });
    $(document).on("click", "#selectedtunes li", function() {
      $(this).appendTo("#alltunes");
      $( "#alltunes" ).children().sortElements(function(a, b){
        return a.innerHTML > b.innerHTML ? 1 : -1;
      });
      FilterTunes();
    });
    // Allow reordering within Selected list only
    $( "#selectedtunes" ).sortable({
      scrollSpeed: 100,
    }).disableSelection();
  } else {
    // On desktop, double-click to move items between lists
    $(document).on("dblclick", "#alltunes li", function() {
      $(this).appendTo("#selectedtunes");
    });
    $(document).on("dblclick", "#selectedtunes li", function() {
      $(this).appendTo("#alltunes");
      $( "#alltunes" ).children().sortElements(function(a, b){
        return a.innerHTML > b.innerHTML ? 1 : -1;
      });
      FilterTunes();
    });
    // Also drag between lists; only Selected is reorderable
    function resortAvailable() {
      $( "#alltunes" ).children().sortElements(function(a, b){
        return a.innerHTML > b.innerHTML ? 1 : -1;
      });
      FilterTunes();
    }
    $( "#alltunes" ).sortable({
      connectWith: "#selectedtunes",
      containment: ".list-area",
      scrollSpeed: 100,
      stop: resortAvailable,
      receive: resortAvailable,
    }).disableSelection();
    $( "#selectedtunes" ).sortable({
      connectWith: "#alltunes",
      containment: ".list-area",
      scrollSpeed: 100,
    }).disableSelection();
  }
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
    window.location.href= "/event/" + sid + "/add/" + tunes;
  } else {
    window.location.href= "/event/" + sid + "/add/" + tunes + "/replace/" + old_set;
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
height:300px;
width:350px;
overflow-y:scroll;
overflow-x:hidden;
border: 1px solid #666666;
padding: 0px;
-webkit-overflow-scrolling:touch;
}
div.list-area {
position:relative;
display:block;
min-height:330px;
}
div.list-title {
font-weight:bold;
position:absolute;
top:0px;
left:0px;
}
div.list-left {
position:relative;
top:0px;
left:0px;
overflow:auto;
}
div.list-right {
position:absolute;
top:0px;
left:370px;
overflow:auto;
}
@media only screen and (max-width:600px) {
div.list-area {
display:block;
}
div.list-right {
position:relative;
left:0px;
top:0px;
clear:both;
}
div.scroll {
float:none;
width:87vw;
}
}
.mobile-instructions {
display:none;
}
@media only screen and (max-width:600px) {
.desktop-instructions {
display:none;
}
.mobile-instructions {
display:block;
}
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
  parts.append("""<p class="desktop-instructions">Drag one or more songs from the Available list """
               """to the Selected list, double-click to move a song between lists, """
               """or press 'Random 3' to select three random tunes.  """
               """Then press Create Set to generate the set:</p>""")
  parts.append("""<p class="mobile-instructions">Tap a song to move it to the Selected list.  """
               """Tap it again to move it back.  Drag to reorder songs in the Selected list.  """
               """You can also press 'Random 3' to select three random tunes.  """
               """Then press Create Set to generate the set:</p>""")
  
  
  section_options = [
    ('all', 'All')
  ]

  keys = utils.kSectionTitles.keys()
  keys.append('ax4')
  keys.sort()
  for key in keys:
    if key == 'ax4':
      title = "All 2/4, 4/4, and C Time"
    else:
      title = utils.kSectionTitles[key]
    section_options.append((key, title))
    
  parts.append(CForm([
    CText("&#9834; Filter:", bold=1),
    CSelect(section_options, current=filter, name='filter',
            onchange='FilterTunes()', id='filterselect'),
    CInput(type='TEXT', name='text_filter', onkeyup='FilterTunes()', id='filtertext'), 
    CInput(type='RESET', value='X', id='filter-reset', onclick='setTimeout(function() { FilterTunes(); })', style="border:0px; font-weight:bold;"),
    CNBSP(2), 
    CInput(type='BUTTON', value='-> Random 3', onclick='setTimeout(function() { RandomThree(); })'), 
  ], onsubmit="return FilterSubmit();", id="filter-form"))
  parts.append(CBreak())
  
  seen_tunes = set()
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
      title += ' - %s - %s' % (obj.Type(), obj.GetKeyString())
      if tune in preload_tunes:
        continue
      if title in seen_tunes:
        continue
      seen_tunes.add(title)
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
    title = '%s - %s - %s' % (obj.title, obj.Type(), obj.GetKeyString())
    selected_tunes.append(CItem(title, id='tune_%s' % tune.replace('_', '+'),
                                 hclass='ui-state-default %s' % obj.klass.split(',')[0]))

  all_tunes.sort()
  all_tunes = [i[1] for i in all_tunes]
  
  tunes_list = CDiv(CList(all_tunes, id='alltunes', hclass='connectedSortable'), hclass='scroll')
  selected_list = CDiv(CList([selected_tunes], id='selectedtunes', hclass='connectedSortable'), hclass='scroll')
  
  parts.append(CDiv([
    CDiv([CDiv(CText("Available:"), hclass='list-title'), CBreak(), tunes_list], hclass='list-left'),
    CDiv([CDiv(CText("Selected:"), hclass='list-title'), CBreak(), selected_list], hclass='list-right'), 
  ], hclass='list-area'))
  parts.append(CBreak())
  parts.append(CDiv(hclass="clear"))
  
  # Creating set outside of event
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
    
  # Adding a spec to a event
  elif spec is None:
    parts.append(CForm([
      CInput(type='button', value="Add Set", onclick="SubmitTunes('%s', '');" % sid),
      CInput(type='button', value="Clear Selected", onclick='ClearTunes();'), 
    ], id='eventsetform'))
  
  # Editing a spec in a event
  else:
    parts.append(CForm([
      CInput(type='button', value="Update Set", onclick="SubmitTunes('%s', '%s');" % (sid, spec)),
      CInput(type='button', value="Clear Selected", onclick='ClearTunes();'), 
    ], id='eventsetform'))
    
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
      CText("Return to event %s" % s.title, href='/event/%s' % sid), 
      CBreak(2)
    ])
    section = 'event'
  else:
    section = 'sets'
    
  return PageWrapper(parts, section, show_eye_candy=(section != 'event'))

@app.route('/tune/new')
def tune_new():
  if not HasCapability(kCapEditTunes):
    return redirect('/authorize/tune/new', code=303)

  # Create a blank tune object with defaults
  obj = utils.CTune('new')
  obj.title = ''
  obj.klass = ''
  obj.key = ''
  obj.meter = '4/4'
  obj.unit = '1/8'
  obj.author = None
  obj.origin = None
  obj.structure = None
  obj.ref = None
  obj.history = None
  obj.url = None
  obj.raw_notes = ''
  obj.chords = ''

  return _build_tune_form(obj, 'new', 'New Tune', '/tune/new/create', '/index')

@app.route('/tune/new/create', methods=['POST'])
def tune_new_create():
  if not HasCapability(kCapEditTunes):
    return redirect('/authorize/tune/new', code=303)

  title = request.form.get('title', '').strip()
  if not title:
    return redirect('/tune/new', code=303)

  # Auto-compute filename from title
  import re
  filename = title.lower()
  filename = re.sub(r'[^a-z0-9\s]', '', filename)
  filename = re.sub(r'\s+', '_', filename)
  filename = re.sub(r'_+', '_', filename)
  filename = filename.strip('_')

  if not filename:
    return redirect('/tune/new', code=303)

  # Check for existing spec file
  spec_path = os.path.join(utils.kDatabaseDir, filename + '.spec')
  if os.path.exists(spec_path):
    return redirect('/tune/new', code=303)

  # Create the tune object and populate from form
  obj = utils.CTune(filename)
  obj.title = title
  obj.key = request.form.get('key', '').strip()
  obj.meter = request.form.get('meter', '4/4').strip()
  obj.unit = request.form.get('unit', '1/8').strip()
  obj.author = request.form.get('author', '').strip() or None
  obj.origin = request.form.get('origin', '').strip() or None
  obj.structure = request.form.get('structure', '').strip() or None
  obj.ref = request.form.get('ref', '').strip() or None
  obj.history = request.form.get('history', '').strip() or None

  # Collect tune types from checkboxes
  types = []
  for sname, stitle, slabel in utils.kSections:
    if sname == 'incomplete':
      continue
    if request.form.get('klass_%s' % sname):
      types.append(sname)
  obj.klass = ','.join(types) if types else 'other'

  # Collect URLs
  urls = []
  for key in sorted(request.form.keys()):
    if key.startswith('url_'):
      val = request.form.get(key, '').strip()
      if val:
        urls.append(val)
  obj.url = '\n'.join(urls) if urls else None

  # Notes (ABC)
  raw_notes = request.form.get('raw_notes', '')
  if raw_notes.strip():
    obj.raw_notes = raw_notes.rstrip('\n') + '\n'
  else:
    obj.raw_notes = ''

  # Reconstruct chords from structured form
  obj.chords = _ReconstructChords(request.form)

  obj.WriteSpec()

  return redirect('/tune/%s' % filename, code=303)

@app.route('/tune/<tune>')
def tune(tune):
  parts = []
  editor = HasCapability(kCapEditTunes)
  parts.extend(CreateTuneHTML(tune, metadata=True, editor=editor))
  return PageWrapper(parts, 'index', show_eye_candy=False)

def _build_editor_js(tune, chord_parts, url_count=1):
  """Build the JavaScript for the tune editor page."""

  # Pass defaults to JS
  defaults_js = '{\n'
  for ttype, vals in utils.kDefaultsByType.items():
    defaults_js += '    "%s": {meter:"%s", unit:"%s", measures:%d, rows:%d},\n' % (
      ttype, vals['meter'], vals['unit'], vals['measures'], vals['rows'])
  defaults_js += '  }'

  return """
<script>
var tuneDefaults = %s;
var formChanged = false;

document.addEventListener('DOMContentLoaded', function() {
  var form = document.querySelector('form.edit-form');
  if (form) {
    form.addEventListener('change', function() { formChanged = true; });
    form.addEventListener('input', function() { formChanged = true; });
  }
});

window.addEventListener('beforeunload', function(e) {
  if (formChanged) {
    e.preventDefault();
    e.returnValue = '';
  }
});

// Type popup menu
function toggleTypeMenu() {
  var dd = document.getElementById('type-menu-dropdown');
  dd.classList.toggle('open');
}
// Priority order by number of tunes of each type in the database
var typePriority = ['reel','jig','waltz','air','polka','march','hornpipe','other','slide','slip','rag','polska','strathspey','rant'];
function updateTypeLabel() {
  var checks = document.querySelectorAll('#type-menu-dropdown input[type="checkbox"]:checked');
  var labels = [];
  for (var i = 0; i < checks.length; i++) {
    var lbl = checks[i].parentNode.textContent.trim();
    labels.push(lbl);
  }
  var span = document.getElementById('type-menu-label');
  span.textContent = labels.length > 0 ? labels.join(', ') : 'Select Type...';
  updateMeterUnit();
  formChanged = true;
}
function updateMeterUnit() {
  // Only update if notes textarea is entirely empty
  var notes = document.getElementById('raw-notes-textarea');
  if (!notes || notes.value.trim() !== '') return;
  var checks = document.querySelectorAll('#type-menu-dropdown input[type="checkbox"]:checked');
  if (checks.length === 0) return;
  // Find the checked type with highest priority (most tunes)
  var bestType = null;
  var bestPri = 999;
  for (var i = 0; i < checks.length; i++) {
    var ttype = checks[i].name.replace('klass_', '');
    var pri = typePriority.indexOf(ttype);
    if (pri === -1) pri = 998;
    if (pri < bestPri) { bestPri = pri; bestType = ttype; }
  }
  if (bestType && tuneDefaults[bestType]) {
    var meterSel = document.getElementById('field-meter');
    if (meterSel) meterSel.value = tuneDefaults[bestType].meter;
    var unitField = document.querySelector('select[name="unit"]');
    if (unitField) unitField.value = tuneDefaults[bestType].unit;
  }
  renderAbcPreview();
}
// Close the type menu when clicking outside
document.addEventListener('click', function(e) {
  var container = document.getElementById('type-menu-container');
  if (container && !container.contains(e.target)) {
    var dd = document.getElementById('type-menu-dropdown');
    if (dd) dd.classList.remove('open');
  }
  var keyContainer = document.getElementById('key-editor-container');
  if (keyContainer && !keyContainer.contains(e.target)) {
    var kdd = document.getElementById('key-editor-dropdown');
    if (kdd) kdd.classList.remove('open');
  }
});

// Key editor
function toggleKeyEditor() {
  var dd = document.getElementById('key-editor-dropdown');
  dd.classList.toggle('open');
  if (dd.classList.contains('open')) {
    // If no key rows exist, add one defaulting to G Major
    var container = document.getElementById('key-rows-container');
    if (container.querySelectorAll('.key-editor-row').length === 0) {
      container.insertAdjacentHTML('beforeend', keyRowHtml(0, 'G', '', true));
      updateKeyValue();
    }
  }
}

function keyRowHtml(idx, letter, mode, showRemove) {
  var letters = ['A','B','C','D','E','F','G','H'];
  var modes = [['','Major'],['m','Minor'],['mix','Modal']];
  var html = '<div class="key-editor-row">';
  html += '<select class="key-letter" onchange="updateKeyValue()">';
  for (var i = 0; i < letters.length; i++) {
    var sel = letters[i] === letter ? ' selected' : '';
    html += '<option value="' + letters[i] + '"' + sel + '>' + letters[i] + '</option>';
  }
  html += '</select> ';
  html += '<select class="key-mode" onchange="updateKeyValue()">';
  for (var i = 0; i < modes.length; i++) {
    var sel = modes[i][0] === mode ? ' selected' : '';
    html += '<option value="' + modes[i][0] + '"' + sel + '>' + modes[i][1] + '</option>';
  }
  html += '</select>';
  if (showRemove) {
    html += ' <button type="button" class="url-remove-btn" style="font-size:85%%; padding:1px 6px" onclick="removeKeyPart(this)">X</button>';
  }
  html += '</div>';
  return html;
}

function updateKeyValue() {
  var container = document.getElementById('key-rows-container');
  var rows = container.querySelectorAll('.key-editor-row');
  if (rows.length === 0) {
    document.getElementById('field-key').value = '';
    document.getElementById('key-display-label').textContent = 'Select Key';
    formChanged = true;
    return;
  }
  var parts = [];
  var displayParts = [];
  for (var i = 0; i < rows.length; i++) {
    var letter = rows[i].querySelector('.key-letter').value;
    var mode = rows[i].querySelector('.key-mode').value;
    parts.push(letter + mode);
    var modeLabel = mode === 'm' ? ' Minor' : mode === 'mix' ? ' Modal' : ' Major';
    displayParts.push(letter + modeLabel);
  }
  document.getElementById('field-key').value = parts.join('/');
  document.getElementById('key-display-label').textContent = displayParts.join(' / ');
  formChanged = true;
  renderAbcPreview();
}

function addKeyPart() {
  var container = document.getElementById('key-rows-container');
  var rows = container.querySelectorAll('.key-editor-row');
  container.insertAdjacentHTML('beforeend', keyRowHtml(rows.length, 'D', '', true));
  updateKeyValue();
}

function removeKeyPart(btn) {
  var row = btn.parentNode;
  var container = row.parentNode;
  container.removeChild(row);
  var rows = container.querySelectorAll('.key-editor-row');
  if (rows.length === 0) {
    // All keys removed — clear value, close popup, show "Select Key"
    document.getElementById('field-key').value = '';
    document.getElementById('key-display-label').textContent = 'Select Key';
    document.getElementById('key-editor-dropdown').classList.remove('open');
    formChanged = true;
  } else {
    updateKeyValue();
  }
}

// Initialize key editor rows
document.addEventListener('DOMContentLoaded', function() {
  if (typeof initialKeyParts !== 'undefined') {
    var container = document.getElementById('key-rows-container');
    if (container) {
      var html = '';
      for (var i = 0; i < initialKeyParts.length; i++) {
        html += keyRowHtml(i, initialKeyParts[i][0], initialKeyParts[i][1], true);
      }
      container.innerHTML = html;
    }
  }
});

// URL field management
var urlCounter = %d;
function addUrlField() {
  var container = document.getElementById('url-container');
  var div = document.createElement('div');
  div.className = 'url-row';
  div.innerHTML = '<input type="text" name="url_' + urlCounter + '" value="" class="url-field" placeholder="Enter URL here" /> ' +
                  '<button type="button" class="url-test-btn" onclick="testUrl(this)">Test</button> ' +
                  '<button type="button" class="url-remove-btn" onclick="removeUrlField(this)">X</button>';
  container.appendChild(div);
  urlCounter++;
  formChanged = true;
}
function removeUrlField(btn) {
  var row = btn.parentNode;
  row.parentNode.removeChild(row);
  formChanged = true;
}

function testUrl(btn) {
  var row = btn.parentNode;
  var input = row.querySelector('input[type="text"]');
  var url = input ? input.value.trim() : '';
  if (!url) { alert('No URL entered.'); return; }
  if (url.indexOf('://') === -1) url = 'http://' + url;
  btn.textContent = '...';
  btn.disabled = true;
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/check-url?url=' + encodeURIComponent(url), true);
  xhr.onload = function() {
    btn.textContent = 'Test';
    btn.disabled = false;
    if (xhr.status === 200) {
      try {
        var data = JSON.parse(xhr.responseText);
        if (data.ok) {
          window.open(url, '_blank');
        } else {
          alert('Link appears broken: ' + data.error);
        }
      } catch(e) {
        alert('Error checking URL.');
      }
    } else {
      alert('Error checking URL.');
    }
  };
  xhr.onerror = function() {
    btn.textContent = 'Test';
    btn.disabled = false;
    alert('Error checking URL.');
  };
  xhr.send();
}

// Chord structure management
var numParts = %d;
var partLabels = 'ABCDEFGHIJ';

function renumberParts() {
  // Renumber all parts and their fields after add/remove
  var container = document.getElementById('chord-parts-container');
  var wrappers = container.querySelectorAll('.part-wrapper');
  numParts = wrappers.length;
  document.querySelector('input[name="num_parts"]').value = numParts;
  // Remove all old rows_in_part hidden fields
  var oldHidden = document.querySelectorAll('input[name^="rows_in_part_"]');
  for (var h = 0; h < oldHidden.length; h++) oldHidden[h].parentNode.removeChild(oldHidden[h]);

  for (var p = 0; p < wrappers.length; p++) {
    wrappers[p].setAttribute('data-part', p);
    var label = p < partLabels.length ? partLabels[p] : '' + p;
    var b = wrappers[p].querySelector('.part-header b');
    if (b) b.textContent = 'Part ' + label;
    // Rename repeat checkbox
    var rep = wrappers[p].querySelector('.part-header input[type="checkbox"]');
    if (rep) rep.name = 'repeat_' + p;
    // Rename chord inputs
    var table = wrappers[p].querySelector('table.edit-chords');
    if (table) {
      var rows = table.querySelectorAll('tr');
      for (var r = 0; r < rows.length; r++) {
        var inputs = rows[r].querySelectorAll('input[type="text"]');
        for (var c = 0; c < inputs.length; c++) {
          inputs[c].name = 'chord_' + p + '_' + r + '_' + c;
        }
      }
      // Add hidden field for rows_in_part
      var hf = document.createElement('input');
      hf.type = 'hidden';
      hf.name = 'rows_in_part_' + p;
      hf.value = rows.length;
      document.querySelector('form.edit-form').appendChild(hf);
    }
  }
}

function getDefaultCols() {
  // Get default columns from first row of first part, or 4
  var firstRow = document.querySelector('#chord-parts-container table.edit-chords tr');
  if (firstRow) {
    return firstRow.querySelectorAll('input[type="text"]').length;
  }
  return 4;
}

function addPart() {
  var container = document.getElementById('chord-parts-container');
  var p = numParts;
  var label = p < partLabels.length ? partLabels[p] : '' + p;

  // Determine rows from tune type defaults
  var rowsPerPart = 2;
  var numCols = getDefaultCols();
  var checks = document.querySelectorAll('#type-menu-dropdown input[type="checkbox"]:checked');
  if (checks.length > 0) {
    var ttype = checks[0].name.replace('klass_', '');
    if (tuneDefaults[ttype]) rowsPerPart = tuneDefaults[ttype].rows;
  }

  var html = '<div class="part-header">';
  html += '<button type="button" class="part-remove-btn" onclick="removePart(this)" title="Remove part">X</button> ';
  html += '<b>Part ' + label + '</b>';
  html += ' &nbsp; Repeat: <input type="checkbox" name="repeat_' + p + '" value="1" checked />';
  html += '</div>';
  html += '<table class="edit-chords" style="margin-bottom:2px">';
  for (var r = 0; r < rowsPerPart; r++) {
    html += '<tr>';
    for (var c = 0; c < numCols; c++) {
      html += '<td><input type="text" name="chord_' + p + '_' + r + '_' + c + '" value="" size="6" /></td>';
    }
    html += '<td><button type="button" class="row-ctl-btn add-measure-btn" onclick="addMeasureToRow(this)" title="Add measure">+</button>';
    html += '<button type="button" class="row-ctl-btn remove-measure-btn" onclick="removeMeasureFromRow(this)" title="Remove measure">&minus;</button>';
    html += '<button type="button" class="row-ctl-btn remove-row-btn" onclick="removeRow(this)" title="Remove row">X</button></td>';
    html += '</tr>';
  }
  html += '</table>';
  html += '<button type="button" class="add-btn" style="font-size:80%%; padding:1px 6px; margin-bottom:8px" onclick="addRowToPart(this)">+ Row</button>';

  var div = document.createElement('div');
  div.className = 'part-wrapper';
  div.innerHTML = html;
  container.appendChild(div);

  renumberParts();
  formChanged = true;
  updateChordPreview();
}

function removePart(btn) {
  var wrapper = btn.closest('.part-wrapper');
  if (!wrapper) return;
  var container = document.getElementById('chord-parts-container');
  if (container.querySelectorAll('.part-wrapper').length <= 1) {
    alert('Must have at least one part.');
    return;
  }
  var inputs = wrapper.querySelectorAll('input[type="text"]');
  var hasData = false;
  for (var i = 0; i < inputs.length; i++) {
    if (inputs[i].value.trim()) { hasData = true; break; }
  }
  if (hasData && !confirm('This part has chord data. Remove it?')) return;
  container.removeChild(wrapper);
  renumberParts();
  formChanged = true;
  updateChordPreview();
}

function addMeasureToRow(btn) {
  var tr = btn.closest('tr');
  var chordInputs = tr.querySelectorAll('input[type="text"]');
  var numCols = chordInputs.length;
  // Get part and row index from existing input
  var match = chordInputs[0] ? chordInputs[0].name.match(/chord_(\\d+)_(\\d+)_/) : null;
  var pIdx = match ? match[1] : 0;
  var rIdx = match ? match[2] : 0;
  var td = document.createElement('td');
  td.innerHTML = '<input type="text" name="chord_' + pIdx + '_' + rIdx + '_' + numCols + '" value="" size="6" />';
  // Insert before the last td (which has the +/- buttons)
  var ctlTd = tr.lastElementChild;
  tr.insertBefore(td, ctlTd);
  formChanged = true;
  updateChordPreview();
}

function removeMeasureFromRow(btn) {
  var tr = btn.closest('tr');
  var chordInputs = tr.querySelectorAll('input[type="text"]');
  if (chordInputs.length <= 1) { alert('Must have at least one measure.'); return; }
  var lastInput = chordInputs[chordInputs.length - 1];
  if (lastInput.value.trim() && !confirm('This measure has data. Remove it?')) return;
  var td = lastInput.parentNode;
  tr.removeChild(td);
  // Renumber the inputs in this row
  var inputs = tr.querySelectorAll('input[type="text"]');
  var match = inputs[0] ? inputs[0].name.match(/chord_(\\d+)_(\\d+)_/) : null;
  if (match) {
    for (var c = 0; c < inputs.length; c++) {
      inputs[c].name = 'chord_' + match[1] + '_' + match[2] + '_' + c;
    }
  }
  formChanged = true;
  updateChordPreview();
}

function addRowToPart(btn) {
  var wrapper = btn.closest('.part-wrapper');
  var table = wrapper.querySelector('table.edit-chords');
  var existingRows = table.querySelectorAll('tr');
  // Get column count from first row
  var numCols = existingRows.length > 0 ? existingRows[0].querySelectorAll('input[type="text"]').length : 4;
  var pIdx = wrapper.getAttribute('data-part');
  var rIdx = existingRows.length;
  var tr = document.createElement('tr');
  var html = '';
  for (var c = 0; c < numCols; c++) {
    html += '<td><input type="text" name="chord_' + pIdx + '_' + rIdx + '_' + c + '" value="" size="6" /></td>';
  }
  html += '<td><button type="button" class="row-ctl-btn add-measure-btn" onclick="addMeasureToRow(this)" title="Add measure">+</button>';
  html += '<button type="button" class="row-ctl-btn remove-measure-btn" onclick="removeMeasureFromRow(this)" title="Remove measure">&minus;</button>';
  html += '<button type="button" class="row-ctl-btn remove-row-btn" onclick="removeRow(this)" title="Remove row">X</button></td>';
  tr.innerHTML = html;
  var tbody = table.querySelector('tbody') || table;
  tbody.appendChild(tr);
  // Update rows_in_part hidden field
  var hf = document.querySelector('input[name="rows_in_part_' + pIdx + '"]');
  if (hf) hf.value = parseInt(hf.value) + 1;
  formChanged = true;
  updateChordPreview();
}

function removeRow(btn) {
  var tr = btn.closest('tr');
  var table = tr.closest('table.edit-chords');
  if (table.querySelectorAll('tr').length <= 1) {
    alert('Must have at least one row.');
    return;
  }
  var inputs = tr.querySelectorAll('input[type="text"]');
  var hasData = false;
  for (var i = 0; i < inputs.length; i++) {
    if (inputs[i].value.trim()) { hasData = true; break; }
  }
  if (hasData && !confirm('This row has data. Remove it?')) return;
  tr.parentNode.removeChild(tr);
  // Renumber to fix row indices and update rows_in_part
  renumberParts();
  formChanged = true;
  updateChordPreview();
}

// Chord preview
function updateChordPreview() {
  var preview = document.getElementById('chord-preview-inner');
  if (!preview) return;
  var header = document.querySelector('input[name="chord_header"]');
  var footer = document.querySelector('input[name="chord_footer"]');
  var headerText = header ? header.value.trim() : '';
  var footerText = footer ? footer.value.trim() : '';

  var wrappers = document.querySelectorAll('#chord-parts-container .part-wrapper');
  var html = '';
  if (headerText) {
    html += '<div class="chord-note">' + headerText.replace(/</g, '&lt;') + '</div>';
  }
  html += '<table class="chords-preview">';
  var partClass = 'even';
  for (var p = 0; p < wrappers.length; p++) {
    var table = wrappers[p].querySelector('table.edit-chords');
    if (!table) continue;
    var repCheck = wrappers[p].querySelector('.part-header input[type="checkbox"]');
    var hasRepeat = repCheck && repCheck.checked;
    var rows = table.querySelectorAll('tr');
    for (var r = 0; r < rows.length; r++) {
      var inputs = rows[r].querySelectorAll('input[type="text"]');
      var isFirst = (r === 0);
      var isLast = (r === rows.length - 1);
      html += '<tr class="' + partClass + '">';
      // Open repeat marker
      if (hasRepeat && isFirst) {
        html += '<td class="first"> :</td>';
      } else {
        html += '<td class="first"></td>';
      }
      for (var c = 0; c < inputs.length; c++) {
        var val = inputs[c].value.trim() || '';
        var cls = (c === inputs.length - 1) ? 'last-chord' : '';
        html += '<td class="' + cls + '">' + (val ? val.replace(/</g, '&lt;') : '&nbsp;') + '</td>';
      }
      // Close repeat marker
      if (hasRepeat && isLast) {
        html += '<td class="last">: </td>';
      } else {
        html += '<td class="last"></td>';
      }
      html += '</tr>';
    }
    partClass = (partClass === 'even') ? 'odd' : 'even';
  }
  html += '</table>';
  if (footerText) {
    html += '<div class="chord-note">' + footerText.replace(/</g, '&lt;') + '</div>';
  }
  preview.innerHTML = html;
}

// Live ABC preview via abcjs
var abcDebounce;
function renderAbcPreview() {
  clearTimeout(abcDebounce);
  abcDebounce = setTimeout(function() { doRenderAbc(); }, 300);
}
function doRenderAbc() {
  var textarea = document.getElementById('raw-notes-textarea');
  var preview = document.getElementById('abcjs-preview');
  if (!textarea || !preview || typeof ABCJS === 'undefined') return;

  var raw = textarea.value.trim();
  if (!raw) {
    preview.innerHTML = '<div style="color:#666; font-style:italic; padding:20px">Enter ABC notation to see preview</div>';
    return;
  }

  // Read current key, meter, unit from form fields
  var key = document.getElementById('field-key').value || 'C';
  var meterSel = document.getElementById('field-meter');
  var meter = meterSel ? meterSel.value : '4/4';
  var unitField = document.querySelector('select[name="unit"]');
  var unit = unitField ? unitField.value : '1/8';

  // Build ABC string with headers, replicating __NotesWithMeterOnEachLine()
  var lines = raw.split('\\n');
  var abc = 'X:1\\nK:' + key + '\\nL:' + unit + '\\nM:' + meter + '\\n';
  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    if (line.length > 1 && line[1] === ':') {
      abc += line + '\\n';
    } else {
      abc += 'M:' + meter + '\\n' + line + '\\n';
    }
  }

  ABCJS.renderAbc("abcjs-preview", abc, {
    responsive: "resize",
    staffwidth: 500
  });
}

// Hook up live preview updates
document.addEventListener('DOMContentLoaded', function() {
  // Update on any input in chord area
  var chordContainer = document.getElementById('chord-parts-container');
  if (chordContainer) {
    chordContainer.addEventListener('input', updateChordPreview);
    chordContainer.addEventListener('change', updateChordPreview);
  }
  var headerField = document.querySelector('input[name="chord_header"]');
  if (headerField) headerField.addEventListener('input', updateChordPreview);
  var footerField = document.querySelector('input[name="chord_footer"]');
  if (footerField) footerField.addEventListener('input', updateChordPreview);
  // Initial render
  updateChordPreview();

  // Live ABC preview
  var notesTA = document.getElementById('raw-notes-textarea');
  if (notesTA) {
    notesTA.addEventListener('input', renderAbcPreview);
    renderAbcPreview();
  }
  var meterSel = document.getElementById('field-meter');
  if (meterSel) meterSel.addEventListener('change', renderAbcPreview);
  var unitField = document.querySelector('select[name="unit"]');
  if (unitField) unitField.addEventListener('input', renderAbcPreview);
});

// Form validation
function validateForm() {
  var title = document.querySelector('input[name="title"]').value.trim();
  if (!title) {
    alert('Title is required.');
    document.querySelector('input[name="title"]').focus();
    return false;
  }

  // Validate tune types have compatible time signatures
  var checks = document.querySelectorAll('#type-menu-dropdown input[type="checkbox"]:checked');
  if (checks.length > 1) {
    var meters = {};
    for (var i = 0; i < checks.length; i++) {
      var ttype = checks[i].name.replace('klass_', '');
      var m = tuneDefaults[ttype] ? tuneDefaults[ttype].meter : '4/4';
      // Group compatible meters: 4/4 and 2/4 and C are compatible
      if (m === '2/4' || m === 'C') m = '4/4';
      meters[m] = 1;
    }
    if (Object.keys(meters).length > 1) {
      alert('The selected tune types have different time signatures and cannot be combined.');
      return false;
    }
  }

  // Validate URL format
  var urlInputs = document.querySelectorAll('input[name^="url_"]');
  for (var i = 0; i < urlInputs.length; i++) {
    var url = urlInputs[i].value.trim();
    if (!url) continue;
    if (!/^https?:\\/\\/.+\\..+/.test(url)) {
      urlInputs[i].style.backgroundColor = '#ffcccc';
      urlInputs[i].focus();
      alert('Invalid URL format: ' + url + '\\nURLs should start with http:// or https://');
      return false;
    }
    urlInputs[i].style.backgroundColor = '';
  }

  // Validate chord cells
  var chordInputs = document.querySelectorAll('#chord-parts-container input[type="text"]');
  for (var i = 0; i < chordInputs.length; i++) {
    var val = chordInputs[i].value;
    if (!val) continue;
    var err = validateChordCell(val);
    if (err) {
      chordInputs[i].style.backgroundColor = '#ffcccc';
      chordInputs[i].focus();
      alert(err);
      return false;
    }
    chordInputs[i].style.backgroundColor = '';
  }

  formChanged = false;
  return true;
}

function validateChordCell(val) {
  // Validate a single chord cell value against the notation spec
  // Valid patterns:
  //   Note: A-H (H = German Bb)
  //   Accidental after note: b (flat), # (sharp)
  //   Quality: m (minor), + (augmented), Dim (diminished), sup (suspended)
  //   Extension: 7, 6, 9 (after note/accidental/quality)
  //   Sustain: - (hold chord)
  //   Multiple chords per cell: just concatenated e.g. AmG
  //   Alt endings: 1: 2: 3: at start
  //   Alternatives: / ( ) for optional/alternative chords
  //   Time sig changes: digits/digits e.g. 7/8
  var j = 0;
  var len = val.length;
  // Allow alternate ending prefix like "1:" "2:" "3:"
  if (j < len && '123'.indexOf(val[j]) >= 0 && j + 1 < len && val[j+1] === ':') {
    j += 2;
  }
  while (j < len) {
    var c = val[j];
    // Parentheses and slash for alternatives
    if (c === '(' || c === ')' || c === '/') { j++; continue; }
    // Sustain dash
    if (c === '-') { j++; continue; }
    // Time signature like 7/8 or 9/8
    if ('0123456789'.indexOf(c) >= 0) {
      var k = j;
      while (k < len && '0123456789'.indexOf(val[k]) >= 0) k++;
      if (k < len && val[k] === '/') {
        k++;
        while (k < len && '0123456789'.indexOf(val[k]) >= 0) k++;
        j = k;
        continue;
      }
      // Bare number not part of time sig or extension - invalid
      return 'Invalid chord: ' + val + '\\nUnexpected character \\'' + c + '\\' at position ' + (j+1) + '.';
    }
    // Note letter A-H
    if ('ABCDEFGH'.indexOf(c) >= 0) {
      j++;
      // Optional accidental: b or #
      if (j < len && (val[j] === 'b' || val[j] === '#')) j++;
      // Optional quality: Dim, sup, m, +
      // Check dim/Dim first (D is also a valid note, so CDim must not parse D as a new note)
      if (j + 2 < len && (val.substring(j, j+3) === 'Dim' || val.substring(j, j+3) === 'dim')) { j += 3; }
      else if (j + 2 < len && (val.substring(j, j+3) === 'sup' || val.substring(j, j+3) === 'Sus' || val.substring(j, j+3) === 'sus')) {
        j += 3;
        // sup is usually followed by a number like sup9
        if (j < len && '0123456789'.indexOf(val[j]) >= 0) j++;
        continue;
      }
      else if (j < len && val[j] === 'm') { j++; }
      else if (j < len && val[j] === '+') { j++; }
      // Optional extension: 7, 6, 9
      if (j < len && ('769'.indexOf(val[j]) >= 0)) j++;
      continue;
    }
    // Anything else is invalid
    return 'Invalid chord: ' + val + '\\nUnexpected character \\'' + c + '\\' at position ' + (j+1) + '.';
  }
  return null;
}

// ========================================================================
// Visual Drag-and-Drop Music Notation Editor
// ========================================================================

// --- Data Model ---
var notationModel = { parts: [] };
var undoStack = [];
var redoStack = [];
var currentTool = null;
var veMode = 'visual'; // 'visual' or 'abc'
var staffGeometry = [];   // array of {y0..y4, spacing, halfSpacing, topY, bottomY, svgTop}
var elementPositions = []; // array of {x, partIdx, elemIdx, charStart, charEnd}
var selectedElements = []; // array of {partIdx, elemIdx}
var isDragging = false;
var lastPointerShift = false;  // Track shift key from pointer events
var dragGhost = null;
var insertionMarker = null;
var lastTuneObj = null;

// Max undo/redo
var kMaxUndo = 50;

function pushUndo() {
  undoStack.push(JSON.stringify(notationModel));
  if (undoStack.length > kMaxUndo) undoStack.shift();
  redoStack = [];
}

function doUndo() {
  if (undoStack.length === 0) return;
  redoStack.push(JSON.stringify(notationModel));
  notationModel = JSON.parse(undoStack.pop());
  selectedElements = [];
  hidePropertyIndicator();
  syncModelToTextarea();
}

function doRedo() {
  if (redoStack.length === 0) return;
  undoStack.push(JSON.stringify(notationModel));
  notationModel = JSON.parse(redoStack.pop());
  selectedElements = [];
  hidePropertyIndicator();
  syncModelToTextarea();
}

// --- ABC Parser ---
function parseAbcToModel(abcText) {
  var model = { parts: [] };
  if (!abcText || !abcText.trim()) {
    model.parts.push({ label: 'A', elements: [] });
    return model;
  }
  var lines = abcText.split('\\n');
  var partLabels = 'ABCDEFGHIJ';
  for (var li = 0; li < lines.length; li++) {
    var line = lines[li].trim();
    if (!line) continue;
    // Skip inline header lines (K:, M:, L:, etc.)
    if (line.length > 1 && line[1] === ':' && 'KMLPQVwW'.indexOf(line[0]) >= 0) continue;
    var elements = parseAbcLine(line);
    var label = partLabels[model.parts.length] || '' + model.parts.length;
    model.parts.push({ label: label, elements: elements });
  }
  if (model.parts.length === 0) {
    model.parts.push({ label: 'A', elements: [] });
  }
  return model;
}

function parseAbcLine(line) {
  var elements = [];
  var i = 0;
  var len = line.length;
  while (i < len) {
    var c = line[i];
    // Whitespace
    if (c === ' ' || c === '\\t') {
      if (elements.length > 0) elements[elements.length - 1].spaceAfter = true;
      i++; continue;
    }
    // Bar lines
    if (c === '|' || c === ':') {
      var bar = '';
      // Collect bar sequence: |, |:, :|, ||, |], [|
      while (i < len && ('|:[]'.indexOf(line[i]) >= 0)) {
        bar += line[i]; i++;
      }
      // Normalize common bar patterns
      if (bar === '|:') elements.push({type:'bar', subtype:'|:'});
      else if (bar === ':|') elements.push({type:'bar', subtype:':|'});
      else if (bar === '||' || bar === '|]' || bar === '[|') elements.push({type:'bar', subtype:bar});
      else if (bar === '|') elements.push({type:'bar', subtype:'|'});
      else {
        // Fallback: multiple bars
        for (var b = 0; b < bar.length; b++) {
          if (bar[b] === '|') elements.push({type:'bar', subtype:'|'});
        }
      }
      continue;
    }
    // Tuplet marker (3 → triplet, etc.) — skip the marker
    if (c === '(' && i + 1 < len && '23456789'.indexOf(line[i+1]) >= 0) {
      i += 2; // skip (N
      continue;
    }
    // Slur start
    if (c === '(') {
      // Mark next note as slur start
      i++;
      var innerElems = parseSlurGroup(line, i);
      i = innerElems.newIdx;
      for (var si = 0; si < innerElems.elems.length; si++) {
        elements.push(innerElems.elems[si]);
      }
      continue;
    }
    // Grace notes {notes}
    if (c === '{') {
      i++; // skip {
      // Check for acciaccatura marker /
      var acciaccatura = false;
      if (i < len && line[i] === '/') { acciaccatura = true; i++; }
      var graceNotes = [];
      while (i < len && line[i] !== '}') {
        if (isNoteStart(line, i)) {
          var gn = parseNote(line, i);
          i = gn.newIdx;
          gn.elem.grace = true;
          graceNotes.push(gn.elem);
        } else {
          i++; // skip unrecognized inside grace
        }
      }
      if (i < len && line[i] === '}') i++; // skip }
      for (var gi = 0; gi < graceNotes.length; gi++) {
        elements.push(graceNotes[gi]);
      }
      continue;
    }
    // Rest
    if (c === 'z' || c === 'x') {
      i++;
      var dur = parseDuration(line, i);
      i = dur.newIdx;
      elements.push({type:'rest', duration:dur.duration});
      continue;
    }
    // Note: accidental? + pitch letter + octave modifiers + duration + tie
    if (isNoteStart(line, i)) {
      var note = parseNote(line, i);
      i = note.newIdx;
      elements.push(note.elem);
      continue;
    }
    // Unrecognized — skip
    i++;
  }
  return elements;
}

function isNoteStart(line, i) {
  var c = line[i];
  if ('ABCDEFGabcdefg'.indexOf(c) >= 0) return true;
  if ((c === '^' || c === '_' || c === '=') && i + 1 < line.length) {
    var next = line[i+1];
    if (next === '^' || next === '_') {
      return i + 2 < line.length && 'ABCDEFGabcdefg'.indexOf(line[i+2]) >= 0;
    }
    return 'ABCDEFGabcdefg'.indexOf(next) >= 0;
  }
  return false;
}

function parseNote(line, i) {
  var accidental = null;
  // Accidental prefix
  if (line[i] === '^') {
    if (i + 1 < line.length && line[i+1] === '^') { accidental = '^^'; i += 2; }
    else { accidental = '^'; i++; }
  } else if (line[i] === '_') {
    if (i + 1 < line.length && line[i+1] === '_') { accidental = '__'; i += 2; }
    else { accidental = '_'; i++; }
  } else if (line[i] === '=') {
    accidental = '='; i++;
  }
  // Pitch letter
  var pitchChar = line[i]; i++;
  var isLower = (pitchChar === pitchChar.toLowerCase());
  var pitch = pitchChar.toUpperCase();
  var octave = isLower ? 1 : 0;
  // Octave modifiers
  while (i < line.length) {
    if (line[i] === "'") { octave++; i++; }
    else if (line[i] === ',') { octave--; i++; }
    else break;
  }
  // Duration
  var dur = parseDuration(line, i);
  i = dur.newIdx;
  // Tie
  var tied = false;
  if (i < line.length && line[i] === '-') { tied = true; i++; }
  return {
    newIdx: i,
    elem: {
      type: 'note',
      pitch: pitch,
      octave: octave,
      duration: dur.duration,
      accidental: accidental,
      tied: tied,
      slurStart: false,
      slurEnd: false
    }
  };
}

function parseDuration(line, i) {
  var dur = '';
  // Number prefix (multiplier)
  while (i < line.length && '0123456789'.indexOf(line[i]) >= 0) {
    dur += line[i]; i++;
  }
  // Slash(es) for division: / = /2, // = /4, /// = /8, or /N for explicit
  if (i < line.length && line[i] === '/') {
    // Count consecutive slashes
    var slashCount = 0;
    while (i < line.length && line[i] === '/') {
      slashCount++; i++;
    }
    // Check for explicit denominator after slashes
    var denomStr = '';
    while (i < line.length && '0123456789'.indexOf(line[i]) >= 0) {
      denomStr += line[i]; i++;
    }
    if (denomStr) {
      // Explicit: /N or //N etc. — multiple slashes with number
      // In standard ABC, /3 means divide by 3. Extra slashes before a number
      // are unusual but we handle them: each extra slash doubles the denominator
      var denom = parseInt(denomStr);
      for (var s = 1; s < slashCount; s++) denom *= 2;
      dur += '/' + denom;
    } else {
      // No number: each slash halves — / = /2, // = /4, /// = /8
      var denom = Math.pow(2, slashCount);
      dur += '/' + denom;
    }
  }
  return { newIdx: i, duration: dur };
}

function parseSlurGroup(line, startIdx) {
  // Parse notes until closing ), marking first as slurStart and last as slurEnd
  var elems = [];
  var i = startIdx;
  var depth = 1;
  while (i < line.length && depth > 0) {
    if (line[i] === ')') { depth--; i++; continue; }
    if (line[i] === '(') { depth++; i++; continue; }
    if (line[i] === ' ' || line[i] === '\\t') {
      if (elems.length > 0) elems[elems.length - 1].spaceAfter = true;
      i++; continue;
    }
    if (line[i] === '|') {
      elems.push({type:'bar', subtype:'|'}); i++; continue;
    }
    if (isNoteStart(line, i)) {
      var note = parseNote(line, i);
      i = note.newIdx;
      elems.push(note.elem);
    } else if (line[i] === 'z' || line[i] === 'x') {
      i++;
      var dur = parseDuration(line, i);
      i = dur.newIdx;
      elems.push({type:'rest', duration:dur.duration});
    } else {
      i++;
    }
  }
  if (elems.length > 0) {
    if (elems[0].type === 'note') elems[0].slurStart = true;
    for (var k = elems.length - 1; k >= 0; k--) {
      if (elems[k].type === 'note') { elems[k].slurEnd = true; break; }
    }
  }
  return { elems: elems, newIdx: i };
}

// --- ABC Serializer ---
function modelToAbc(model) {
  var lines = [];
  for (var p = 0; p < model.parts.length; p++) {
    var part = model.parts[p];
    var line = '';
    var inSlur = false;
    for (var e = 0; e < part.elements.length; e++) {
      var el = part.elements[e];
      if (el.type === 'note') {
        if (el.slurStart && !inSlur) { line += '('; inSlur = true; }
        // Grace note wrapper
        if (el.grace) line += '{';
        // Accidental
        if (el.accidental) line += el.accidental;
        // Pitch letter with octave
        if (el.octave >= 1) {
          line += el.pitch.toLowerCase();
          for (var o = 1; o < el.octave; o++) line += "'";
        } else if (el.octave <= -1) {
          line += el.pitch.toUpperCase();
          for (var o = 0; o > el.octave; o--) line += ',';
        } else {
          line += el.pitch.toUpperCase();
        }
        // Duration (skip for grace notes)
        if (el.duration && !el.grace) line += el.duration;
        if (el.grace) line += '}';
        // Tie
        if (el.tied) line += '-';
        if (el.slurEnd && inSlur) { line += ')'; inSlur = false; }
      } else if (el.type === 'rest') {
        line += 'z';
        if (el.duration) line += el.duration;
      } else if (el.type === 'bar') {
        line += el.subtype || '|';
      }
      if (el.spaceAfter) line += ' ';
    }
    if (inSlur) line += ')';
    lines.push(line);
  }
  return lines.join('\\n');
}

function syncModelToTextarea() {
  var textarea = document.getElementById('raw-notes-textarea');
  if (!textarea) return;
  var abc = modelToAbc(notationModel);
  textarea.value = abc;
  formChanged = true;
  doRenderAbc();
}

// --- Mode Toggle ---
function toggleEditorMode(mode) {
  veMode = mode;
  var visBtn = document.getElementById('ve-mode-visual-btn');
  var abcBtn = document.getElementById('ve-mode-abc-btn');
  var toolbar = document.getElementById('ve-toolbar');
  var textareaPane = document.getElementById('ve-textarea-pane');
  var propPanel = document.getElementById('ve-property-panel');
  if (mode === 'visual') {
    if (visBtn) { visBtn.classList.add('ve-mode-active'); }
    if (abcBtn) { abcBtn.classList.remove('ve-mode-active'); }
    if (toolbar) toolbar.style.display = 'flex';
    if (textareaPane) textareaPane.style.display = 'none';
    if (propPanel) propPanel.style.display = 'none';
    // Parse textarea content into model
    var textarea = document.getElementById('raw-notes-textarea');
    if (textarea) {
      notationModel = parseAbcToModel(textarea.value);
    }
    selectedElements = [];
    doRenderAbc();
  } else {
    if (visBtn) { visBtn.classList.remove('ve-mode-active'); }
    if (abcBtn) { abcBtn.classList.add('ve-mode-active'); }
    if (toolbar) toolbar.style.display = 'none';
    if (textareaPane) textareaPane.style.display = 'block';
    if (propPanel) propPanel.style.display = 'none';
    selectedElements = [];
    currentTool = null;
    clearToolSelection();
    doRenderAbc();
  }
}

function clearToolSelection() {
  var btns = document.querySelectorAll('.ve-tool-btn');
  for (var i = 0; i < btns.length; i++) {
    btns[i].classList.remove('ve-tool-active');
  }
  currentTool = null;
}

function activateSelectTool() {
  clearToolSelection();
  currentTool = null;
  var selBtn = document.getElementById('ve-select-tool');
  if (selBtn) selBtn.classList.add('ve-tool-active');
  var editorEl = document.querySelector('.edit-form');
  if (editorEl) editorEl.classList.remove('ve-scissors-active');
}

// Convert a selectable index (from elementPositions, which excludes bars
// and grace notes) back to a model element index.
function selectableIdxToModelIdx(part, selIdx) {
  var selectableCount = 0;
  for (var j = 0; j < part.elements.length; j++) {
    if (part.elements[j].type === 'bar') continue;
    if (part.elements[j].grace) continue;
    if (selectableCount === selIdx) return j;
    selectableCount++;
  }
  return part.elements.length;
}

// --- SVG Coordinate Helpers ---
// Convert a point from an element's local coordinate space to the SVG root
// coordinate space (accounting for all parent <g> transforms).
function localToSvgRoot(svg, elem, localX, localY) {
  // Convert element-local coordinates to SVG viewBox coordinates.
  // We go: element-local -> screen (via elem.getScreenCTM)
  //     -> viewBox (via svg.getScreenCTM inverse)
  // This ensures the result is in the same coordinate space as
  // clientToSvgCoords() which also produces viewBox coordinates.
  // NOTE: getCTM() includes the viewBox-to-viewport scaling and
  // would give viewport-pixel coords, not viewBox coords.
  var pt = svg.createSVGPoint();
  pt.x = localX;
  pt.y = localY;
  var elemSCTM = elem.getScreenCTM();
  var svgSCTM = svg.getScreenCTM();
  if (elemSCTM && svgSCTM) {
    var screenPt = pt.matrixTransform(elemSCTM);
    return screenPt.matrixTransform(svgSCTM.inverse());
  }
  return pt;
}

// Convert client/screen coordinates to SVG root coordinates.
function clientToSvgCoords(svg, clientX, clientY) {
  var pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  // getScreenCTM() gives transform from SVG viewport to screen;
  // its inverse converts screen coords back to SVG viewport coords.
  var screenCTM = svg.getScreenCTM();
  if (screenCTM) {
    return pt.matrixTransform(screenCTM.inverse());
  }
  return pt;
}

// --- Staff Geometry Extraction ---
// Finds the 5-line staff systems by detecting actual horizontal <path> elements
// in the SVG. Staff lines are the WIDEST horizontal segments — much wider than
// beams, ledger lines, or bar lines. We collect all horizontal segments with
// their widths, then keep only those at least 80%% as wide as the maximum.
function extractStaffGeometry(svgContainer) {
  staffGeometry = [];
  if (!svgContainer) return;
  var svg = svgContainer.querySelector('svg');
  if (!svg) return;

  // Collect all horizontal segments with their widths and Y positions
  var allSegments = []; // {y: rootY, width: segWidth}

  // Scan all <path> elements for horizontal M...L segments.
  // abcjs puts multiple staff lines into a single <path> element.
  var segRe = /M\\s*([\\d.-]+)[,\\s]+([\\d.-]+)\\s*L\\s*([\\d.-]+)[,\\s]+([\\d.-]+)/g;
  var paths = svg.querySelectorAll('path');
  for (var i = 0; i < paths.length; i++) {
    var d = paths[i].getAttribute('d');
    if (!d) continue;
    var seg;
    segRe.lastIndex = 0;
    while ((seg = segRe.exec(d)) !== null) {
      var x1 = parseFloat(seg[1]), y1 = parseFloat(seg[2]);
      var x2 = parseFloat(seg[3]), y2 = parseFloat(seg[4]);
      // Must be horizontal (same Y)
      if (Math.abs(y1 - y2) > 0.5) continue;
      var segWidth = Math.abs(x2 - x1);
      if (segWidth < 10) continue; // skip tiny segments
      var rootPt = localToSvgRoot(svg, paths[i], (x1 + x2) / 2, y1);
      allSegments.push({ y: rootPt.y, width: segWidth });
    }
  }

  // Also check <line> elements
  var lineElems = svg.querySelectorAll('line');
  for (var i = 0; i < lineElems.length; i++) {
    var lx1 = parseFloat(lineElems[i].getAttribute('x1'));
    var ly1 = parseFloat(lineElems[i].getAttribute('y1'));
    var lx2 = parseFloat(lineElems[i].getAttribute('x2'));
    var ly2 = parseFloat(lineElems[i].getAttribute('y2'));
    if (isNaN(lx1) || isNaN(ly1) || isNaN(lx2) || isNaN(ly2)) continue;
    if (lineElems[i].classList.contains('ve-insertion-marker')) continue;
    if (Math.abs(ly1 - ly2) > 0.5) continue;
    var segWidth = Math.abs(lx2 - lx1);
    if (segWidth < 10) continue;
    var rootPt = localToSvgRoot(svg, lineElems[i], (lx1 + lx2) / 2, ly1);
    allSegments.push({ y: rootPt.y, width: segWidth });
  }

  if (allSegments.length < 5) return;

  // Find the maximum width among all horizontal segments.
  // Staff lines are always the widest (they span nearly the full staff width).
  // Beams, ledger lines, etc. are much shorter.
  var maxWidth = 0;
  for (var i = 0; i < allSegments.length; i++) {
    if (allSegments[i].width > maxWidth) maxWidth = allSegments[i].width;
  }

  // Keep only segments that are at least 80%% as wide as the widest.
  // This eliminates beams (typically 10-30%% of staff width) while keeping
  // staff lines (typically 95-100%% of max width).
  var minWidth = maxWidth * 0.8;
  var staffLineYs = [];
  for (var i = 0; i < allSegments.length; i++) {
    if (allSegments[i].width >= minWidth) {
      staffLineYs.push(allSegments[i].y);
    }
  }

  if (staffLineYs.length < 5) return;

  // Sort by Y (top of screen = smallest Y)
  staffLineYs.sort(function(a, b) { return a - b; });

  // De-duplicate Y values that are nearly identical
  var uniqueYs = [staffLineYs[0]];
  for (var i = 1; i < staffLineYs.length; i++) {
    if (Math.abs(staffLineYs[i] - uniqueYs[uniqueYs.length - 1]) > 0.5) {
      uniqueYs.push(staffLineYs[i]);
    }
  }

  if (uniqueYs.length < 5) return;

  // Find staff systems: groups of exactly 5 EVENLY-SPACED horizontal lines.
  var used = {};
  for (var i = 0; i <= uniqueYs.length - 5; i++) {
    if (used[i]) continue;
    var ys = uniqueYs.slice(i, i + 5);
    var spacing = (ys[4] - ys[0]) / 4;
    if (spacing < 1) continue; // degenerate
    var ok = true;
    for (var j = 0; j < 4; j++) {
      var gap = ys[j + 1] - ys[j];
      if (Math.abs(gap - spacing) > spacing * 0.15) { ok = false; break; }
    }
    if (!ok) continue;
    var halfSpacing = spacing / 2;
    staffGeometry.push({
      y0: ys[0], y1: ys[1], y2: ys[2], y3: ys[3], y4: ys[4],
      spacing: spacing,
      halfSpacing: halfSpacing,
      topY: ys[0] - spacing * 2,
      bottomY: ys[4] + spacing * 2
    });
    for (var j = 0; j < 5; j++) used[i + j] = true;
  }
}

// --- Per-Part Rendering Data ---
// Each entry: { container, svg, tuneObj, geo, elementPositions, partIdx }
var partRenderings = [];

function buildElementPositionMap(tuneObj, svgEl) {
  var positions = [];
  if (!tuneObj || !tuneObj[0]) return positions;
  try {
    var selectables = tuneObj[0].getSelectableArray();
    if (!selectables) return positions;
    for (var i = 0; i < selectables.length; i++) {
      var sel = selectables[i];
      if (!sel || sel.absEl === undefined) continue;
      var absEl = sel.absEl;
      if (!absEl) continue;
      // Use the rendered SVG element's bounding box for positions in viewBox
      // coords, which matches what clientToSvgCoords returns for clicks.
      // absEl.x is in abcjs's internal layout coords which may differ.
      var x = absEl.x || 0;
      var w = absEl.w || 10;
      if (svgEl && absEl.elemset && absEl.elemset.length > 0) {
        try {
          var svgElem = absEl.elemset[0];
          // Use getBoundingClientRect -> clientToSvgCoords so element positions
          // use the exact same transform path as click coordinates
          var rect = svgElem.getBoundingClientRect();
          var rootPt = clientToSvgCoords(svgEl, rect.left, rect.top);
          var rootPt2 = clientToSvgCoords(svgEl, rect.right, rect.top);
          // bbox-based position used
          x = rootPt.x;
          w = rootPt2.x - rootPt.x;
          if (w < 1) w = 10;
        } catch(ex) {}
      }
      positions.push({
        x: x,
        w: w,
        centerX: x + w / 2,
        charStart: sel.startChar || 0,
        charEnd: sel.endChar || 0
      });
    }
  } catch(e) {}
  return positions;
}

// Build a map from model element index to SVG element arrays for highlighting.
// Uses char offset matching between model elements and abcjs selectables.
// Also builds beam groups: arrays of {elemIndices, svgElems} for beam highlighting.
function buildElemSvgMap(tuneObj, partIdx) {
  var result = {map: {}, beams: []};
  if (!tuneObj || !tuneObj[0]) return result;
  if (partIdx >= notationModel.parts.length) return result;
  var part = notationModel.parts[partIdx];

  // Compute the header length for this part's ABC
  var key = document.getElementById('field-key').value || 'C';
  var meterSel = document.getElementById('field-meter');
  var meter = meterSel ? meterSel.value : '4/4';
  var unitField = document.querySelector('select[name="unit"]');
  var unit = unitField ? unitField.value : '1/8';
  var headerLen = ('X:1\\nK:' + key + '\\nL:' + unit + '\\nM:' + meter + '\\n').length;

  // Pre-compute char start positions for each model element
  var elemCharStarts = [];
  var pos = 0;
  for (var e = 0; e < part.elements.length; e++) {
    elemCharStarts.push(headerLen + pos);
    pos += elementAbcLength(part.elements[e]);
  }

  var map = result.map;
  var beamRefs = [];  // [{ref, elemIndices}] - track unique beam objects

  try {
    var selectables = tuneObj[0].getSelectableArray();
    if (!selectables) return result;
    for (var j = 0; j < selectables.length; j++) {
      var sa = selectables[j];
      if (!sa || !sa.absEl || !sa.absEl.elemset) continue;
      // startChar lives on absEl.abcelem in abcjs 6.x
      var sc = (sa.absEl.abcelem && sa.absEl.abcelem.startChar !== undefined) ? sa.absEl.abcelem.startChar : undefined;
      if (sc === undefined) continue;
      // Find which model element this selectable belongs to
      // Use core length (without spaceAfter) so trailing spaces don't cause
      // the next element's startChar to match this element's range.
      // If startChar lands on a trailing space, attribute to the next element.
      var matchedIdx = -1;
      for (var e = 0; e < elemCharStarts.length; e++) {
        var eStart = elemCharStarts[e];
        var eCoreLen = elementAbcCoreLength(part.elements[e]);
        if (sc >= eStart && sc < eStart + eCoreLen) {
          matchedIdx = e;
          break;
        }
        // Check if sc falls on trailing space — attribute to next element
        if (part.elements[e].spaceAfter && sc >= eStart + eCoreLen && sc < eStart + elementAbcLength(part.elements[e])) {
          matchedIdx = (e + 1 < elemCharStarts.length) ? e + 1 : e;
          break;
        }
      }
      if (matchedIdx >= 0) {
        var me = matchedIdx;
        if (!map[me]) map[me] = [];
        for (var k = 0; k < sa.absEl.elemset.length; k++) {
          map[me].push(sa.absEl.elemset[k]);
        }
        // When abcjs folds a grace note with its following note into
        // one selectable, also map the SVG elements to the next
        // (main) note so highlighting works for both elements.
        if (part.elements[me].grace && me + 1 < part.elements.length) {
          if (!map[me + 1]) map[me + 1] = [];
          for (var k = 0; k < sa.absEl.elemset.length; k++) {
            map[me + 1].push(sa.absEl.elemset[k]);
          }
        }
      }
      // Track beam groups
      if (matchedIdx >= 0 && sa.absEl.beam) {
        var beamRef = sa.absEl.beam;
        var found = false;
        for (var bi = 0; bi < beamRefs.length; bi++) {
          if (beamRefs[bi].ref === beamRef) {
            beamRefs[bi].elemIndices.push(matchedIdx);
            found = true;
            break;
          }
        }
        if (!found) {
          beamRefs.push({ref: beamRef, elemIndices: [matchedIdx]});
        }
      }
    }
    // Extract beam X ranges for matching to SVG beam paths
    for (var bi = 0; bi < beamRefs.length; bi++) {
      var br = beamRefs[bi];
      // Get X range from beam geometry (beam.beams[] has startX/endX)
      var bdata = br.ref.beams;
      if (bdata && bdata.length > 0) {
        result.beams.push({
          elemIndices: br.elemIndices,
          startX: bdata[0].startX,
          endX: bdata[0].endX
        });
      }
    }
  } catch(ex) {}

  // Map bar line SVG elements to model bar elements by position order.
  // abcjs doesn't include bars in getSelectableArray(), so we scan the SVG directly.
  try {
    var renderTarget = document.getElementById('ve-part-render-' + partIdx);
    if (renderTarget) {
      var svg = renderTarget.querySelector('svg');
      if (svg) {
        var barSvgEls = svg.querySelectorAll('.abcjs-bar');
        // Collect model indices of bar elements
        var barModelIndices = [];
        for (var bi = 0; bi < part.elements.length; bi++) {
          if (part.elements[bi].type === 'bar') barModelIndices.push(bi);
        }
        // Match nth SVG bar to nth model bar
        var limit = Math.min(barSvgEls.length, barModelIndices.length);
        for (var bi = 0; bi < limit; bi++) {
          var midx = barModelIndices[bi];
          if (!map[midx]) map[midx] = [];
          map[midx].push(barSvgEls[bi]);
        }
      }
    }
  } catch(ex) {}

  return result;
}

// --- Y to Pitch Conversion ---
// Treble clef staff lines bottom-to-top: E4, G4, B4, D5, F5
// Staff positions: E4=0, F4=1, G4=2, A4=3, B4=4, C5=5, D5=6, E5=7, F5=8
// Line 4 (top) = F5 = position 8, Line 0 (bottom) = E4 = position 0
var staffNotes = ['C','D','E','F','G','A','B'];

function yToStaffPosition(y, geo) {
  // geo.y0 = top line (F5, position 8), geo.y4 = bottom line (E4, position 0)
  // Position increases upward
  var offset = (y - geo.y0) / geo.halfSpacing;
  var pos = 8 - Math.round(offset);
  return pos;
}

function staffPositionToPitch(pos) {
  // Staff position 0 = E4 = bottom line of treble clef
  // ABC convention: uppercase = C4-B4 (octave 0), lowercase = C5-B5 (octave 1)
  // E4 = uppercase 'E' = octave 0, diatonic index 2
  // Diatonic: C=0, D=1, E=2, F=3, G=4, A=5, B=6
  var baseDiatonic = 2; // E
  var baseOctave = 0;   // E4 = octave 0 (uppercase in ABC)
  var diatonic = baseDiatonic + pos;
  // Normalize: diatonic 0-6 = C-B
  var octaveShift = Math.floor(diatonic / 7);
  diatonic = ((diatonic %% 7) + 7) %% 7;
  var octave = baseOctave + octaveShift;
  return { pitch: staffNotes[diatonic], octave: octave };
}

function pitchToStaffPosition(pitch, octave) {
  var noteIdx = staffNotes.indexOf(pitch);
  if (noteIdx < 0) noteIdx = 0;
  // E4 (noteIdx=2, octave=0) = position 0
  var diatonic = noteIdx + octave * 7;
  var pos = diatonic - 2; // subtract E4's diatonic index
  return pos;
}

function pitchToDisplayName(pitch, octave) {
  // Convert to scientific pitch notation
  // Our octave 0 = ABC uppercase = C4-B4 range
  var sciOctave = octave + 4;
  // Adjust: C is start of scientific octave
  var noteIdx = staffNotes.indexOf(pitch);
  if (noteIdx >= 0 && noteIdx < 2) {
    // C, D are below E in the same ABC octave but same scientific octave
  }
  return pitch + sciOctave;
}

// --- X to Insertion Index ---
function xToInsertionIndex(dropX, partIdx) {
  // Build a combined position list of all model elements (notes, rests, AND bars)
  // so insertion respects bar line boundaries.
  if (partIdx >= partRenderings.length) return 0;
  var pr = partRenderings[partIdx];
  var part = notationModel.parts[pr.partIdx];
  if (!part) return 0;

  // Collect X positions for all model elements
  var allPositions = []; // [{modelIdx, centerX}]

  // Get note/rest positions from selectable positions
  var positions = pr.elementPositions || [];
  var selIdx = 0;
  for (var j = 0; j < part.elements.length; j++) {
    var el = part.elements[j];
    if (el.type === 'bar') continue;
    if (el.grace) continue;
    if (selIdx < positions.length) {
      allPositions.push({modelIdx: j, centerX: positions[selIdx].centerX});
    }
    selIdx++;
  }

  // Get bar positions from SVG
  var svg = pr.renderTarget ? pr.renderTarget.querySelector('svg') : null;
  if (svg) {
    var barSvgEls = svg.querySelectorAll('.abcjs-bar');
    var barModelIndices = [];
    for (var j = 0; j < part.elements.length; j++) {
      if (part.elements[j].type === 'bar') barModelIndices.push(j);
    }
    var limit = Math.min(barSvgEls.length, barModelIndices.length);
    for (var bi = 0; bi < limit; bi++) {
      try {
        var bbox = barSvgEls[bi].getBBox();
        allPositions.push({modelIdx: barModelIndices[bi], centerX: bbox.x + bbox.width / 2});
      } catch(ex) {}
    }
  }

  if (allPositions.length === 0) return 0;

  // Sort by X position
  allPositions.sort(function(a, b) { return a.centerX - b.centerX; });

  // Find where the click falls
  for (var i = 0; i < allPositions.length; i++) {
    if (dropX < allPositions[i].centerX) {
      return allPositions[i].modelIdx;
    }
  }
  // Click is after all elements — insert at the end
  return part.elements.length;
}

// --- Duration Mapping ---
function toolToDuration(toolName) {
  // Map tool name to ABC duration suffix based on L: unit note
  var unitField = document.querySelector('select[name="unit"]');
  var unit = unitField ? unitField.value.trim() : '1/8';
  // Parse unit as fraction
  var unitNum = 1, unitDen = 8;
  var um = unit.match(/(\\d+)\\/(\\d+)/);
  if (um) { unitNum = parseInt(um[1]); unitDen = parseInt(um[2]); }
  else if (unit.match(/^\\d+$/)) { unitNum = parseInt(unit); unitDen = 1; }
  var unitVal = unitNum / unitDen;

  // Target durations in whole notes
  var targets = {
    'whole': 1,
    'half': 0.5,
    'quarter': 0.25,
    'eighth': 0.125,
    'sixteenth': 0.0625
  };
  var target = targets[toolName];
  if (!target) return '';
  var ratio = target / unitVal;
  if (Math.abs(ratio - 1) < 0.001) return '';
  if (Math.abs(ratio - 2) < 0.001) return '2';
  if (Math.abs(ratio - 4) < 0.001) return '4';
  if (Math.abs(ratio - 8) < 0.001) return '8';
  if (Math.abs(ratio - 0.5) < 0.001) return '/2';
  if (Math.abs(ratio - 0.25) < 0.001) return '/4';
  if (Math.abs(ratio - 0.125) < 0.001) return '/8';
  if (Math.abs(ratio - 3) < 0.001) return '3';
  // Default: return numeric ratio
  if (ratio >= 1) return '' + Math.round(ratio);
  return '/' + Math.round(1/ratio);
}

// Halve a duration string. Returns null if result would be too short (< 1/8 unit).
function halfDuration(durStr) {
  if (durStr === undefined || durStr === null) durStr = '';
  // Parse duration string into numerator/denominator ratio relative to unit
  var num = 1, den = 1;
  var m = durStr.match(/^(\\d+)\\/(\\d+)$/);
  if (m) { num = parseInt(m[1]); den = parseInt(m[2]); }
  else {
    m = durStr.match(/^\\/(\\d+)$/);
    if (m) { num = 1; den = parseInt(m[1]); }
    else {
      m = durStr.match(/^(\\d+)$/);
      if (m) { num = parseInt(m[1]); den = 1; }
      // else: empty string means 1/1
    }
  }
  // Halve: multiply denominator by 2
  den *= 2;
  // Simplify
  var g = gcd(num, den);
  num /= g; den /= g;
  // Check minimum: don't go below 1/8 of a unit
  if (num / den < 1/8 - 0.001) return null;
  // Convert back to ABC duration string
  if (num === 1 && den === 1) return '';
  if (den === 1) return '' + num;
  if (num === 1) return '/' + den;
  return '' + num + '/' + den;
}

function gcd(a, b) { while (b) { var t = b; b = a %% b; a = t; } return a; }

// Split a note element in the model at the given index, inserting a second note after it.
// Returns true if split was performed, false if duration can't be halved further.
function splitNoteElement(part, elemIdx) {
  var el = part.elements[elemIdx];
  if (el.type !== 'note' && el.type !== 'rest') return false;
  if (el.grace) return false;
  var half = halfDuration(el.duration || '');
  if (half === null) return false;
  // Create the second element (copy of original)
  var newEl = {type: el.type, duration: half};
  if (el.type === 'note') {
    newEl.pitch = el.pitch;
    newEl.octave = el.octave;
    if (el.accidental) newEl.accidental = el.accidental;
    // Transfer slurEnd and tied from original to new element
    if (el.slurEnd) { newEl.slurEnd = true; el.slurEnd = false; }
    if (el.tied) { newEl.tied = true; el.tied = false; }
    // Transfer spaceAfter from original to new element
    if (el.spaceAfter) { newEl.spaceAfter = true; el.spaceAfter = false; }
  } else {
    // rest: transfer spaceAfter
    if (el.spaceAfter) { newEl.spaceAfter = true; el.spaceAfter = false; }
  }
  // Update original element's duration to half
  el.duration = half;
  // Insert new element after original
  part.elements.splice(elemIdx + 1, 0, newEl);
  return true;
}

// --- Render Integration ---
var origDoRenderAbc = null;

function veDoRenderAbc() {
  var textarea = document.getElementById('raw-notes-textarea');
  var previewEl = document.getElementById('abcjs-preview');
  if (!textarea || !previewEl || typeof ABCJS === 'undefined') return;

  var raw = textarea.value.trim();
  if (!raw && veMode !== 'visual') {
    previewEl.innerHTML = '<div style="color:#666; font-style:italic; padding:20px">Enter ABC notation or use the visual editor above</div>';
    partRenderings = [];
    updatePartHeaders();
    return;
  }
  if (!raw && veMode === 'visual') {
    // Ensure model has at least one part for visual editing
    if (notationModel.parts.length === 0) {
      notationModel.parts.push({ label: 'A', elements: [{type: 'bar', subtype: '|'}] });
    }
  }

  var key = document.getElementById('field-key').value || 'C';
  var meterSel = document.getElementById('field-meter');
  var meter = meterSel ? meterSel.value : '4/4';
  var unitField = document.querySelector('select[name="unit"]');
  var unit = unitField ? unitField.value : '1/8';

  if (veMode !== 'visual') {
    // ABC text mode: render all parts into one SVG as before
    var lines = raw.split('\\n');
    var abc = 'X:1\\nK:' + key + '\\nL:' + unit + '\\nM:' + meter + '\\n';
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (line.length > 1 && line[1] === ':') {
        abc += line + '\\n';
      } else {
        abc += 'M:' + meter + '\\n' + line + '\\n';
      }
    }
    ABCJS.renderAbc("abcjs-preview", abc, {
      responsive: "resize", staffwidth: 500, add_classes: true
    });
    partRenderings = [];
    updatePartHeaders();
    return;
  }

  // Visual mode: render each part into its own container
  var partLabels = 'ABCDEFGHIJ';
  previewEl.innerHTML = '';
  partRenderings = [];

  for (var p = 0; p < notationModel.parts.length; p++) {
    var part = notationModel.parts[p];
    var label = part.label || (p < partLabels.length ? partLabels[p] : '' + p);

    // Create part container with label
    var partContainer = document.createElement('div');
    partContainer.className = 've-part-container';
    partContainer.setAttribute('data-part-idx', '' + p);

    var partLabel = document.createElement('div');
    partLabel.className = 've-part-label';
    partLabel.setAttribute('data-part-idx', '' + p);
    partLabel.textContent = 'Part ' + label;
    if (notationModel.parts.length > 1) {
      var removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 've-part-label-remove';
      removeBtn.innerHTML = '&times;';
      removeBtn.title = 'Remove part ' + label;
      removeBtn.setAttribute('data-part-idx', '' + p);
      removeBtn.addEventListener('click', function(ev) {
        ev.stopPropagation();
        var idx = parseInt(this.getAttribute('data-part-idx'));
        removeNotePart(idx);
      });
      partLabel.appendChild(removeBtn);
    }
    setupPartLabelDrag(partLabel, p);
    partContainer.appendChild(partLabel);

    var renderTarget = document.createElement('div');
    renderTarget.className = 've-part-render';
    renderTarget.id = 've-part-render-' + p;
    partContainer.appendChild(renderTarget);

    previewEl.appendChild(partContainer);

    // Build ABC for this single part
    var partAbc = modelToAbcPart(part);
    var abc = 'X:1\\nK:' + key + '\\nL:' + unit + '\\nM:' + meter + '\\n' + partAbc + '\\n';

    var renderOpts = {
      responsive: "resize",
      staffwidth: 500,
      add_classes: true,
      selectionColor: "#000000",
      clickListener: (function(partIdx) {
        return function(abcElem, tuneNumber, classes, analysis, drag, mouseEvent) {
          veClickListener(abcElem, tuneNumber, classes, analysis, drag, mouseEvent, partIdx);
        };
      })(p),
      dragging: false
    };

    var tuneObj = ABCJS.renderAbc('ve-part-render-' + p, abc, renderOpts);

    partRenderings.push({
      container: partContainer,
      renderTarget: renderTarget,
      tuneObj: tuneObj,
      geo: null,
      elementPositions: [],
      elemSvgMap: {},   // model elemIdx -> array of SVG elements
      beamGroups: [],   // [{elemIndices: [...], svgElems: [...]}]
      partIdx: p
    });
  }

  // "+ Add Part" button below last part
  var addPartBtn = document.createElement('button');
  addPartBtn.type = 'button';
  addPartBtn.className = 've-add-part-btn';
  addPartBtn.textContent = '+ Add Part';
  addPartBtn.addEventListener('click', function() {
    addNotePart(notationModel.parts.length);
  });
  previewEl.appendChild(addPartBtn);

  // Post-render: extract geometry for each part
  setTimeout(function() {
    for (var i = 0; i < partRenderings.length; i++) {
      var pr = partRenderings[i];
      // Extract single staff geometry for this part
      staffGeometry = [];
      extractStaffGeometry(pr.renderTarget);
      pr.geo = staffGeometry.length > 0 ? staffGeometry[0] : null;
      var partSvg = pr.renderTarget.querySelector('svg');
      pr.elementPositions = buildElementPositionMap(pr.tuneObj, partSvg);
      // Build model-index to SVG-elements map and beam groups
      var svgMapResult = buildElemSvgMap(pr.tuneObj, pr.partIdx);
      pr.elemSvgMap = svgMapResult.map;
      pr.beamGroups = svgMapResult.beams;
      // Add wider hit areas to thin bar lines, beam bars, and slurs for easier clicking
      if (partSvg) { addBarHitAreas(partSvg); addBeamHitAreas(partSvg, pr.partIdx); addSlurHitAreas(partSvg, pr.partIdx); }
    }
    updatePartHeaders();
    highlightSelected();
  }, 50);
}

// --- Click Listener (abcjs callback) ---
// partIdx is passed via closure from per-part render options
function veClickListener(abcElem, tuneNumber, classes, analysis, drag, mouseEvent, partIdx) {
  if (veMode !== 'visual') return;
  if (isDragging) return;  // Suppress during palette drag
  if (partIdx === undefined) partIdx = 0;

  // Scissors tool: split the clicked note/rest
  if (currentTool === 'scissors') {
    var mapped = mapAbcElemToModel(abcElem, partIdx);
    if (mapped && mapped.partIdx >= 0) {
      var part = notationModel.parts[mapped.partIdx];
      var el = part.elements[mapped.elemIdx];
      if ((el.type === 'note' || el.type === 'rest') && !el.grace) {
        pushUndo();
        splitNoteElement(part, mapped.elemIdx);
        syncModelToTextarea();
      }
    }
    return;
  }

  // Check if click was actually on a bar line — handle before abcjs note selection
  if (mouseEvent) {
    var barEl = findBarAncestor(mouseEvent.target);
    if (barEl) {
      if (!currentTool || currentTool === 'beam' || currentTool === 'slur' || currentTool === 'grace' ||
          currentTool === 'sharp' || currentTool === 'flat' || currentTool === 'natural') {
        var barPartIdx = findPartForSvgElement(barEl);
        if (barPartIdx < 0) barPartIdx = partIdx;
        var modelIdx = findBarModelIndex(barPartIdx, barEl);
        if (modelIdx >= 0) {
          var isShift = lastPointerShift || mouseEvent.shiftKey;
          if (isShift && selectedElements.length > 0) {
            var anchor = selectedElements[0];
            if (anchor.partIdx === barPartIdx) {
              var lo = Math.min(anchor.elemIdx, modelIdx);
              var hi = Math.max(anchor.elemIdx, modelIdx);
              selectedElements = [];
              for (var ri = lo; ri <= hi; ri++) {
                selectedElements.push({partIdx: barPartIdx, elemIdx: ri});
              }
            } else {
              selectedElements.push({partIdx: barPartIdx, elemIdx: modelIdx});
            }
          } else {
            selectedElements = [{partIdx: barPartIdx, elemIdx: modelIdx}];
          }
          highlightSelected();
          setTimeout(highlightSelected, 20);
          showPropertyIndicator();
          return;
        }
      }
    }
  }

  // Selection mode: click on a note to select it, shift-click to multi-select
  // Works when no note/rest/bar tool is active
  if (!currentTool || currentTool === 'slur' || currentTool === 'grace' ||
      currentTool === 'sharp' || currentTool === 'flat' || currentTool === 'natural') {
    var mapped = mapAbcElemToModel(abcElem, partIdx);
    if (mapped && mapped.partIdx >= 0) {
      // Use lastPointerShift (from our pointerdown handler) for reliable shift detection
      var isShift = lastPointerShift || (mouseEvent && mouseEvent.shiftKey);
      if (isShift && selectedElements.length > 0) {
        // Range select: select all elements between the first selected and the clicked one
        var anchor = selectedElements[0];
        if (anchor.partIdx === mapped.partIdx) {
          var lo = Math.min(anchor.elemIdx, mapped.elemIdx);
          var hi = Math.max(anchor.elemIdx, mapped.elemIdx);
          selectedElements = [];
          for (var ri = lo; ri <= hi; ri++) {
            selectedElements.push({partIdx: mapped.partIdx, elemIdx: ri});
          }
        } else {
          // Different parts: just add to selection
          selectedElements.push({partIdx: mapped.partIdx, elemIdx: mapped.elemIdx});
        }
      } else if (selectedElements.length === 1 &&
                 selectedElements[0].partIdx === mapped.partIdx &&
                 selectedElements[0].elemIdx === mapped.elemIdx) {
        // Click on already-selected element: deselect it
        selectedElements = [];
        highlightSelected();
        hidePropertyIndicator();
        return;
      } else {
        selectedElements = [{partIdx: mapped.partIdx, elemIdx: mapped.elemIdx}];
      }
      highlightSelected();
      // Re-apply after a short delay in case abcjs modifies elements post-callback
      setTimeout(highlightSelected, 20);
      showPropertyIndicator();
      return;
    }
  }

  // Deselect if clicking empty area
  selectedElements = [];
  highlightSelected();
  hidePropertyIndicator();
}

// --- Map abcjs element to model ---
function mapAbcElemToModel(abcElem, partIdx) {
  if (!abcElem || abcElem.startChar === undefined) return null;
  if (partIdx === undefined) partIdx = 0;
  if (partIdx >= notationModel.parts.length) return null;

  var charOffset = abcElem.startChar;

  // Per-part ABC has header: 'X:1\\nK:key\\nL:unit\\nM:meter\\n' then the notes
  var key = document.getElementById('field-key').value || 'C';
  var meterSel = document.getElementById('field-meter');
  var meter = meterSel ? meterSel.value : '4/4';
  var unitField = document.querySelector('select[name="unit"]');
  var unit = unitField ? unitField.value : '1/8';
  var headerLen = ('X:1\\nK:' + key + '\\nL:' + unit + '\\nM:' + meter + '\\n').length;

  var inPartOffset = charOffset - headerLen;
  if (inPartOffset < 0) inPartOffset = 0;

  var partAbc = modelToAbcPart(notationModel.parts[partIdx]);
  var elemIdx = charOffsetToElemIdx(partAbc, inPartOffset, notationModel.parts[partIdx].elements);
  return { partIdx: partIdx, elemIdx: elemIdx };
}

function modelToAbcPart(part) {
  // Serialize just one part
  var line = '';
  var inSlur = false;
  for (var e = 0; e < part.elements.length; e++) {
    var el = part.elements[e];
    if (el.type === 'note') {
      if (el.slurStart && !inSlur) { line += '('; inSlur = true; }
      if (el.grace) line += '{';
      if (el.accidental) line += el.accidental;
      if (el.octave >= 1) {
        line += el.pitch.toLowerCase();
        for (var o = 1; o < el.octave; o++) line += "'";
      } else if (el.octave <= -1) {
        line += el.pitch.toUpperCase();
        for (var o = 0; o > el.octave; o--) line += ',';
      } else {
        line += el.pitch.toUpperCase();
      }
      if (el.duration && !el.grace) line += el.duration;
      if (el.grace) line += '}';
      if (el.tied) line += '-';
      if (el.slurEnd && inSlur) { line += ')'; inSlur = false; }
    } else if (el.type === 'rest') {
      line += 'z';
      if (el.duration) line += el.duration;
    } else if (el.type === 'bar') {
      line += el.subtype || '|';
    }
    if (el.spaceAfter) line += ' ';
  }
  if (inSlur) line += ')';
  return line;
}

function charOffsetToElemIdx(abcText, offset, elements) {
  // Walk through the part's ABC text char by char, matching to element boundaries.
  // Use core length (without spaceAfter) for matching so trailing spaces don't
  // cause the next element's startChar to fall inside this element's range.
  // If offset lands on a trailing space, attribute it to the next element.
  var pos = 0;
  for (var e = 0; e < elements.length; e++) {
    var el = elements[e];
    var coreLen = elementAbcCoreLength(el);
    var fullLen = elementAbcLength(el);
    if (offset >= pos && offset < pos + coreLen) return e;
    // Offset lands on trailing space — belongs to next element
    if (el.spaceAfter && offset >= pos + coreLen && offset < pos + fullLen) {
      return (e + 1 < elements.length) ? e + 1 : e;
    }
    pos += fullLen;
  }
  return Math.max(0, elements.length - 1);
}

function elementAbcCoreLength(el) {
  // Length of the element's ABC text WITHOUT trailing space
  if (el.type === 'bar') return (el.subtype || '|').length;
  if (el.type === 'rest') return 1 + (el.duration || '').length;
  if (el.type === 'note') {
    var len = 0;
    if (el.slurStart) len += 1;
    if (el.grace) len += 1; // {
    if (el.accidental) len += el.accidental.length;
    len += 1; // pitch letter
    if (el.octave >= 1) {
      len += el.octave - 1; // apostrophes
    } else if (el.octave <= -1) {
      len += Math.abs(el.octave); // commas
    }
    if (el.duration && !el.grace) len += el.duration.length;
    if (el.grace) len += 1; // }
    if (el.tied) len += 1;
    if (el.slurEnd) len += 1;
    return len;
  }
  return 1;
}

function elementAbcLength(el) {
  return elementAbcCoreLength(el) + (el.spaceAfter ? 1 : 0);
}

// --- Selection Highlighting ---
// Apply red highlight to an SVG element and all its children
// If colorOnly is true, change color but not stroke-width (for beams/ties)
function veApplyHighlight(el, colorOnly) {
  var cls = (el.getAttribute && el.getAttribute('class')) || '';
  // Skip hit-area rects — they must stay invisible
  if (cls.indexOf('ve-bar-hitarea') >= 0 || cls.indexOf('ve-slur-hitarea') >= 0) return;
  el.setAttribute('data-ve-hl', '1');
  var isTieOrSlur = cls.indexOf('abcjs-tie') >= 0 || cls.indexOf('abcjs-slur') >= 0;
  if (isTieOrSlur) {
    el.style.setProperty('fill', 'none', 'important');
    el.style.setProperty('stroke', '#cc3333', 'important');
  } else {
    el.style.setProperty('fill', '#cc3333', 'important');
    el.style.setProperty('stroke', '#cc3333', 'important');
    if (!colorOnly) el.style.setProperty('stroke-width', '1.5', 'important');
  }
  var children = el.children || el.childNodes;
  if (children) {
    for (var c = 0; c < children.length; c++) {
      if (children[c].nodeType === 1) veApplyHighlight(children[c], colorOnly);
    }
  }
}
// Remove highlight from an SVG element and all its children
function veRemoveHighlight(el) {
  el.removeAttribute('data-ve-hl');
  el.style.removeProperty('fill');
  el.style.removeProperty('stroke');
  el.style.removeProperty('stroke-width');
  el.classList.remove('ve-note-highlight');
  var children = el.children || el.childNodes;
  if (children) {
    for (var c = 0; c < children.length; c++) {
      if (children[c].nodeType === 1) veRemoveHighlight(children[c]);
    }
  }
}

function highlightSelected() {
  // Remove old highlights
  var old = document.querySelectorAll('[data-ve-hl]');
  for (var i = 0; i < old.length; i++) {
    var el = old[i];
    el.removeAttribute('data-ve-hl');
    el.style.removeProperty('fill');
    el.style.removeProperty('stroke');
    el.style.removeProperty('stroke-width');
    el.classList.remove('ve-note-highlight');
  }

  // Build a set of selected {partIdx, elemIdx} for fast lookup
  var selSet = {};
  for (var s = 0; s < selectedElements.length; s++) {
    var sel = selectedElements[s];
    selSet[sel.partIdx + ',' + sel.elemIdx] = true;
  }

  // Highlight selected notes
  for (var s = 0; s < selectedElements.length; s++) {
    var sel = selectedElements[s];
    if (sel.partIdx >= partRenderings.length) continue;
    var pr = partRenderings[sel.partIdx];
    if (!pr || !pr.elemSvgMap) continue;
    var svgElems = pr.elemSvgMap[sel.elemIdx];
    if (svgElems) {
      for (var k = 0; k < svgElems.length; k++) {
        veApplyHighlight(svgElems[k]);
      }
    }
  }

  // Highlight beams where ALL connected notes are selected (color only, no width change)
  for (var p = 0; p < partRenderings.length; p++) {
    var pr = partRenderings[p];
    if (!pr || !pr.beamGroups || pr.beamGroups.length === 0) continue;
    // Collect X ranges of beams whose notes are all selected
    var beamXRanges = [];
    for (var bi = 0; bi < pr.beamGroups.length; bi++) {
      var bg = pr.beamGroups[bi];
      var allSelected = true;
      for (var ni = 0; ni < bg.elemIndices.length; ni++) {
        if (!selSet[p + ',' + bg.elemIndices[ni]]) {
          allSelected = false;
          break;
        }
      }
      if (allSelected && bg.startX !== undefined) {
        beamXRanges.push({startX: bg.startX, endX: bg.endX});
      }
    }
    if (beamXRanges.length === 0) continue;
    // Find SVG beam paths and match by X range
    var svg = pr.renderTarget.querySelector('svg');
    if (!svg) continue;
    var beamPaths = svg.querySelectorAll('.abcjs-beam-elem');
    for (var bp = 0; bp < beamPaths.length; bp++) {
      try {
        var bbox = beamPaths[bp].getBBox();
        var bx1 = bbox.x;
        var bx2 = bbox.x + bbox.width;
        for (var ri = 0; ri < beamXRanges.length; ri++) {
          var r = beamXRanges[ri];
          // Match if beam path overlaps the beam group's X range
          if (bx1 >= r.startX - 5 && bx2 <= r.endX + 5) {
            veApplyHighlight(beamPaths[bp], true);
            break;
          }
        }
      } catch(ex) {}
    }
  }
}

// --- Property Panel ---
// --- Property Indicator and Panel ---
// Small indicator button appears near selection; clicking it opens the property panel.

function showPropertyIndicator() {
  var indicator = document.getElementById('ve-prop-indicator');
  if (!indicator) return;
  if (selectedElements.length === 0) { hidePropertyIndicator(); return; }
  // Find SVG position of the first selected element
  var sel = selectedElements[0];
  var pr = null;
  for (var pi = 0; pi < partRenderings.length; pi++) {
    if (partRenderings[pi].partIdx === sel.partIdx) { pr = partRenderings[pi]; break; }
  }
  if (!pr || !pr.elemSvgMap) { hidePropertyIndicator(); return; }
  var svgElems = pr.elemSvgMap[sel.elemIdx];
  if (!svgElems || svgElems.length === 0) { hidePropertyIndicator(); return; }
  var container = document.getElementById('ve-preview-container');
  if (!container) return;
  var containerRect = container.getBoundingClientRect();
  var elemRect = svgElems[0].getBoundingClientRect();
  // Position indicator above the element
  var left = elemRect.left + elemRect.width / 2 - containerRect.left - 10;
  var top = elemRect.top - containerRect.top - 24;
  if (top < 0) top = elemRect.bottom - containerRect.top + 2;
  indicator.style.left = left + 'px';
  indicator.style.top = top + 'px';
  indicator.style.display = 'block';
}

function hidePropertyIndicator() {
  var indicator = document.getElementById('ve-prop-indicator');
  if (indicator) indicator.style.display = 'none';
  hidePropertyPanel();
}

function setupPropertyIndicator() {
  var indicator = document.getElementById('ve-prop-indicator');
  if (!indicator) return;
  indicator.addEventListener('pointerdown', function(e) {
    e.stopPropagation();
    e.preventDefault();
    var panel = document.getElementById('ve-property-panel');
    if (panel && panel.style.display !== 'none') {
      hidePropertyPanel();
    } else {
      showPropertyPanel();
    }
  });
  indicator.addEventListener('click', function(e) {
    e.stopPropagation();
    e.preventDefault();
  });
  // Prevent clicks on the property panel from propagating to deselect handlers
  var panel = document.getElementById('ve-property-panel');
  if (panel) {
    panel.addEventListener('pointerdown', function(e) { e.stopPropagation(); });
    panel.addEventListener('click', function(e) { e.stopPropagation(); });
  }
  // Close property panel when clicking outside it
  document.addEventListener('pointerdown', function(e) {
    if (!panel || panel.style.display === 'none') return;
    if (panel.contains(e.target) || indicator.contains(e.target)) return;
    hidePropertyPanel();
  });
}

function showPropertyPanel() {
  var panel = document.getElementById('ve-property-panel');
  if (!panel) return;
  if (selectedElements.length === 0) return;
  var sel = selectedElements[0];
  if (sel.partIdx >= notationModel.parts.length) return;
  if (sel.elemIdx >= notationModel.parts[sel.partIdx].elements.length) return;
  var el = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
  var noteCount = 0;
  for (var si = 0; si < selectedElements.length; si++) {
    var se = selectedElements[si];
    var se_el = notationModel.parts[se.partIdx].elements[se.elemIdx];
    if (se_el.type === 'note' && !se_el.grace) noteCount++;
  }
  var html = '<div class="ve-prop-header"><button type="button" class="ve-prop-close" onclick="hidePropertyPanel()">&times;</button></div>';
  if (el.type === 'note' || el.type === 'rest') {
    if (el.type === 'note' && selectedElements.length === 1) {
      html += '<div class="ve-prop-row"><span class="ve-prop-label">Pitch:</span> ' +
              el.pitch + (el.octave >= 1 ? el.octave : '') + '</div>';
    }
    html += '<div class="ve-prop-row"><span class="ve-prop-label">Dur:</span>';
    var durs = [
      {label:'W', dur:getDurForTool('whole'), title:'Whole'},
      {label:'H', dur:getDurForTool('half'), title:'Half'},
      {label:'Q', dur:getDurForTool('quarter'), title:'Quarter'},
      {label:'8', dur:getDurForTool('eighth'), title:'Eighth'},
      {label:'16', dur:getDurForTool('sixteenth'), title:'16th'}
    ];
    for (var d = 0; d < durs.length; d++) {
      var active = (el.duration === durs[d].dur) ? ' ve-prop-active' : '';
      html += '<button type="button" class="ve-prop-btn' + active + '" title="' + durs[d].title +
              '" onclick="vePropSetDuration(\\'' + durs[d].dur + '\\')">' +
              durs[d].label + '</button>';
    }
    html += '</div>';
    if (el.type === 'note') {
      html += '<div class="ve-prop-row"><span class="ve-prop-label">Acc:</span>';
      var accs = [{label:'\\u266f', val:'^'}, {label:'\\u266d', val:'_', big:true}, {label:'\\u266e', val:'=', big:true}];
      for (var a = 0; a < accs.length; a++) {
        var active = (el.accidental === accs[a].val) ? ' ve-prop-active' : '';
        var accCls = accs[a].big ? ' ve-acc-icon' : '';
        html += '<button type="button" class="ve-prop-btn' + active + accCls + '" onclick="vePropToggleAccidental(\\'' +
                accs[a].val + '\\')">' + accs[a].label + '</button>';
      }
      html += '</div>';
    }
  } else if (el.type === 'bar') {
    html += '<div class="ve-prop-row"><span class="ve-prop-label">Bar</span></div>';
    var bars = [{label:'|', val:'|'}, {label:'|:', val:'|:'}, {label:':|', val:':|'}];
    html += '<div class="ve-prop-row">';
    for (var b = 0; b < bars.length; b++) {
      var active = (el.subtype === bars[b].val) ? ' ve-prop-active' : '';
      html += '<button type="button" class="ve-prop-btn' + active + '" onclick="vePropSetBarType(\\'' +
              bars[b].val + '\\')">' + bars[b].label + '</button>';
    }
    html += '</div>';
  }
  // Delete button
  html += '<div class="ve-prop-row" style="margin-top:4px;border-top:1px solid #ddd;padding-top:4px">';
  html += '<button type="button" class="ve-prop-btn" style="background:#cc3333;color:white;border-color:#993333" ' +
          'onclick="veDeleteSelected()">Delete</button>';
  html += '</div>';

  var content = document.getElementById('ve-prop-content');
  if (content) content.innerHTML = html;
  // Position near the indicator
  var indicator = document.getElementById('ve-prop-indicator');
  var container = document.getElementById('ve-preview-container');
  if (indicator && container) {
    var indLeft = parseInt(indicator.style.left) || 0;
    var indTop = parseInt(indicator.style.top) || 0;
    panel.style.left = indLeft + 'px';
    panel.style.top = (indTop + indicator.offsetHeight + 4) + 'px';
    panel.style.right = 'auto';
    panel.style.display = 'block';
    // Adjust if panel overflows container on the right
    var panelRect = panel.getBoundingClientRect();
    var containerRect = container.getBoundingClientRect();
    if (panelRect.right > containerRect.right - 4) {
      var adjustedLeft = containerRect.width - panel.offsetWidth - 4;
      if (adjustedLeft < 0) adjustedLeft = 0;
      panel.style.left = adjustedLeft + 'px';
    }
  } else {
    panel.style.display = 'block';
  }
}

function hidePropertyPanel() {
  var panel = document.getElementById('ve-property-panel');
  if (panel) panel.style.display = 'none';
}

function getDurForTool(toolName) {
  return toolToDuration(toolName);
}

// Property panel actions — all operate on selectedElements
function vePropSetDuration(dur) {
  pushUndo();
  for (var si = 0; si < selectedElements.length; si++) {
    var sel = selectedElements[si];
    var el = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
    if (el.type === 'note' || el.type === 'rest') el.duration = dur;
  }
  syncModelToTextarea();
  hidePropertyPanel();
}

function vePropToggleAccidental(acc) {
  pushUndo();
  for (var si = 0; si < selectedElements.length; si++) {
    var sel = selectedElements[si];
    var el = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
    if (el.type === 'note') el.accidental = (el.accidental === acc) ? null : acc;
  }
  syncModelToTextarea();
  hidePropertyPanel();
}

function vePropToggleTie() {
  pushUndo();
  for (var si = 0; si < selectedElements.length; si++) {
    var sel = selectedElements[si];
    var el = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
    if (el.type === 'note') el.tied = !el.tied;
  }
  syncModelToTextarea();
  hidePropertyPanel();
}

function vePropToggleGrace() {
  if (selectedElements.length === 0) return;
  pushUndo();
  if (selectedElements.length === 1) {
    // Single note: simple toggle
    var sel = selectedElements[0];
    var el = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
    if (el.type === 'note') el.grace = !el.grace;
  } else if (selectedElements.length === 2) {
    // Two notes: make first a grace note and slur to second
    var sortedSel = selectedElements.slice().sort(function(a, b) { return a.elemIdx - b.elemIdx; });
    var firstEl = notationModel.parts[sortedSel[0].partIdx].elements[sortedSel[0].elemIdx];
    var secondEl = notationModel.parts[sortedSel[1].partIdx].elements[sortedSel[1].elemIdx];
    if (firstEl.type === 'note' && secondEl.type === 'note') {
      if (firstEl.grace) {
        // Undo: remove grace and slur
        firstEl.grace = false;
        firstEl.slurStart = false;
        secondEl.slurEnd = false;
      } else {
        // Make first a grace note with slur to second
        firstEl.grace = true;
        firstEl.slurStart = true;
        secondEl.slurEnd = true;
      }
    }
  }
  syncModelToTextarea();
  hidePropertyPanel();
}

function vePropSetBarType(barType) {
  pushUndo();
  for (var si = 0; si < selectedElements.length; si++) {
    var sel = selectedElements[si];
    var el = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
    if (el.type === 'bar') el.subtype = barType;
  }
  syncModelToTextarea();
  hidePropertyPanel();
}

// --- Delete ---
function veDeleteSelected() {
  if (selectedElements.length === 0) return;
  pushUndo();
  // Sort by descending elemIdx to avoid index shifting
  var sorted = selectedElements.slice().sort(function(a, b) {
    if (a.partIdx !== b.partIdx) return b.partIdx - a.partIdx;
    return b.elemIdx - a.elemIdx;
  });
  for (var i = 0; i < sorted.length; i++) {
    var s = sorted[i];
    if (s.partIdx < notationModel.parts.length) {
      notationModel.parts[s.partIdx].elements.splice(s.elemIdx, 1);
    }
  }
  selectedElements = [];
  hidePropertyIndicator();
  syncModelToTextarea();
}

// --- Parts Bar ---
// Part controls are now inline on each part label (× button) and below parts (+ Add Part).
function updatePartHeaders() {
  // No-op: inline part controls are rendered in veDoRenderAbc()
}

function removePartHeaders() {
  // No-op: inline part controls are rendered in veDoRenderAbc()
}

function addNotePart(beforeIndex) {
  pushUndo();
  var partLabels = 'ABCDEFGHIJ';
  var newPart = { label: '', elements: [{type: 'bar', subtype: '|'}] };
  if (beforeIndex >= notationModel.parts.length) {
    notationModel.parts.push(newPart);
  } else {
    notationModel.parts.splice(beforeIndex, 0, newPart);
  }
  // Re-label all parts
  for (var i = 0; i < notationModel.parts.length; i++) {
    notationModel.parts[i].label = i < partLabels.length ? partLabels[i] : '' + i;
  }
  syncModelToTextarea();
}

function removeNotePart(index) {
  if (notationModel.parts.length <= 1) {
    alert('Must have at least one part.');
    return;
  }
  var part = notationModel.parts[index];
  if (part.elements.length > 0 && !confirm('Part ' + part.label + ' has data. Remove it?')) return;
  pushUndo();
  notationModel.parts.splice(index, 1);
  var partLabels = 'ABCDEFGHIJ';
  for (var i = 0; i < notationModel.parts.length; i++) {
    notationModel.parts[i].label = i < partLabels.length ? partLabels[i] : '' + i;
  }
  selectedElements = [];
  hidePropertyIndicator();
  syncModelToTextarea();
}

// --- Part Drag Reorder ---
var partDragState = {dragging: false, fromIdx: -1, startY: 0, dropIndicator: null};

function reorderPart(fromIdx, toIdx) {
  if (fromIdx === toIdx || fromIdx < 0 || toIdx < 0) return;
  if (fromIdx >= notationModel.parts.length) return;
  pushUndo();
  var part = notationModel.parts.splice(fromIdx, 1)[0];
  notationModel.parts.splice(toIdx, 0, part);
  // Re-label all parts
  var partLabels = 'ABCDEFGHIJ';
  for (var i = 0; i < notationModel.parts.length; i++) {
    notationModel.parts[i].label = i < partLabels.length ? partLabels[i] : '' + i;
  }
  selectedElements = [];
  hidePropertyIndicator();
  syncModelToTextarea();
}

function getPartContainerMidpoints() {
  // Get vertical midpoints of each part container for drop targeting
  var midpoints = [];
  for (var i = 0; i < partRenderings.length; i++) {
    var rect = partRenderings[i].container.getBoundingClientRect();
    midpoints.push({idx: i, top: rect.top, bottom: rect.bottom, mid: (rect.top + rect.bottom) / 2});
  }
  return midpoints;
}

function getPartDropIndex(clientY) {
  var mids = getPartContainerMidpoints();
  if (mids.length === 0) return 0;
  // Before first part
  if (clientY < mids[0].mid) return 0;
  // After last part
  if (clientY >= mids[mids.length - 1].mid) return mids.length - 1;
  // Between parts
  for (var i = 0; i < mids.length; i++) {
    if (clientY < mids[i].mid) return i;
  }
  return mids.length - 1;
}

function showPartDropIndicator(clientY) {
  removePartDropIndicator();
  var dropIdx = getPartDropIndex(clientY);
  var indicator = document.createElement('div');
  indicator.className = 've-part-drop-indicator';
  var previewEl = document.getElementById('abcjs-preview');
  if (!previewEl) return;
  // Insert before the target container
  if (dropIdx < partRenderings.length) {
    previewEl.insertBefore(indicator, partRenderings[dropIdx].container);
  } else {
    // After last container, before the add button
    var addBtn = previewEl.querySelector('.ve-add-part-btn');
    if (addBtn) {
      previewEl.insertBefore(indicator, addBtn);
    } else {
      previewEl.appendChild(indicator);
    }
  }
  partDragState.dropIndicator = indicator;
}

function removePartDropIndicator() {
  if (partDragState.dropIndicator && partDragState.dropIndicator.parentNode) {
    partDragState.dropIndicator.parentNode.removeChild(partDragState.dropIndicator);
  }
  partDragState.dropIndicator = null;
}

function setupPartLabelDrag(partLabel, partIdx) {
  if (notationModel.parts.length <= 1) return;

  partLabel.addEventListener('pointerdown', function(e) {
    // Skip if clicking × button
    if (e.target.classList.contains('ve-part-label-remove')) return;
    if (notationModel.parts.length <= 1) return;
    partDragState.dragging = false;
    partDragState.fromIdx = partIdx;
    partDragState.startY = e.clientY;
    partLabel.setPointerCapture(e.pointerId);
    e.preventDefault();
  });

  partLabel.addEventListener('pointermove', function(e) {
    if (partDragState.fromIdx < 0) return;
    var dy = Math.abs(e.clientY - partDragState.startY);
    if (!partDragState.dragging && dy > 5) {
      partDragState.dragging = true;
      // Dim source part
      if (partDragState.fromIdx < partRenderings.length) {
        partRenderings[partDragState.fromIdx].container.style.opacity = '0.5';
      }
    }
    if (partDragState.dragging) {
      showPartDropIndicator(e.clientY);
    }
  });

  partLabel.addEventListener('pointerup', function(e) {
    if (partDragState.dragging) {
      var toIdx = getPartDropIndex(e.clientY);
      // Adjust: if dropping after the source, account for removal
      if (toIdx > partDragState.fromIdx) {
        // toIdx stays as-is since splice-then-insert handles it
      }
      removePartDropIndicator();
      // Restore opacity
      if (partDragState.fromIdx < partRenderings.length) {
        partRenderings[partDragState.fromIdx].container.style.opacity = '';
      }
      if (toIdx !== partDragState.fromIdx) {
        reorderPart(partDragState.fromIdx, toIdx);
      }
    }
    partDragState.dragging = false;
    partDragState.fromIdx = -1;
  });

  partLabel.addEventListener('pointercancel', function(e) {
    removePartDropIndicator();
    if (partDragState.fromIdx >= 0 && partDragState.fromIdx < partRenderings.length) {
      partRenderings[partDragState.fromIdx].container.style.opacity = '';
    }
    partDragState.dragging = false;
    partDragState.fromIdx = -1;
  });
}

// --- Toolbar Tool Selection ---
function setupToolbar() {
  var btns = document.querySelectorAll('.ve-tool-btn');
  for (var i = 0; i < btns.length; i++) {
    (function(btn) {
      btn.addEventListener('pointerdown', function(e) {
        var tool = btn.getAttribute('data-tool');
        if (!tool) return;

        // Select tool: activate selection mode
        if (tool === 'select') {
          activateSelectTool();
          e.preventDefault();
          return;
        }

        // Scissors tool: modal tool for splitting notes / breaking beams
        if (tool === 'scissors') {
          if (currentTool === 'scissors') {
            // Toggle off — return to select
            activateSelectTool();
          } else {
            // Activate scissors mode (requires clicking on elements to act)
            clearToolSelection();
            currentTool = 'scissors';
            btn.classList.add('ve-tool-active');
            selectedElements = [];
            highlightSelected();
            hidePropertyIndicator();
            var editorEl = document.querySelector('.edit-form');
            if (editorEl) editorEl.classList.add('ve-scissors-active');
          }
          e.preventDefault();
          return;
        }

        // Special tools act on selection immediately
        if (tool === 'beam' || tool === 'slur' || tool === 'sharp' || tool === 'flat' || tool === 'natural' || tool === 'grace') {
          // Immediate action for beam on selected notes (toggle)
          // If any adjacent selected notes have spaceAfter (broken beam), remove
          // spaces to join them. Otherwise add spaces to break beams.
          if (tool === 'beam' && selectedElements.length >= 2) {
            pushUndo();
            var sortedSel = selectedElements.slice().sort(function(a, b) { return a.elemIdx - b.elemIdx; });
            // Check if any selected note (except last) has spaceAfter
            var anyBroken = false;
            for (var si = 0; si < sortedSel.length - 1; si++) {
              var sel = sortedSel[si];
              var elem = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
              if (elem.spaceAfter) { anyBroken = true; break; }
            }
            // Toggle: if any broken, join all; if all joined, break all
            for (var si = 0; si < sortedSel.length - 1; si++) {
              var sel = sortedSel[si];
              var elem = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
              if (elem.type === 'note' || elem.type === 'rest') {
                elem.spaceAfter = !anyBroken;
              }
            }
            syncModelToTextarea();
            selectedElements = [];
            highlightSelected();
            hidePropertyIndicator();
          }
          // Immediate action for slur on selected range (toggle)
          if (tool === 'slur' && selectedElements.length >= 2) {
            pushUndo();
            var sortedSel = selectedElements.slice().sort(function(a, b) { return a.elemIdx - b.elemIdx; });
            var first = sortedSel[0];
            var last = sortedSel[sortedSel.length - 1];
            var fe = notationModel.parts[first.partIdx].elements[first.elemIdx];
            var le = notationModel.parts[last.partIdx].elements[last.elemIdx];
            // Toggle: if slur already exists on this range, remove it
            var hasSlur = (fe.type === 'note' && fe.slurStart && le.type === 'note' && le.slurEnd);
            // Clear all slur flags on selected notes
            for (var si = 0; si < sortedSel.length; si++) {
              var se = sortedSel[si];
              var el = notationModel.parts[se.partIdx].elements[se.elemIdx];
              if (el.type === 'note') { el.slurStart = false; el.slurEnd = false; }
            }
            // If slur wasn't present, add it
            if (!hasSlur) {
              if (fe.type === 'note') fe.slurStart = true;
              if (le.type === 'note') le.slurEnd = true;
            }
            syncModelToTextarea();
            selectedElements = [];
            highlightSelected();
            hidePropertyIndicator();
          }
          // Immediate action for accidentals on selected notes
          if ((tool === 'sharp' || tool === 'flat' || tool === 'natural') && selectedElements.length > 0) {
            var acc = tool === 'sharp' ? '^' : tool === 'flat' ? '_' : '=';
            pushUndo();
            for (var si = 0; si < selectedElements.length; si++) {
              var sel = selectedElements[si];
              var elem = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
              if (elem.type === 'note') {
                elem.accidental = (elem.accidental === acc) ? null : acc;
              }
            }
            syncModelToTextarea();
          }
          // Immediate action for grace note toggle on selected notes
          if (tool === 'grace' && selectedElements.length > 0) {
            pushUndo();
            for (var si = 0; si < selectedElements.length; si++) {
              var sel = selectedElements[si];
              var elem = notationModel.parts[sel.partIdx].elements[sel.elemIdx];
              if (elem.type === 'note') {
                elem.grace = !elem.grace;
              }
            }
            syncModelToTextarea();
          }
          e.preventDefault();
          return;
        }

        // Note/rest/bar tools: toggle selection or start drag
        if (currentTool === tool) {
          activateSelectTool();
          e.preventDefault();
          return;
        }
        clearToolSelection();
        currentTool = tool;
        btn.classList.add('ve-tool-active');
        selectedElements = [];
        highlightSelected();
        hidePropertyIndicator();

        // Start drag from palette
        startPaletteDrag(e, btn, tool);
      });
    })(btns[i]);
  }
  // Select tool active by default on page load
  activateSelectTool();
}

// --- Palette Drag ---
function startPaletteDrag(e, btn, tool) {
  isDragging = true;
  var startX = e.clientX, startY = e.clientY;
  var dragStarted = false;  // True once pointer moves enough to be a real drag

  var pitchLabel = document.getElementById('ve-pitch-label');

  btn.setPointerCapture(e.pointerId);

  function onMove(ev) {
    if (!isDragging) return;
    // Require minimum 5px movement before starting visual drag
    if (!dragStarted) {
      var dx = ev.clientX - startX, dy = ev.clientY - startY;
      if (dx * dx + dy * dy < 25) return;
      dragStarted = true;
      // Create ghost on first real movement
      dragGhost = document.createElement('div');
      dragGhost.className = 've-drag-ghost';
      dragGhost.innerHTML = btn.innerHTML || tool;
      document.body.appendChild(dragGhost);
    }
    dragGhost.style.left = (ev.clientX + 10) + 'px';
    dragGhost.style.top = (ev.clientY - 15) + 'px';

    // Check if over staff
    var overStaff = getStaffAtPoint(ev.clientX, ev.clientY);
    if (overStaff) {
      // Show pitch label
      if (tool !== 'bar' && tool !== 'bar-open' && tool !== 'bar-close' && !tool.match(/^rest-/)) {
        var snappedPos = yToStaffPosition(overStaff.localY, overStaff.geo);
        var pp = staffPositionToPitch(snappedPos);
        if (pitchLabel) {
          pitchLabel.textContent = pitchToDisplayName(pp.pitch, pp.octave);
          pitchLabel.style.display = 'block';
          pitchLabel.style.left = (ev.clientX + 20) + 'px';
          pitchLabel.style.top = (ev.clientY - 25) + 'px';
        }
      }
      // Show insertion marker
      showInsertionMarker(overStaff, ev.clientX);
    } else {
      if (pitchLabel) pitchLabel.style.display = 'none';
      removeInsertionMarker();
    }
  }

  function onUp(ev) {
    btn.removeEventListener('pointermove', onMove);
    btn.removeEventListener('pointerup', onUp);
    btn.removeEventListener('pointercancel', onUp);
    try { btn.releasePointerCapture(ev.pointerId); } catch(ex) {}
    if (dragGhost) { document.body.removeChild(dragGhost); dragGhost = null; }
    if (pitchLabel) pitchLabel.style.display = 'none';
    removeInsertionMarker();

    // Only place element if drag actually started (moved enough)
    if (dragStarted) {
      var overStaff = getStaffAtPoint(ev.clientX, ev.clientY);
      if (overStaff) {
        placeElementOnStaff(tool, overStaff, ev.clientX);
      }
    }
    // Keep isDragging true briefly to suppress abcjs clickListener
    // and setupStaffClick handler from also firing
    setTimeout(function() { isDragging = false; }, 100);
  }

  btn.addEventListener('pointermove', onMove);
  btn.addEventListener('pointerup', onUp);
  btn.addEventListener('pointercancel', onUp);
}

// --- Bar Line Selection Helpers ---
function findBarAncestor(el) {
  // Walk up from click target to find an .abcjs-bar SVG group
  while (el && el !== document) {
    if (el.classList && el.classList.contains('abcjs-bar')) return el;
    el = el.parentNode;
  }
  return null;
}

function addBarHitAreas(svg) {
  // Add invisible wider hit-area rects to thin bar lines so they're easier to click
  var bars = svg.querySelectorAll('.abcjs-bar');
  for (var i = 0; i < bars.length; i++) {
    var bar = bars[i];
    // Skip if we already added a hit area
    if (bar.querySelector('.ve-bar-hitarea')) continue;
    try {
      var bbox = bar.getBBox();
      var hitRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      hitRect.setAttribute('class', 've-bar-hitarea');
      hitRect.setAttribute('x', bbox.x + bbox.width / 2 - 6);
      hitRect.setAttribute('y', bbox.y);
      hitRect.setAttribute('width', 12);
      hitRect.setAttribute('height', bbox.height);
      hitRect.setAttribute('fill', 'transparent');
      hitRect.setAttribute('pointer-events', 'all');
      bar.insertBefore(hitRect, bar.firstChild);
    } catch(ex) {}
  }
}

function addBeamHitAreas(svg, partIdx) {
  // Add invisible wider hit-area rects over beam bars so they're easier to click.
  // Beam bars are thin filled paths with class abcjs-beam-elem.
  // Each hit area gets its own click handler since abcjs stops event
  // propagation on SVG clicks, preventing delegation to parent elements.
  var beams = svg.querySelectorAll('path[class*="abcjs-beam-elem"]');
  for (var i = 0; i < beams.length; i++) {
    var beam = beams[i];
    try {
      var bbox = beam.getBBox();
      // Only add hit areas for beam bars (wide and thin), not stems
      if (bbox.width < 5 || bbox.height > bbox.width) continue;
      var hitRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      hitRect.setAttribute('class', 've-beam-hitarea');
      hitRect.setAttribute('x', bbox.x);
      hitRect.setAttribute('y', bbox.y - 4);
      hitRect.setAttribute('width', bbox.width);
      hitRect.setAttribute('height', bbox.height + 8);
      hitRect.setAttribute('fill', 'transparent');
      hitRect.setAttribute('pointer-events', 'all');
      hitRect.style.cursor = 'pointer';
      svg.appendChild(hitRect);
      // Use pointerdown — abcjs intercepts click events in the capture phase,
      // and the rubber-band handler captures the pointer on pointerdown
      // (redirecting pointerup/click away). stopPropagation prevents both.
      hitRect.addEventListener('pointerdown', function(e) {
        if (veMode !== 'visual') return;
        // Scissors tool: break/join beam at click point
        if (currentTool === 'scissors') {
          e.stopPropagation();
          e.preventDefault();
          var cutResult = findBeamCutPoint(e.clientX, e.clientY, partIdx);
          if (cutResult) {
            pushUndo();
            var cutEl = notationModel.parts[cutResult.partIdx].elements[cutResult.elemIdx];
            // Toggle: break if not broken, join if already broken
            cutEl.spaceAfter = !cutEl.spaceAfter;
            syncModelToTextarea();
          }
          isDragging = true;
          setTimeout(function() { isDragging = false; }, 300);
          return;
        }
        if (currentTool) return;
        e.stopPropagation();
        e.preventDefault();
        var beamSel = findBeamGroupAtPoint(e.clientX, e.clientY);
        if (!beamSel || beamSel.length === 0) return;
        selectedElements = beamSel;
        highlightSelected();
        setTimeout(highlightSelected, 20);
        showPropertyIndicator();
        // Suppress deselect handlers that fire on subsequent click/pointerup
        isDragging = true;
        setTimeout(function() { isDragging = false; }, 300);
      });
      // Stop click and pointerup from propagating — prevents abcjs
      // capture-phase click handler and deselect handlers from firing
      hitRect.addEventListener('click', function(e) {
        e.stopImmediatePropagation();
        e.preventDefault();
      }, true);  // capture phase
      hitRect.addEventListener('click', function(e) {
        e.stopImmediatePropagation();
        e.preventDefault();
      });  // bubble phase
      hitRect.addEventListener('pointerup', function(e) {
        e.stopImmediatePropagation();
      }, true);
      hitRect.addEventListener('pointerup', function(e) {
        e.stopImmediatePropagation();
      });
    } catch(ex) {}
  }
}

function addSlurHitAreas(svg, partIdx) {
  // Add invisible wider hit areas over slur arcs so they can be clicked
  // with the scissors tool to split the slur at the click point.
  var slurs = svg.querySelectorAll('path[class*="abcjs-slur"]');
  for (var i = 0; i < slurs.length; i++) {
    var slur = slurs[i];
    try {
      var bbox = slur.getBBox();
      // Skip very small slur arcs (grace-note-to-note connections)
      if (bbox.width < 12) continue;
      var hitRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      hitRect.setAttribute('class', 've-slur-hitarea');
      hitRect.setAttribute('x', bbox.x);
      hitRect.setAttribute('y', bbox.y - 3);
      hitRect.setAttribute('width', bbox.width);
      hitRect.setAttribute('height', bbox.height + 6);
      hitRect.setAttribute('fill', 'transparent');
      hitRect.setAttribute('stroke', 'none');
      hitRect.setAttribute('pointer-events', 'all');
      svg.appendChild(hitRect);
      hitRect.addEventListener('pointerdown', function(e) {
        if (veMode !== 'visual') return;
        if (currentTool !== 'scissors') return;
        e.stopPropagation();
        e.preventDefault();
        // Find which part rendering this belongs to
        var pr = null;
        for (var pi = 0; pi < partRenderings.length; pi++) {
          if (partRenderings[pi].partIdx === partIdx) { pr = partRenderings[pi]; break; }
        }
        if (!pr) return;
        var svgEl = pr.renderTarget ? pr.renderTarget.querySelector('svg') : null;
        if (!svgEl) return;
        var clickSvgX = clientToSvgCoords(svgEl, e.clientX, e.clientY).x;
        var part = notationModel.parts[partIdx];
        if (!part) return;
        var positions = pr.elementPositions || [];
        // Find the slur (slurStart..slurEnd range) that this click falls within.
        // Use the hit area bounding box to narrow down the slur, then find the
        // note boundary closest to the click X for the cut point.
        var hitBbox = this.getBBox();
        var slurInfo = findSlurSpanningX(part, positions, hitBbox.x, hitBbox.x + hitBbox.width);
        if (!slurInfo) return;
        // Find cut point: boundary between adjacent notes closest to click X
        var cutIdx = findSlurCutIndex(part, positions, slurInfo, clickSvgX);
        if (cutIdx < 0) return;
        pushUndo();
        // Set slurEnd on cutIdx note, slurStart on cutIdx+1 note
        // (cutting the slur into two slurs)
        var cutEl = part.elements[cutIdx];
        // Find next note after cutIdx that's in the slur range
        var nextNoteIdx = -1;
        for (var ni = cutIdx + 1; ni <= slurInfo.endIdx; ni++) {
          if (part.elements[ni].type === 'note' && !part.elements[ni].grace) {
            nextNoteIdx = ni; break;
          }
        }
        if (nextNoteIdx < 0) return;
        var nextEl = part.elements[nextNoteIdx];
        // Check if we're toggling: if this boundary already has slurEnd+slurStart,
        // join the slurs instead of splitting
        if (cutEl.slurEnd && nextEl.slurStart) {
          // Join: remove the intermediate slurEnd/slurStart
          cutEl.slurEnd = false;
          nextEl.slurStart = false;
        } else {
          // Split: count non-grace notes on each side to avoid degenerate 1-note slurs
          var leftNotes = 0, rightNotes = 0;
          for (var ci = slurInfo.startIdx; ci <= cutIdx; ci++) {
            if (part.elements[ci].type === 'note' && !part.elements[ci].grace) leftNotes++;
          }
          for (var ci = nextNoteIdx; ci <= slurInfo.endIdx; ci++) {
            if (part.elements[ci].type === 'note' && !part.elements[ci].grace) rightNotes++;
          }
          if (leftNotes >= 2) {
            cutEl.slurEnd = true;
          } else {
            // Left sub-slur would be 1 note — remove it instead
            part.elements[slurInfo.startIdx].slurStart = false;
          }
          if (rightNotes >= 2) {
            nextEl.slurStart = true;
          } else {
            // Right sub-slur would be 1 note — remove it instead
            part.elements[slurInfo.endIdx].slurEnd = false;
          }
        }
        syncModelToTextarea();
        isDragging = true;
        setTimeout(function() { isDragging = false; }, 300);
      });
      // Suppress click/pointerup propagation like beam hit areas
      hitRect.addEventListener('click', function(e) {
        if (currentTool === 'scissors') { e.stopImmediatePropagation(); e.preventDefault(); }
      }, true);
      hitRect.addEventListener('click', function(e) {
        if (currentTool === 'scissors') { e.stopImmediatePropagation(); e.preventDefault(); }
      });
      hitRect.addEventListener('pointerup', function(e) {
        if (currentTool === 'scissors') { e.stopImmediatePropagation(); }
      }, true);
      hitRect.addEventListener('pointerup', function(e) {
        if (currentTool === 'scissors') { e.stopImmediatePropagation(); }
      });
    } catch(ex) {}
  }
}

// Find the slur (slurStart..slurEnd range) whose notes span the given X range.
// Returns {startIdx, endIdx} of model indices, or null.
function findSlurSpanningX(part, positions, hitLeftX, hitRightX) {
  // Find all slur ranges in the model
  var slurs = [];
  var slurStack = [];
  for (var i = 0; i < part.elements.length; i++) {
    var el = part.elements[i];
    if (el.type === 'note' && el.slurStart) slurStack.push(i);
    if (el.type === 'note' && el.slurEnd && slurStack.length > 0) {
      slurs.push({startIdx: slurStack.pop(), endIdx: i});
    }
  }
  if (slurs.length === 0) return null;
  // Find the slur whose notes best match the hit area X range
  var bestSlur = null;
  var bestOverlap = -1;
  for (var si = 0; si < slurs.length; si++) {
    var s = slurs[si];
    // Get X positions of start and end notes
    var startSelIdx = modelIdxToSelectableIdx(part, s.startIdx);
    var endSelIdx = modelIdxToSelectableIdx(part, s.endIdx);
    if (startSelIdx < 0 || endSelIdx < 0) continue;
    if (startSelIdx >= positions.length || endSelIdx >= positions.length) continue;
    var slurLeftX = positions[startSelIdx].centerX;
    var slurRightX = positions[endSelIdx].centerX;
    // Check overlap between hit area and slur span
    var overlapLeft = Math.max(hitLeftX, slurLeftX);
    var overlapRight = Math.min(hitRightX, slurRightX);
    var overlap = overlapRight - overlapLeft;
    if (overlap > bestOverlap) {
      bestOverlap = overlap;
      bestSlur = s;
    }
  }
  return bestSlur;
}

// Convert model index to selectable index (inverse of selectableIdxToModelIdx)
function modelIdxToSelectableIdx(part, modelIdx) {
  var selectableCount = 0;
  for (var j = 0; j < part.elements.length; j++) {
    if (part.elements[j].type === 'bar') continue;
    if (part.elements[j].grace) continue;
    if (j === modelIdx) return selectableCount;
    selectableCount++;
  }
  return -1;
}

// Find the note boundary within a slur closest to clickSvgX for cutting.
// Returns the model index of the note just BEFORE the cut point.
function findSlurCutIndex(part, positions, slurInfo, clickSvgX) {
  // Collect the non-grace note indices within the slur range
  var noteIndices = [];
  for (var i = slurInfo.startIdx; i <= slurInfo.endIdx; i++) {
    var el = part.elements[i];
    if ((el.type === 'note' || el.type === 'rest') && !el.grace) {
      noteIndices.push(i);
    }
  }
  if (noteIndices.length < 2) return -1;
  // Find the boundary between adjacent notes closest to click X
  var bestIdx = -1;
  var bestDist = Infinity;
  for (var ni = 0; ni < noteIndices.length - 1; ni++) {
    var selIdx1 = modelIdxToSelectableIdx(part, noteIndices[ni]);
    var selIdx2 = modelIdxToSelectableIdx(part, noteIndices[ni + 1]);
    if (selIdx1 < 0 || selIdx2 < 0) continue;
    if (selIdx1 >= positions.length || selIdx2 >= positions.length) continue;
    var midX = (positions[selIdx1].centerX + positions[selIdx2].centerX) / 2;
    var dist = Math.abs(midX - clickSvgX);
    if (dist < bestDist) {
      bestDist = dist;
      bestIdx = noteIndices[ni];
    }
  }
  return bestIdx;
}

function findPartForSvgElement(svgEl) {
  // Find which part rendering contains this SVG element
  for (var i = 0; i < partRenderings.length; i++) {
    var svg = partRenderings[i].renderTarget.querySelector('svg');
    if (svg && svg.contains(svgEl)) return i;
  }
  return -1;
}

function findBarModelIndex(partIdx, barSvgEl) {
  // Find all .abcjs-bar elements in this part's SVG, determine which
  // position the clicked bar is at, then map to the nth bar in the model
  if (partIdx >= partRenderings.length) return -1;
  var pr = partRenderings[partIdx];
  var svg = pr.renderTarget.querySelector('svg');
  if (!svg) return -1;
  var allBars = svg.querySelectorAll('.abcjs-bar');
  var svgBarIdx = -1;
  for (var i = 0; i < allBars.length; i++) {
    if (allBars[i] === barSvgEl) { svgBarIdx = i; break; }
  }
  if (svgBarIdx < 0) return -1;
  // Map to nth bar in model
  var part = notationModel.parts[partIdx];
  var barCount = 0;
  for (var i = 0; i < part.elements.length; i++) {
    if (part.elements[i].type === 'bar') {
      if (barCount === svgBarIdx) return i;
      barCount++;
    }
  }
  return -1;
}

// --- Beam Group Lookup by Click Position ---
// Given a click at (clientX, clientY), find the beam group at that position
// and return its selected elements array, or null if no beam group found.
function findBeamGroupAtPoint(clientX, clientY) {
  var staff = getStaffAtPoint(clientX, clientY);
  if (!staff) return null;
  var pr = null;
  for (var pi = 0; pi < partRenderings.length; pi++) {
    if (partRenderings[pi].partIdx === staff.partIdx) { pr = partRenderings[pi]; break; }
  }
  if (!pr || !pr.beamGroups || pr.beamGroups.length === 0) return null;
  var positions = pr.elementPositions || [];
  var part = notationModel.parts[pr.partIdx];
  if (!part || positions.length === 0) return null;
  var svg = pr.renderTarget ? pr.renderTarget.querySelector('svg') : null;
  if (!svg) return null;
  var clickSvgX = clientToSvgCoords(svg, clientX, clientY).x;
  // Find the closest element position to the click
  var closestSelIdx = -1;
  var closestDist = Infinity;
  for (var i = 0; i < positions.length; i++) {
    var dist = Math.abs(positions[i].centerX - clickSvgX);
    if (dist < closestDist) { closestDist = dist; closestSelIdx = i; }
  }
  if (closestSelIdx < 0 || closestDist > 30) return null;
  var clickedModelIdx = selectableIdxToModelIdx(part, closestSelIdx);
  // Find which beam group contains this element
  for (var bi = 0; bi < pr.beamGroups.length; bi++) {
    var bg = pr.beamGroups[bi];
    for (var ni = 0; ni < bg.elemIndices.length; ni++) {
      if (bg.elemIndices[ni] === clickedModelIdx) {
        var result = [];
        for (var j = 0; j < bg.elemIndices.length; j++) {
          result.push({partIdx: pr.partIdx, elemIdx: bg.elemIndices[j]});
        }
        return result;
      }
    }
  }
  return null;
}

// Find the beam cut point: the note boundary within a beam group closest to click X.
// Returns {partIdx, elemIdx} of the note just BEFORE the cut point, or null.
function findBeamCutPoint(clientX, clientY, hintPartIdx) {
  var staff = getStaffAtPoint(clientX, clientY);
  if (!staff) return null;
  var pr = null;
  for (var pi = 0; pi < partRenderings.length; pi++) {
    if (partRenderings[pi].partIdx === staff.partIdx) { pr = partRenderings[pi]; break; }
  }
  if (!pr || !pr.beamGroups || pr.beamGroups.length === 0) return null;
  var positions = pr.elementPositions || [];
  var part = notationModel.parts[pr.partIdx];
  if (!part || positions.length === 0) return null;
  var svg = pr.renderTarget ? pr.renderTarget.querySelector('svg') : null;
  if (!svg) return null;
  var clickSvgX = clientToSvgCoords(svg, clientX, clientY).x;
  // Find the closest element to the click
  var closestSelIdx = -1;
  var closestDist = Infinity;
  for (var i = 0; i < positions.length; i++) {
    var dist = Math.abs(positions[i].centerX - clickSvgX);
    if (dist < closestDist) { closestDist = dist; closestSelIdx = i; }
  }
  if (closestSelIdx < 0 || closestDist > 40) return null;
  var clickedModelIdx = selectableIdxToModelIdx(part, closestSelIdx);
  // Find which beam group contains this element
  for (var bi = 0; bi < pr.beamGroups.length; bi++) {
    var bg = pr.beamGroups[bi];
    var posInGroup = -1;
    for (var ni = 0; ni < bg.elemIndices.length; ni++) {
      if (bg.elemIndices[ni] === clickedModelIdx) { posInGroup = ni; break; }
    }
    if (posInGroup < 0) continue;
    // Find the boundary between adjacent notes closest to the click X.
    // Each boundary is between position[n] and position[n+1] in the group.
    // We want to set spaceAfter on the note just before the boundary.
    var bestBoundaryIdx = -1;
    var bestBoundaryDist = Infinity;
    for (var bj = 0; bj < bg.elemIndices.length - 1; bj++) {
      // Get SVG positions for these two elements
      var modelIdx1 = bg.elemIndices[bj];
      var modelIdx2 = bg.elemIndices[bj + 1];
      // Find selectable indices for these model indices
      var selIdx1 = -1, selIdx2 = -1;
      var sc = 0;
      for (var mi = 0; mi < part.elements.length; mi++) {
        if (part.elements[mi].type === 'bar' || part.elements[mi].grace) continue;
        if (mi === modelIdx1) selIdx1 = sc;
        if (mi === modelIdx2) selIdx2 = sc;
        sc++;
      }
      if (selIdx1 >= 0 && selIdx2 >= 0 && selIdx1 < positions.length && selIdx2 < positions.length) {
        var midX = (positions[selIdx1].centerX + positions[selIdx2].centerX) / 2;
        var dist = Math.abs(midX - clickSvgX);
        if (dist < bestBoundaryDist) {
          bestBoundaryDist = dist;
          bestBoundaryIdx = bj;
        }
      }
    }
    if (bestBoundaryIdx >= 0) {
      return {partIdx: pr.partIdx, elemIdx: bg.elemIndices[bestBoundaryIdx]};
    }
  }
  return null;
}

// --- Staff Click-to-Place ---
function setupStaffClick() {
  // Use event delegation on the preview container so it works with
  // dynamically created per-part SVGs
  var preview = document.getElementById('abcjs-preview');
  if (!preview) return;
  // Track shift state on pointerdown for reliable shift-click detection
  preview.addEventListener('pointerdown', function(e) {
    lastPointerShift = e.shiftKey;
  });
  // Bar selection via hit areas — handles clicks on ve-bar-hitarea rects
  // and any .abcjs-bar descendants that abcjs doesn't route through its callback
  preview.addEventListener('click', function(e) {
    if (veMode !== 'visual') return;
    if (isDragging) return;
    // Only handle selection mode (no placement tool active)
    if (currentTool && ['whole','half','quarter','eighth','sixteenth','rest-whole','rest-half','rest-quarter','rest-eighth','rest-sixteenth','bar','bar-open','bar-close'].indexOf(currentTool) >= 0) return;
    var barEl = findBarAncestor(e.target);
    if (!barEl) return;
    var barPartIdx = findPartForSvgElement(barEl);
    if (barPartIdx < 0) return;
    var modelIdx = findBarModelIndex(barPartIdx, barEl);
    if (modelIdx < 0) return;
    var isShift = e.shiftKey;
    if (isShift && selectedElements.length > 0) {
      var anchor = selectedElements[0];
      if (anchor.partIdx === barPartIdx) {
        var lo = Math.min(anchor.elemIdx, modelIdx);
        var hi = Math.max(anchor.elemIdx, modelIdx);
        selectedElements = [];
        for (var ri = lo; ri <= hi; ri++) {
          selectedElements.push({partIdx: barPartIdx, elemIdx: ri});
        }
      } else {
        selectedElements.push({partIdx: barPartIdx, elemIdx: modelIdx});
      }
    } else {
      selectedElements = [{partIdx: barPartIdx, elemIdx: modelIdx}];
    }
    highlightSelected();
    setTimeout(highlightSelected, 20);
    showPropertyIndicator();
  });
  // Beam group selection — double-click a note to select all notes in its
  // beam group (the notes connected by the same horizontal beam bar).
  preview.addEventListener('dblclick', function(e) {
    if (veMode !== 'visual') return;
    if (currentTool) return;  // Only in selection mode
    var beamSel = findBeamGroupAtPoint(e.clientX, e.clientY);
    if (!beamSel) return;
    selectedElements = beamSel;
    highlightSelected();
    setTimeout(highlightSelected, 20);
    showPropertyIndicator();
    e.preventDefault();
  });
  // Deselect when clicking empty area (not on a note/rest/bar)
  preview.addEventListener('click', function(e) {
    if (veMode !== 'visual') return;
    if (isDragging) return;
    // Check if the click target is inside an abcjs note/rest SVG element —
    // if so, the abcjs callback or bar handler will handle it
    var t = e.target;
    while (t && t !== preview) {
      var cls = (t.getAttribute && t.getAttribute('class')) || '';
      if (cls.indexOf('abcjs-note') >= 0 || cls.indexOf('abcjs-rest') >= 0 ||
          cls.indexOf('abcjs-bar') >= 0 || cls.indexOf('ve-bar-hitarea') >= 0 ||
          cls.indexOf('ve-slur-hitarea') >= 0) return;
      t = t.parentElement;
    }
    // Clicking empty area deactivates scissors tool
    if (currentTool === 'scissors') {
      activateSelectTool();
      return;
    }
    if (selectedElements.length === 0) return;
    selectedElements = [];
    highlightSelected();
    hidePropertyIndicator();
  });
  preview.addEventListener('pointerup', function(e) {
    if (veMode !== 'visual') return;
    if (isDragging) return;
    lastPointerShift = e.shiftKey;

    if (!currentTool) return;
    if (['whole','half','quarter','eighth','sixteenth','rest-whole','rest-half','rest-quarter','rest-eighth','rest-sixteenth','bar','bar-open','bar-close'].indexOf(currentTool) < 0) return;

    var overStaff = getStaffAtPoint(e.clientX, e.clientY);
    if (overStaff) {
      placeElementOnStaff(currentTool, overStaff, e.clientX);
    }
  });
}

// --- Rubber-Band Drag Selection ---
function setupRubberBandSelection() {
  var preview = document.getElementById('ve-preview-container');
  if (!preview) return;
  var rbStartX, rbStartY, rbPartIdx, isRubberBanding;
  var rbDiv = null;
  var rbPointerId = null;

  preview.addEventListener('pointerdown', function(e) {
    if (veMode !== 'visual') return;
    if (currentTool !== null) return;  // Only in selection mode
    // Don't start rubber-band on toolbar buttons or property UI
    var t = e.target;
    var onInteractive = false;
    while (t && t !== preview) {
      var cls = (t.getAttribute && t.getAttribute('class')) || '';
      if (cls.indexOf('ve-tool') >= 0 || cls.indexOf('ve-mode') >= 0 ||
          cls.indexOf('ve-prop') >= 0) return;
      // Don't start on existing notes/rests/bars — let normal click handle those
      if (cls.indexOf('abcjs-note') >= 0 || cls.indexOf('abcjs-rest') >= 0 ||
          cls.indexOf('abcjs-bar') >= 0 || cls.indexOf('ve-bar-hitarea') >= 0 ||
          cls.indexOf('ve-slur-hitarea') >= 0) { onInteractive = true; break; }
      t = t.parentElement;
    }
    if (onInteractive) return;
    // Prevent native browser drag on SVG elements
    e.preventDefault();
    // Determine which part we're starting in
    var staff = getStaffAtPoint(e.clientX, e.clientY);
    if (!staff) {
      // Clicked empty space outside any staff — deselect
      if (selectedElements.length > 0) {
        selectedElements = [];
        highlightSelected();
        hidePropertyIndicator();
      }
      return;
    }
    rbStartX = e.clientX;
    rbStartY = e.clientY;
    rbPartIdx = staff.partIdx;
    isRubberBanding = false;
    rbPointerId = e.pointerId;
    preview.setPointerCapture(e.pointerId);
  });

  preview.addEventListener('pointermove', function(e) {
    if (rbPointerId === null || e.pointerId !== rbPointerId) return;
    var dx = e.clientX - rbStartX;
    var dy = e.clientY - rbStartY;
    if (!isRubberBanding && (dx * dx + dy * dy) < 25) return;  // 5px threshold
    isRubberBanding = true;

    // Create or update rubber-band div
    var left = Math.min(rbStartX, e.clientX);
    var top = Math.min(rbStartY, e.clientY);
    var width = Math.abs(e.clientX - rbStartX);
    var height = Math.abs(e.clientY - rbStartY);
    if (!rbDiv) {
      rbDiv = document.createElement('div');
      rbDiv.className = 've-rubber-band';
      document.body.appendChild(rbDiv);
    }
    rbDiv.style.left = left + 'px';
    rbDiv.style.top = top + 'px';
    rbDiv.style.width = width + 'px';
    rbDiv.style.height = height + 'px';

    // Hit-test elements in the target part against the rubber-band rectangle
    var rbLeft = left, rbRight = left + width, rbTop = top, rbBottom = top + height;
    var newSelected = [];
    var rbPart = (rbPartIdx < partRenderings.length) ? notationModel.parts[partRenderings[rbPartIdx].partIdx] : null;
    if (rbPartIdx < partRenderings.length) {
      var pr = partRenderings[rbPartIdx];
      var positions = pr.elementPositions || [];
      var svg = pr.renderTarget ? pr.renderTarget.querySelector('svg') : null;
      if (svg && positions.length > 0) {
        var ctm = svg.getScreenCTM();
        if (ctm) {
          for (var i = 0; i < positions.length; i++) {
            var pos = positions[i];
            // Convert SVG coords to client coords using the CTM
            var elLeft = ctm.a * pos.x + ctm.e;
            var elRight = ctm.a * (pos.x + pos.w) + ctm.e;
            // Check horizontal overlap with rubber-band
            if (elRight >= rbLeft && elLeft <= rbRight) {
              // Use vertical overlap too — check against SVG bounds
              var svgRect = svg.getBoundingClientRect();
              if (svgRect.bottom >= rbTop && svgRect.top <= rbBottom) {
                var modelIdx = rbPart ? selectableIdxToModelIdx(rbPart, i) : i;
                newSelected.push({partIdx: pr.partIdx, elemIdx: modelIdx});
              }
            }
          }
        }
      }
    }
    // Expand selection to include grace note partners: if a main note
    // is selected, also select its preceding grace note, and vice versa.
    if (rbPart && newSelected.length > 0) {
      var selSet = {};
      for (var si = 0; si < newSelected.length; si++) {
        selSet[newSelected[si].elemIdx] = true;
      }
      var toAdd = [];
      for (var si = 0; si < newSelected.length; si++) {
        var idx = newSelected[si].elemIdx;
        var el = rbPart.elements[idx];
        // If this is a grace note, also select the following main note
        if (el && el.grace && idx + 1 < rbPart.elements.length && !selSet[idx + 1]) {
          toAdd.push({partIdx: newSelected[si].partIdx, elemIdx: idx + 1});
          selSet[idx + 1] = true;
        }
        // If preceding element is a grace note, also select it
        if (idx > 0 && rbPart.elements[idx - 1].grace && !selSet[idx - 1]) {
          toAdd.push({partIdx: newSelected[si].partIdx, elemIdx: idx - 1});
          selSet[idx - 1] = true;
        }
      }
      for (var ai = 0; ai < toAdd.length; ai++) {
        newSelected.push(toAdd[ai]);
      }
    }
    selectedElements = newSelected;
    highlightSelected();
  });

  function endRubberBand(e) {
    if (rbPointerId === null || e.pointerId !== rbPointerId) return;
    if (rbDiv) {
      rbDiv.parentNode.removeChild(rbDiv);
      rbDiv = null;
    }
    var wasRubberBanding = isRubberBanding;
    rbPointerId = null;
    try { preview.releasePointerCapture(e.pointerId); } catch(ex) {}
    if (wasRubberBanding) {
      // Suppress the click handler from deselecting
      isDragging = true;
      setTimeout(function() { isDragging = false; }, 50);
      // Show property indicator for selection
      if (selectedElements.length > 0) {
        showPropertyIndicator();
      }
    }
  }

  preview.addEventListener('pointerup', endRubberBand);
  preview.addEventListener('pointercancel', endRubberBand);
}

// --- Place Element on Staff ---
function placeElementOnStaff(tool, overStaff, clientX) {
  var partIdx = overStaff.partIdx;
  if (partIdx >= notationModel.parts.length) return;
  var part = notationModel.parts[partIdx];

  var localX = overStaff.localX;
  if (localX === undefined) {
    var svg = overStaff.svg || document.querySelector('#abcjs-preview svg');
    if (svg) {
      var svgPt = clientToSvgCoords(svg, clientX, 0);
      localX = svgPt.x;
    } else {
      localX = 0;
    }
  }
  var insertIdx = xToInsertionIndex(localX, partIdx);

  pushUndo();

  var elem = null;
  var restMatch = tool.match(/^rest-(whole|half|quarter|eighth|sixteenth)$/);
  if (restMatch) {
    elem = { type: 'rest', duration: toolToDuration(restMatch[1]) };
  } else if (tool === 'bar') {
    elem = { type: 'bar', subtype: '|' };
  } else if (tool === 'bar-open') {
    elem = { type: 'bar', subtype: '|:' };
  } else if (tool === 'bar-close') {
    elem = { type: 'bar', subtype: ':|' };
  } else {
    // Note — map Y to pitch
    var snappedPos = yToStaffPosition(overStaff.localY, overStaff.geo);
    var pp = staffPositionToPitch(snappedPos);
    elem = {
      type: 'note',
      pitch: pp.pitch,
      octave: pp.octave,
      duration: toolToDuration(tool),
      accidental: null,
      tied: false,
      slurStart: false,
      slurEnd: false
    };
  }

  if (insertIdx >= part.elements.length) {
    part.elements.push(elem);
  } else {
    part.elements.splice(insertIdx, 0, elem);
  }

  syncModelToTextarea();
}

// --- Get Staff at Point ---
// Searches all per-part SVGs to find which part the point is in
function getStaffAtPoint(clientX, clientY) {
  for (var i = 0; i < partRenderings.length; i++) {
    var pr = partRenderings[i];
    if (!pr.geo) continue;
    var svg = pr.renderTarget.querySelector('svg');
    if (!svg) continue;
    var svgRect = svg.getBoundingClientRect();
    if (clientX < svgRect.left || clientX > svgRect.right ||
        clientY < svgRect.top || clientY > svgRect.bottom) continue;

    var svgPt = clientToSvgCoords(svg, clientX, clientY);
    return {
      partIdx: pr.partIdx,
      geo: pr.geo,
      svg: svg,
      localX: svgPt.x,
      localY: svgPt.y,
      clientX: clientX,
      clientY: clientY
    };
  }
  return null;
}

// --- Insertion Marker ---
function showInsertionMarker(overStaff, clientX) {
  removeInsertionMarker();
  var svg = overStaff.svg || document.querySelector('#abcjs-preview svg');
  if (!svg) return;
  var svgPt = clientToSvgCoords(svg, clientX, 0);
  var localX = svgPt.x;
  var geo = overStaff.geo;
  var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
  line.setAttribute('x1', localX);
  line.setAttribute('y1', geo.y0 - geo.spacing);
  line.setAttribute('x2', localX);
  line.setAttribute('y2', geo.y4 + geo.spacing);
  line.setAttribute('class', 've-insertion-marker');
  svg.appendChild(line);
  insertionMarker = line;
}

function removeInsertionMarker() {
  if (insertionMarker && insertionMarker.parentNode) {
    insertionMarker.parentNode.removeChild(insertionMarker);
  }
  insertionMarker = null;
}

// --- Keyboard Shortcuts ---
function setupKeyboardShortcuts() {
  document.addEventListener('keydown', function(e) {
    if (veMode !== 'visual') return;
    // Don't intercept when focused on input/textarea/select
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

    // Delete/Backspace: remove selected
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (selectedElements.length > 0) {
        e.preventDefault();
        veDeleteSelected();
      }
      return;
    }
    // Ctrl/Cmd+Z: undo
    if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
      e.preventDefault();
      doUndo();
      return;
    }
    // Ctrl/Cmd+Shift+Z or Ctrl+Y: redo
    if ((e.ctrlKey || e.metaKey) && (e.key === 'Z' || e.key === 'y')) {
      e.preventDefault();
      doRedo();
      return;
    }
    // Escape: deselect
    if (e.key === 'Escape') {
      selectedElements = [];
      clearToolSelection();
      highlightSelected();
      hidePropertyIndicator();
      return;
    }
    // Left arrow: select previous note
    if (e.key === 'ArrowLeft' && selectedElements.length > 0) {
      e.preventDefault();
      var sel = selectedElements[0];
      if (sel.elemIdx > 0) {
        selectedElements = [{partIdx: sel.partIdx, elemIdx: sel.elemIdx - 1}];
        highlightSelected();
        showPropertyIndicator();
      }
      return;
    }
    // Right arrow: select next note
    if (e.key === 'ArrowRight' && selectedElements.length > 0) {
      e.preventDefault();
      var sel = selectedElements[0];
      var maxIdx = notationModel.parts[sel.partIdx].elements.length - 1;
      if (sel.elemIdx < maxIdx) {
        selectedElements = [{partIdx: sel.partIdx, elemIdx: sel.elemIdx + 1}];
        highlightSelected();
        showPropertyIndicator();
      }
      return;
    }
  });
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', function() {
  // Override doRenderAbc with visual editor version
  if (typeof doRenderAbc !== 'undefined') {
    origDoRenderAbc = doRenderAbc;
  }
  doRenderAbc = veDoRenderAbc;

  // Parse initial ABC into model
  var textarea = document.getElementById('raw-notes-textarea');
  if (textarea && textarea.value.trim()) {
    notationModel = parseAbcToModel(textarea.value);
  }

  // Setup toolbar
  setupToolbar();
  setupStaffClick();
  setupRubberBandSelection();
  setupKeyboardShortcuts();
  setupPropertyIndicator();

  // Start in visual mode
  toggleEditorMode('visual');

  // For new tunes with no ABC, add an initial empty part
  if (!textarea || !textarea.value.trim()) {
    addNotePart(0);
    undoStack = [];
    redoStack = [];
  }
});

</script>
""" % (defaults_js, url_count, len(chord_parts))

@app.route('/tune/<tune>/edit')
def tune_edit(tune):
  if not HasCapability(kCapEditTunes):
    return redirect('/authorize/tune/%s/edit' % tune, code=303)

  obj = utils.CTune(tune)
  try:
    obj.ReadDatabase()
  except SystemExit:
    pass

  return _build_tune_form(obj, tune, 'Edit Tune', '/tune/%s/save' % tune, '/tune/%s' % tune)

def _build_tune_form(obj, tune, heading, save_action, cancel_url):
  """Build the full tune editor form, shared by edit and new tune pages."""

  # Parse chords into structured form for the editor
  chord_parts = []  # list of {'rows': [[cell, ...], ...], 'repeat': bool}
  header_text = ''
  footer_text = ''
  num_columns = 4

  if obj.chords and obj.chords.strip():
    chord_lines = obj.chords.strip().splitlines()
    header_lines = []
    footer_lines = []
    chart_lines = []
    in_chart = False
    past_chart = False
    for line in chord_lines:
      if '|' in line:
        in_chart = True
        past_chart = False
        chart_lines.append(line)
      elif in_chart:
        past_chart = True
        in_chart = False
        footer_lines.append(line)
      elif past_chart:
        footer_lines.append(line)
      else:
        header_lines.append(line)
    header_text = '\n'.join(header_lines)
    footer_text = '\n'.join(footer_lines)

    chart_text = '\n'.join(chart_lines)
    parsed = utils.ParseChords(chart_text)
    num_columns = GetNumColumns(parsed)

    # Convert parsed chords into structured parts
    for part in parsed:
      has_repeat = '|:' in part or ':|' in part
      cells = [m for m in part if m not in ('|:', ':|')]
      rows = []
      row = []
      for cell in cells:
        row.append(cell)
        if len(row) == num_columns:
          rows.append(row)
          row = []
      if row:
        rows.append(row)
      chord_parts.append({'rows': rows, 'repeat': has_repeat})

  # If no chord parts, create a default empty structure
  if not chord_parts:
    ttype = obj.klass.split(',')[0] if obj.klass else 'reel'
    defaults = utils.kDefaultsByType.get(ttype, utils.kDefaultsByType['reel'])
    num_columns = defaults['measures'] / defaults['rows']
    for p in range(2):
      rows = []
      for r in range(defaults['rows']):
        rows.append([''] * num_columns)
      chord_parts.append({'rows': rows, 'repeat': True})

  # Current types
  current_types = set(obj.klass.split(',')) if obj.klass else set()

  # URL list
  url_list = []
  if obj.url:
    url_list = [u.strip() for u in obj.url.split('\n') if u.strip()]

  parts = []
  parts.append(CH(heading, 2))

  # Build the editor JavaScript
  editor_js = _build_editor_js(tune, chord_parts, max(len(url_list), 1))

  # Build form fields
  meter_options = [('C', 'C'), ('5/8', '5/8'), ('6/8', '6/8'), ('7/8', '7/8'), ('9/8', '9/8'), ('2/4', '2/4'), ('3/4', '3/4'), ('4/4', '4/4')]
  unit_options = [('1/16', '1/16'), ('1/8', '1/8'), ('1/4', '1/4'), ('1/2', '1/2')]

  form_body = [
    editor_js,

    # Hidden structural fields
    CInput(type='HIDDEN', name='num_parts', value=str(len(chord_parts))),
  ]

  # Hidden fields for rows_in_part and repeat per part
  for p_idx, cp in enumerate(chord_parts):
    form_body.append(CInput(type='HIDDEN', name='rows_in_part_%d' % p_idx, value=str(len(cp['rows']))))

  form_body.extend([
    # Title, Key, Type on one flex row
    CDiv([
      CDiv([
        CInput(type='text', name='title', value=obj.title or '', hclass='title-input', placeholder='Enter title here'),
      ], hclass='title-field'),
      CDiv([
        _build_key_selector(obj.key or ''),
      ], hclass='key-field'),
      CDiv([
        _build_type_selector(current_types),
      ], hclass='type-field'),
    ], hclass='title-row'),

    # Structure (e.g. AABBCCBB)
    CDiv([
      CInput(type='text', name='structure', value=obj.structure or '', hclass='wide-input', placeholder='Add playing notes here (if any)'),
    ], hclass='field-row'),

    # Author
    CDiv([
      CInput(type='text', name='author', value=obj.author or '', hclass='wide-input', placeholder='Enter author here'),
    ], hclass='field-row'),

    # Origin
    CDiv([
      CInput(type='text', name='origin', value=obj.origin or '', hclass='wide-input', placeholder='Enter origin here'),
    ], hclass='field-row'),

    # History
    CDiv('History:', hclass='section-header'),
    CDiv([
      CTextArea(obj.history or '', name='history', rows=6, cols=80, hclass='description-field'),
    ], hclass='field-row'),

    # Notes (ref field — "Collected from Author", etc.)
    CDiv('Notes:', hclass='section-header'),
    CDiv([
      CTextArea(obj.ref or '', name='ref', rows=3, cols=80, hclass='description-field'),
    ], hclass='field-row'),

    # References (URLs)
    CDiv('References:', hclass='section-header'),
    CDiv(_build_url_fields(url_list), id='url-container'),
    CDiv([
      '<button type="button" class="add-btn" onclick="addUrlField()">+ Add Reference</button>',
    ], hclass='field-row', style='margin-top:4px'),

    # Notes (ABC)
    CDiv('Melody Reminder (ABC Format):', hclass='section-header'),
    CDiv(_build_notes_section(obj, tune, meter_options, unit_options), hclass='notes-section', id='notes-section'),

    # Chords
    CDiv('Chords:', hclass='section-header'),
    CDiv([
      # Left: chord editor
      CDiv([
        CDiv([
          CInput(type='text', name='chord_header', value=header_text, placeholder='Header notes', style='width:100%'),
        ], hclass='field-row'),
        CDiv(_build_chord_tables(chord_parts, num_columns), id='chord-parts-container'),
        CDiv([
          CInput(type='text', name='chord_footer', value=footer_text, placeholder='Footer notes', style='width:100%'),
        ], hclass='field-row'),
        CDiv([
          '<button type="button" class="add-btn" onclick="addPart()">+ Add Part</button>',
        ], hclass='chord-structure-controls'),
      ], hclass='chord-editor-pane'),
      # Right: live preview
      CDiv([
        CDiv('', id='chord-preview-inner'),
      ], hclass='chord-preview-pane', id='chord-preview-pane'),
    ], hclass='chord-layout'),

    # Submit
    CBreak(2),
    CInput(type='SUBMIT', value='  Save  '),
    CText(' '),
    CInput(type='button', value='  Cancel  ', onclick="window.location='%s'" % cancel_url),
  ])

  parts.append(CForm(form_body, action=save_action, method='POST',
                      hclass='edit-form', onsubmit='return validateForm()'))

  # Chord notation guide
  parts.append(_chord_notation_guide())

  return PageWrapper(parts, 'index', show_eye_candy=False)

def _build_key_selector(key_str):
  """Build a clickable key display with popup editor for single or multi-key tunes."""
  # Parse key string into parts: D -> [('D','')], Em -> [('E','m')], D/G -> [('D',''),('G','')]
  key_parts = []
  if key_str.strip():
    for k in key_str.split('/'):
      k = k.strip()
      if k.endswith('mix'):
        key_parts.append((k[:-3], 'mix'))
      elif k.endswith('m'):
        key_parts.append((k[:-1], 'm'))
      else:
        key_parts.append((k, ''))

  # Build display label matching GetKeyString() format
  if key_parts:
    display_parts = []
    for letter, mode in key_parts:
      if mode == 'm':
        display_parts.append(letter + ' Minor')
      elif mode == 'mix':
        display_parts.append(letter + ' Modal')
      else:
        display_parts.append(letter + ' Major')
    display = ' / '.join(display_parts)
  else:
    display = 'Select Key'

  # Build key editor rows for the popup
  letters = 'A B C D E F G H'.split()
  modes = [('', 'Major'), ('m', 'Minor'), ('mix', 'Modal')]

  rows_html = ''
  for i, (letter, mode) in enumerate(key_parts):
    rows_html += _key_editor_row_html(i, letter, mode, letters, modes, True)

  return CDiv([
    CInput(type='HIDDEN', name='key', value=key_str, id='field-key'),
    '<button type="button" class="key-display-btn" id="key-display-btn" onclick="toggleKeyEditor()">'
    '<span id="key-display-label">%s</span> &#9662;</button>' % display,
    CDiv([
      CDiv('', id='key-rows-container'),
      CDiv([
        '<button type="button" class="add-btn" style="font-size:85%; padding:2px 8px" '
        'onclick="addKeyPart()">+ Key</button>',
      ], style='margin-top:4px'),
    ], hclass='key-editor-dropdown', id='key-editor-dropdown'),
    '<script>var initialKeyParts = [%s];</script>' % ','.join(['["%s","%s"]' % (l, m) for l, m in key_parts]),
  ], hclass='key-editor-container', id='key-editor-container')

def _key_editor_row_html(idx, letter, mode, letters, modes, show_remove):
  """Build HTML for one key editor row (used server-side and pattern for JS)."""
  letter_opts = ''
  for l in letters:
    sel = ' selected' if l == letter else ''
    letter_opts += '<option value="%s"%s>%s</option>' % (l, sel, l)
  mode_opts = ''
  for mv, ml in modes:
    sel = ' selected' if mv == mode else ''
    mode_opts += '<option value="%s"%s>%s</option>' % (mv, sel, ml)
  remove_btn = ''
  if show_remove:
    remove_btn = (' <button type="button" class="url-remove-btn" style="font-size:85%; padding:1px 6px" '
                   'onclick="removeKeyPart(this)">X</button>')
  return ('<div class="key-editor-row">'
          '<select class="key-letter" onchange="updateKeyValue()">%s</select> '
          '<select class="key-mode" onchange="updateKeyValue()">%s</select>'
          '%s</div>' % (letter_opts, mode_opts, remove_btn))

def _build_type_selector(current_types):
  """Build a popup multi-select dropdown for tune types."""
  # Build the summary text from current selections
  labels = []
  for sname, stitle, slabel in utils.kSections:
    if sname == 'incomplete':
      continue
    if sname in current_types:
      labels.append(slabel or sname.capitalize())
  summary = ', '.join(labels) if labels else 'Select Type...'

  # Build checkbox items for the dropdown
  items = []
  for sname, stitle, slabel in utils.kSections:
    if sname == 'incomplete':
      continue
    label = slabel or sname.capitalize()
    checked_attr = ' checked' if sname in current_types else ''
    items.append(
      '<label class="type-menu-item">'
      '<input type="checkbox" name="klass_%s" value="1"%s onchange="updateTypeLabel()" /> %s'
      '</label>' % (sname, checked_attr, label)
    )

  return CDiv([
    '<button type="button" class="type-menu-btn" id="type-menu-btn" onclick="toggleTypeMenu()">'
    '<span id="type-menu-label">%s</span> &#9662;</button>' % summary,
    CDiv('\n'.join(items), hclass='type-menu-dropdown', id='type-menu-dropdown'),
  ], hclass='type-menu-container', id='type-menu-container')

def _build_url_fields(url_list):
  """Build URL input rows for the editor."""
  rows = []
  for i, url in enumerate(url_list):
    rows.append(CDiv([
      CInput(type='text', name='url_%d' % i, value=url, hclass='url-field', placeholder='Enter URL here'),
      ' <button type="button" class="url-test-btn" onclick="testUrl(this)">Test</button>',
      ' <button type="button" class="url-remove-btn" onclick="removeUrlField(this)">X</button>',
    ], hclass='url-row'))
  if not url_list:
    rows.append(CDiv([
      CInput(type='text', name='url_0', value='', hclass='url-field', placeholder='Enter URL here'),
      ' <button type="button" class="url-test-btn" onclick="testUrl(this)">Test</button>',
      ' <button type="button" class="url-remove-btn" onclick="removeUrlField(this)">X</button>',
    ], hclass='url-row'))
  return rows

def _build_notes_section(obj, tune, meter_options, unit_options):
  """Build the notes (ABC) editing section with visual editor and ABC text mode."""
  raw = obj.raw_notes.rstrip('\n') if obj.raw_notes else ''

  # Mode toggle buttons
  mode_toggle = CDiv([
    '<button type="button" class="ve-mode-btn ve-mode-active" id="ve-mode-visual-btn" '
    'onclick="toggleEditorMode(\'visual\')">Visual Editor</button>',
    '<button type="button" class="ve-mode-btn" id="ve-mode-abc-btn" '
    'onclick="toggleEditorMode(\'abc\')">ABC Text</button>',
  ], hclass='ve-mode-toggle')

  # Toolbar palette (shown in visual mode)
  toolbar = CDiv([
    # Selection tool (default mode)
    CDiv([
      '<button type="button" class="ve-tool-btn" data-tool="select" id="ve-select-tool" title="Selection tool">'
      '<svg viewBox="0 0 20 24" width="16" height="20"><path d="M4,2 L4,18 L8,14 L12,20 L14,19 L10,13 L16,13 Z" fill="currentColor" stroke="currentColor" stroke-width="0.5" stroke-linejoin="round"/></svg>'
      '</button>',
    ], hclass='ve-tool-group'),
    # Duration tools
    CDiv([
      # Whole note
      '<button type="button" class="ve-tool-btn" data-tool="whole" title="Whole note">'
      '<svg viewBox="0 0 24 20" width="24" height="20"><ellipse cx="12" cy="10" rx="6" ry="4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
      # Half note
      '<button type="button" class="ve-tool-btn" data-tool="half" title="Half note">'
      '<svg viewBox="0 0 20 32" width="16" height="26"><ellipse cx="8" cy="24" rx="5.5" ry="3.5" fill="none" stroke="currentColor" stroke-width="1.5" transform="rotate(-15,8,24)"/><line x1="13" y1="23" x2="13" y2="4" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
      # Quarter note
      '<button type="button" class="ve-tool-btn" data-tool="quarter" title="Quarter note">'
      '<svg viewBox="0 0 20 32" width="16" height="26"><ellipse cx="8" cy="24" rx="5.5" ry="3.5" fill="currentColor" transform="rotate(-15,8,24)"/><line x1="13" y1="23" x2="13" y2="4" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
      # Eighth note
      '<button type="button" class="ve-tool-btn" data-tool="eighth" title="Eighth note">'
      '<svg viewBox="0 0 22 32" width="18" height="26"><ellipse cx="7" cy="24" rx="5.5" ry="3.5" fill="currentColor" transform="rotate(-15,7,24)"/><line x1="12" y1="23" x2="12" y2="4" stroke="currentColor" stroke-width="1.5"/><path d="M12,4 Q16,8 18,14" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
      # Sixteenth note
      '<button type="button" class="ve-tool-btn" data-tool="sixteenth" title="Sixteenth note">'
      '<svg viewBox="0 0 22 32" width="18" height="26"><ellipse cx="7" cy="24" rx="5.5" ry="3.5" fill="currentColor" transform="rotate(-15,7,24)"/><line x1="12" y1="23" x2="12" y2="4" stroke="currentColor" stroke-width="1.5"/><path d="M12,4 Q16,8 18,14" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M12,9 Q16,13 18,19" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
    ], hclass='ve-tool-group'),
    # Rests (one per duration)
    CDiv([
      '<button type="button" class="ve-tool-btn" data-tool="rest-whole" title="Whole rest">'
      '<svg viewBox="0 0 20 24" width="16" height="20"><line x1="2" y1="10" x2="18" y2="10" stroke="currentColor" stroke-width="1"/><rect x="5" y="10" width="10" height="4" fill="currentColor"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="rest-half" title="Half rest">'
      '<svg viewBox="0 0 20 24" width="16" height="20"><line x1="2" y1="14" x2="18" y2="14" stroke="currentColor" stroke-width="1"/><rect x="5" y="10" width="10" height="4" fill="currentColor"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="rest-quarter" title="Quarter rest">'
      '<svg viewBox="-0.5 -13 9 23" width="12" height="20"><path d="M1.89-11.82c0.12-0.06 0.24-0.06 0.36-0.03c0.09 0.06 4.74 5.58 4.86 5.82c0.21 0.39 0.15 0.78-0.15 1.26c-0.24 0.33-0.72 0.81-1.62 1.56c-0.45 0.36-0.87 0.75-0.96 0.84c-0.93 0.99-1.14 2.49-0.6 3.63c0.18 0.39 0.27 0.48 1.32 1.68c1.92 2.25 1.83 2.16 1.83 2.34c0 0.18-0.18 0.36-0.36 0.39c-0.15 0-0.27-0.06-0.48-0.27c-0.75-0.75-2.46-1.29-3.39-1.08c-0.45 0.09-0.69 0.27-0.9 0.69c-0.12 0.3-0.21 0.66-0.24 1.14c-0.03 0.66 0.09 1.35 0.3 2.01c0.15 0.42 0.24 0.66 0.45 0.96c0.18 0.24 0.18 0.33 0.03 0.42c-0.12 0.06-0.18 0.03-0.45-0.3c-1.08-1.38-2.07-3.36-2.4-4.83c-0.27-1.05-0.15-1.77 0.27-2.07c0.21-0.12 0.42-0.15 0.87-0.15c0.87 0.06 2.1 0.39 3.3 0.9l0.39 0.18l-1.65-1.95c-2.52-2.97-2.61-3.09-2.7-3.27c-0.09-0.24-0.12-0.48-0.03-0.75c0.15-0.48 0.57-0.96 1.83-2.01c0.45-0.36 0.84-0.72 0.93-0.78c0.69-0.75 1.02-1.8 0.9-2.79c-0.06-0.33-0.21-0.84-0.39-1.11c-0.09-0.15-0.45-0.6-0.81-1.05c-0.36-0.42-0.69-0.81-0.72-0.87c-0.09-0.18 0-0.42 0.21-0.51z" fill="currentColor"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="rest-eighth" title="Eighth rest">'
      '<svg viewBox="-0.5 -7 9 15" width="12" height="20"><path d="M1.68-6.12c0.66-0.09 1.23 0.09 1.68 0.51c0.27 0.3 0.39 0.54 0.57 1.26c0.09 0.33 0.18 0.66 0.21 0.72c0.12 0.27 0.33 0.45 0.6 0.48c0.12 0 0.18 0 0.33-0.09c0.39-0.18 1.32-1.29 1.68-1.98c0.09-0.21 0.24-0.3 0.39-0.3c0.12 0 0.27 0.09 0.33 0.18c0.03 0.06-0.27 1.11-1.86 6.42c-1.02 3.48-1.89 6.39-1.92 6.42c0 0.03-0.12 0.12-0.24 0.15c-0.18 0.09-0.21 0.09-0.45 0.09c-0.24 0-0.3 0-0.48-0.06c-0.09-0.06-0.21-0.12-0.21-0.15c-0.06-0.03 0.15-0.57 1.68-4.92c0.96-2.67 1.74-4.89 1.71-4.89l-0.51 0.15c-1.08 0.36-1.74 0.48-2.55 0.48c-0.66 0-0.84-0.03-1.32-0.27c-1.32-0.63-1.77-2.16-1.02-3.3c0.33-0.45 0.84-0.81 1.38-0.9z" fill="currentColor"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="rest-sixteenth" title="Sixteenth rest">'
      '<svg viewBox="-0.5 -7 11 22" width="12" height="20"><path d="M3.33-6.12c0.66-0.09 1.23 0.09 1.68 0.51c0.27 0.3 0.39 0.54 0.57 1.26c0.09 0.33 0.18 0.66 0.21 0.72c0.15 0.39 0.57 0.57 0.87 0.42c0.39-0.18 1.2-1.23 1.62-2.07c0.06-0.15 0.24-0.24 0.36-0.24c0.12 0 0.27 0.09 0.33 0.18c0.03 0.06-0.45 1.86-2.67 10.17c-1.5 5.55-2.73 10.14-2.76 10.17c-0.03 0.03-0.12 0.12-0.24 0.15c-0.18 0.09-0.21 0.09-0.45 0.09c-0.24 0-0.3 0-0.48-0.06c-0.09-0.06-0.21-0.12-0.21-0.15c-0.06-0.03 0.12-0.57 1.44-4.92c0.81-2.67 1.47-4.86 1.47-4.89c-0.03 0-0.27 0.06-0.54 0.15c-1.08 0.36-1.77 0.48-2.58 0.48c-0.66 0-0.84-0.03-1.32-0.27c-1.32-0.63-1.77-2.16-1.02-3.3c0.72-1.05 2.22-1.23 3.06-0.42c0.3 0.33 0.42 0.6 0.6 1.38c0.09 0.45 0.21 0.78 0.33 0.9c0.09 0.09 0.27 0.18 0.45 0.21c0.12 0 0.18 0 0.33-0.09c0.33-0.15 1.02-0.93 1.41-1.59c0.12-0.21 0.18-0.39 0.39-1.08c0.66-2.1 1.17-3.84 1.17-3.87c0 0-0.21 0.06-0.42 0.15c-0.51 0.15-1.2 0.33-1.68 0.42c-0.33 0.06-0.51 0.06-0.96 0.06c-0.66 0-0.84-0.03-1.32-0.27c-1.32-0.63-1.77-2.16-1.02-3.3c0.33-0.45 0.84-0.81 1.38-0.9z" fill="currentColor"/></svg>'
      '</button>',
    ], hclass='ve-tool-group'),
    # Bar lines
    CDiv([
      '<button type="button" class="ve-tool-btn" data-tool="bar" title="Bar line">'
      '<svg viewBox="0 0 8 24" width="8" height="20"><line x1="4" y1="2" x2="4" y2="22" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="bar-open" title="Open repeat |:">'
      '<svg viewBox="0 0 16 24" width="14" height="20"><line x1="4" y1="2" x2="4" y2="22" stroke="currentColor" stroke-width="1.5"/><circle cx="10" cy="9" r="1.5" fill="currentColor"/><circle cx="10" cy="15" r="1.5" fill="currentColor"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="bar-close" title="Close repeat :|">'
      '<svg viewBox="0 0 16 24" width="14" height="20"><circle cx="6" cy="9" r="1.5" fill="currentColor"/><circle cx="6" cy="15" r="1.5" fill="currentColor"/><line x1="12" y1="2" x2="12" y2="22" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
    ], hclass='ve-tool-group'),
    # Accidentals
    CDiv([
      '<button type="button" class="ve-tool-btn" data-tool="sharp" title="Sharp">&#9839;</button>',
      '<button type="button" class="ve-tool-btn ve-acc-icon" data-tool="flat" title="Flat">&#9837;</button>',
      '<button type="button" class="ve-tool-btn ve-acc-icon" data-tool="natural" title="Natural">&#9838;</button>',
    ], hclass='ve-tool-group'),
    # Tie / Slur
    CDiv([
      '<button type="button" class="ve-tool-btn" data-tool="beam" title="Beam: join or break beam grouping">'
      '<svg viewBox="0 0 24 20" width="20" height="16"><line x1="6" y1="12.5" x2="6" y2="7.5" stroke="currentColor" stroke-width="1.5"/><line x1="18" y1="12.5" x2="18" y2="7.5" stroke="currentColor" stroke-width="1.5"/><line x1="6" y1="12.5" x2="18" y2="12.5" stroke="currentColor" stroke-width="2.5"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="slur" title="Slur: phrasing arc across selected notes">'
      '<svg viewBox="0 0 24 16" width="20" height="14"><path d="M2,4 Q12,16 22,4" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>'
      '</button>',
      '<button type="button" class="ve-tool-btn" data-tool="grace" title="Grace note (acciaccatura)">'
      '<svg viewBox="0 0 20 28" width="16" height="22"><ellipse cx="8" cy="16" rx="3.5" ry="2.5" fill="currentColor" transform="rotate(-15,8,16)"/><line x1="11" y1="15" x2="11" y2="3" stroke="currentColor" stroke-width="1.5"/><path d="M11,3 Q13.5,5.5 15,9" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>'
      '</button>',
    ], hclass='ve-tool-group'),
    # Scissors (split note / break beam)
    CDiv([
      '<button type="button" class="ve-tool-btn" data-tool="scissors" title="Split note, rest, beam, or slur">'
      '<svg viewBox="0 0 24 24" width="18" height="18"><circle cx="7" cy="17" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="17" cy="17" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="9.1" y1="15.2" x2="17" y2="3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><line x1="14.9" y1="15.2" x2="7" y2="3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>'
      '</button>',
    ], hclass='ve-tool-group'),
  ], hclass='ve-toolbar', id='ve-toolbar')

  # Meter/unit fields (always visible)
  meter_unit_row = CDiv([
    CSpan([
      CText('Meter:', bold=1, hclass='edit-label'),
      CSelect(meter_options, current=obj.meter or '4/4', name='meter', id='field-meter'),
    ], hclass='inline-fields'),
    CSpan([
      CText('Unit:', bold=1, hclass='edit-label'),
      CSelect(unit_options, current=obj.unit or '1/8', name='unit', id='field-unit'),
    ], hclass='inline-fields'),
  ], hclass='field-row', style='margin-bottom:8px')

  # ABC textarea (hidden in visual mode, shown in abc mode)
  textarea_pane = CDiv([
    CTextArea(raw, name='raw_notes', id='raw-notes-textarea', rows=8, cols=40,
              hclass='notes-textarea', style='font-family:monospace; width:100%'),
  ], id='ve-textarea-pane', style='display:none')

  # Preview pane with overlay container for staff interaction
  # Property panel is inside the preview container so position:absolute works correctly
  preview_pane = CDiv([
    CDiv('', id='abcjs-preview', hclass='ve-staff-area'),
    CDiv('&#9881;', id='ve-prop-indicator', hclass='ve-prop-indicator', style='display:none'),
    CDiv([
      CDiv('', id='ve-prop-content'),
    ], hclass='ve-property-panel', id='ve-property-panel', style='display:none'),
  ], hclass='notes-preview-pane ve-preview-container', id='ve-preview-container')

  # Pitch label (follows ghost during drag)
  pitch_label = CDiv('', id='ve-pitch-label', hclass='ve-pitch-label', style='display:none')

  return [
    mode_toggle,
    meter_unit_row,
    toolbar,
    CDiv([
      textarea_pane,
      preview_pane,
    ], hclass='notes-layout'),
    pitch_label,
  ]

def _build_chord_tables(chord_parts, num_columns):
  """Build chord input tables for each part."""
  part_labels = 'ABCDEFGHIJ'
  items = []
  for p_idx, cp in enumerate(chord_parts):
    label = part_labels[p_idx] if p_idx < len(part_labels) else str(p_idx)
    repeat_attrs = dict(type='checkbox', name='repeat_%d' % p_idx, value='1')
    if cp['repeat']:
      repeat_attrs['checked'] = 'checked'

    part_rows_html = []
    for r_idx, row_cells in enumerate(cp['rows']):
      tds = []
      for c_idx, cell in enumerate(row_cells):
        field_name = 'chord_%d_%d_%d' % (p_idx, r_idx, c_idx)
        tds.append(CTD(CInput(type='text', name=field_name, value=cell,
                              size=max(6, len(cell) + 2))))
      # Add +/- measure and remove row buttons at end of row
      tds.append(CTD([
        '<button type="button" class="row-ctl-btn add-measure-btn" '
        'onclick="addMeasureToRow(this)" title="Add measure">+</button>',
        '<button type="button" class="row-ctl-btn remove-measure-btn" '
        'onclick="removeMeasureFromRow(this)" title="Remove measure">&minus;</button>',
        '<button type="button" class="row-ctl-btn remove-row-btn" '
        'onclick="removeRow(this)" title="Remove row">X</button>',
      ]))
      part_rows_html.append(CTR(tds))

    part_content = [
      CDiv([
        '<button type="button" class="part-remove-btn" onclick="removePart(this)" title="Remove part">X</button> ',
        CText('Part %s' % label, bold=1),
        ' &nbsp; Repeat: ',
        CInput(**repeat_attrs),
      ], hclass='part-header'),
      CTable(part_rows_html, width=None, hclass='edit-chords', style='margin-bottom:2px'),
      '<button type="button" class="add-btn" style="font-size:80%; padding:1px 6px; margin-bottom:8px" '
      'onclick="addRowToPart(this)">+ Row</button>',
    ]
    items.append(CDiv(part_content, hclass='part-wrapper', data_part=str(p_idx)))

  return items

def _chord_notation_guide():
  """Return the chord notation guide div."""
  return CDiv([
    CH("Chord Notation Reference", 3),
    CParagraph([
      "Chords A through G and H for German Bb. ", 
      CText("b", bold=1), "=flat, ", CText("#", bold=1), "=sharp, ",
      CText("+", bold=1), "=augmented, ", CText("m", bold=1), "=minor "
      "like: ", CText("Am  Bb  F#m  C+  Eb", italic=1),
      ". For 2+ chords in a measure, write them together like: ",
      CText("AmG F#mE DGA", italic=1),
    ]),
    CParagraph([
      "Add", CText("7", bold=1), ", ", CText("6", bold=1), ", or ",
      CText("9", bold=1), " extend chords. ",
      "", CText("dim", bold=1), "=diminished, ", CText("sup", bold=1), "=suspended "
      "like: ", CText("A7  Em6  Bbm7  C#dim  Csup9", italic=1),
    ]),
    CParagraph([
      "Use ", CText("-", bold=1), " to explicitely sustain chords. "
      "like: ", CText("G-D", italic=1), " (G two beats, D for one), ",
      CText("A--", italic=1), " (A for three beats).",
    ]),
    CParagraph([
      CText("1:", bold=1), " ", CText("2:", bold=1), " ", CText("3:", bold=1),
      " at line start for alternate endings. "
      "Or use / and () for alternative/optional chords, like: ",
      CText("A(G/B)", italic=1), ", but ", CText("1:", italic=1), " or ", CText("2:", italic=1),
      " endings are clearer. "
      "Including the new time signature, like: ",
      CText("7/8", italic=1), " or ", CText("9/8", italic=1), " for time signature change.",
    ]),
    CParagraph([
      "Header and footer notes for playing style, form, or anything unusual like: ",
      "\"Play the A part 3x\"", " and ",
      "\"B-part only has 7 bars!\""
    ]),
  ], style='padding-top:20px')

@app.route('/tune/<tune>/save', methods=['POST'])
def tune_save(tune):
  if not HasCapability(kCapEditTunes):
    return redirect('/authorize/tune/%s/edit' % tune, code=303)

  obj = utils.CTune(tune)
  try:
    obj.ReadDatabase()
  except SystemExit:
    return redirect('/tune/%s' % tune, code=303)

  # Update all fields from form
  obj.title = request.form.get('title', obj.title or '').strip()
  obj.key = request.form.get('key', obj.key or '').strip()
  obj.meter = request.form.get('meter', obj.meter or '').strip()
  obj.unit = request.form.get('unit', obj.unit or '').strip()
  obj.author = request.form.get('author', '').strip() or None
  obj.origin = request.form.get('origin', '').strip() or None
  obj.structure = request.form.get('structure', '').strip() or None
  obj.ref = request.form.get('ref', '').strip() or None
  obj.history = request.form.get('history', '').strip() or None

  # Collect tune types from checkboxes
  types = []
  for sname, stitle, slabel in utils.kSections:
    if sname == 'incomplete':
      continue
    if request.form.get('klass_%s' % sname):
      types.append(sname)
  if types:
    obj.klass = ','.join(types)
  else:
    obj.klass = 'other'

  # Collect URLs
  urls = []
  for key in sorted(request.form.keys()):
    if key.startswith('url_'):
      val = request.form.get(key, '').strip()
      if val:
        urls.append(val)
  obj.url = '\n'.join(urls) if urls else None

  # Notes (ABC)
  raw_notes = request.form.get('raw_notes', '')
  if raw_notes.strip():
    obj.raw_notes = raw_notes.rstrip('\n') + '\n'
  else:
    obj.raw_notes = ''

  # Reconstruct chords from structured form
  obj.chords = _ReconstructChords(request.form)

  # Write the full spec file and invalidate caches
  obj.WriteSpec()
  obj.InvalidateCaches()

  return redirect('/tune/%s' % tune, code=303)

def _ReconstructChords(form):
  """Reconstruct formatted chord text from the structured edit form fields."""
  num_parts = int(form.get('num_parts', 0))
  header_text = form.get('chord_header', '').strip()
  footer_text = form.get('chord_footer', '').strip()

  if num_parts == 0:
    return ''

  # Read all part data — each row can have a different number of columns
  line_data = []
  max_columns = 0
  for p in range(num_parts):
    num_rows = int(form.get('rows_in_part_%d' % p, 2))
    has_repeat = form.get('repeat_%d' % p) == '1'

    for r in range(num_rows):
      # Collect all columns present for this row
      chords = []
      c = 0
      while True:
        val = form.get('chord_%d_%d_%d' % (p, r, c), None)
        if val is None:
          break
        chords.append(ValidateChord(val.strip()))
        c += 1
      if not chords:
        # Fallback: at least one empty cell
        chords = ['']
      if len(chords) > max_columns:
        max_columns = len(chords)
      is_first_row = (r == 0)
      is_last_row = (r == num_rows - 1)
      has_open = has_repeat and is_first_row
      has_close = has_repeat and is_last_row
      line_data.append((has_open, has_close, chords))

  # Check if there's any non-empty chord data
  has_any_chords = False
  for _, _, chords in line_data:
    for c in chords:
      if c:
        has_any_chords = True
        break
    if has_any_chords:
      break
  if not has_any_chords and not header_text and not footer_text:
    return ''

  # Compute max width per column position
  col_widths = [0] * max_columns
  for _, _, chords in line_data:
    for i, c in enumerate(chords):
      col_widths[i] = max(col_widths[i], len(c))

  # Build formatted lines
  any_close = any(d[1] for d in line_data)
  result_lines = []

  if header_text:
    result_lines.append(header_text)

  for has_open, has_close, chords in line_data:
    if has_open:
      prefix = '|:'
    else:
      prefix = '  '

    padded = [c.ljust(col_widths[i]) if i < len(col_widths) else c for i, c in enumerate(chords)]
    line = prefix + ' ' + ' | '.join(padded)

    if has_close:
      line += ' :|'
    elif any_close:
      line += '  |'
    else:
      line += ' |'

    result_lines.append(line)

  if footer_text:
    result_lines.append(footer_text)

  return '\n'.join(result_lines)

@app.route('/check-url')
def check_url():
  """Check if a URL is accessible. Uses curl to avoid Python 2.7 SSL issues."""
  import json as json_module
  import subprocess
  url = request.args.get('url', '')
  if not url:
    return json_module.dumps({'ok': False, 'error': 'No URL provided'}), 400, {'Content-Type': 'application/json'}
  try:
    result = subprocess.Popen(
      ['curl', '-sS', '-o', '/dev/null', '-w', '%{http_code}', '-L',
       '--http1.1', '--max-time', '10',
       '-A', 'Mozilla/5.0 (compatible; TuneJam link checker)',
       url],
      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = result.communicate()
    code_str = stdout.strip()
    if result.returncode != 0:
      error = stderr.strip() if stderr.strip() else 'Connection failed'
      return json_module.dumps({'ok': False, 'error': error}), 200, {'Content-Type': 'application/json'}
    code = int(code_str) if code_str.isdigit() else 0
    if code >= 400:
      return json_module.dumps({'ok': False, 'error': 'HTTP %d' % code}), 200, {'Content-Type': 'application/json'}
    return json_module.dumps({'ok': True}), 200, {'Content-Type': 'application/json'}
  except Exception as e:
    return json_module.dumps({'ok': False, 'error': str(e)}), 200, {'Content-Type': 'application/json'}

@app.route('/png/<tune>')
def png(tune):
  tune = utils.CTune(tune)
  png_file = tune.MakeNotesPNGFile(density=600)
  if png_file is None or not os.path.exists(png_file):
    abort(404)
  return send_file(png_file, mimetype='image/png')

@app.route('/sheet/<tune>')
def sheet(tune):
  tune = utils.CTune(tune)
  png_file = tune.MakeSheetMusicPNGFile(density=600)
  if png_file is None or not os.path.exists(png_file):
    abort(404)
  return send_file(png_file, mimetype='image/png')

@app.route('/sheet/view/<tunes>')
def sheet_view(tunes):
  tunes = tunes.split('&')
  parts = []
  for tune in tunes:
    parts.append(CDiv(CImage(src='/sheet/%s' % tune, width="100%")))
  return PageWrapper(parts, None)

@app.route('/sheet/print/<tunes>')
def sheet_print(tunes):
  import sheetbook
  tunes = tunes.split('&')
  book = sheetbook.CSheetBook(tunes)
  pdf_file = book.GeneratePDF(include_index=len(tunes) > 1, generate=True)
  return send_file(pdf_file, mimetype='application/pdf')

@app.route('/sheet/abc/<tune>')
def sheet_abc(tune):
  tune = utils.CTune(tune)
  tune.ReadDatabase()
  sheet = tune.ReadSheetMusic().replace('<', '&lt;').replace('>', '&gt;')
  
  parts = tune.GetActionIcons(icons=['play']) + [
    CH(tune.title, 2),
    CParagraph("This is the ABC encoding of this tune.  It can be edited and played as sound with "
               "tools listed at <a href='https://abcnotation.com/software'>https://abcnotation.com/software</a> "
               "(such as <a href='https://sourceforge.net/projects/easyabc/'>EasyABC</a>)."),
    CBreak(), 
    CText('<pre>%s</pre>' % sheet), 
    CBreak(2),
    CImage(src='/sheet/%s' % tune.name, width='100%'),
    CBreak(), 
  ]

  return PageWrapper(parts, 'local')
  
@app.route('/sheet/all')
def sheet_all():
  import sheetbook
  tunes = utils.GetTuneIndex(True)
  
  titles = []
  sections = tunes.keys()
  all_tunes = set()
  for section in sections:
    for title, tune in tunes[section]:
      all_tunes.add((title, tune))
      
  tunes = []
  for title, tune in sorted(all_tunes):
    obj = utils.CTune(tune)
    obj.ReadDatabase()
    notes = obj.ReadSheetMusic()
    if not notes:
      continue
    tunes.append(tune)
    
  book = sheetbook.CSheetBook(tunes, "Sheet Music for Locally Written Tunes", "Cambridge NY")
    
  pdf_file = book.GeneratePDF(include_index=len(tunes) > 1)
  return send_file(pdf_file, mimetype='application/pdf')

def get_all_books():
  import allbook
  import flipbook
  retval = [
    allbook.CAllBook(metadata_only=True),
    allbook.CAllBookBySection(metadata_only=True),
    allbook.CAllBookByTime(metadata_only=True),
    None,
    flipbook.CFlipBook(metadata_only=True),
    flipbook.CFlipBookByTime(metadata_only=True),
    None,
  ]
  custom_books = []
  files = os.listdir(utils.kDatabaseDir)
  for fn in files:
    if not fn.endswith('.book'):
      continue
    book = fn[:-len('.book')]
    custom_books.append(utils.CBook(book, metadata_only=True))
    
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
      if os.path.exists(os.path.join(utils.kCacheLoc, book.name+'.lock')):
        url = None
        title = book.subtitle + ' - temporarily unavailable - rebuilding '
        img = CImage(src='/image/rebuilding.gif')
        refresh = 5
      else:
        url = '/print/%s' % book.url
        img = ''
        title = book.subtitle
      parts.extend([
        CText('&#9834; '),
        CText(title, href=url),
        img,
        CBreak(),
      ])

    parts.extend([
      CBreak(),
      CText('&#9834; '),
      CText("Sheet Music for Local Tunes", href='/sheet/all'),
      CDiv(style='clear:both'),
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
  
  elif format == 'event':
    import sessbook
    event = utils.CEvent(bookname)
    event.ReadEvent()
    book = sessbook.CEventBook(event)
    target, up_to_date = book._GetCacheFile('.pdf')
    fn = os.path.join(utils.kEventsLoc, event.name+'.evt')
    if utils.IsFileNewer(fn, target) and os.path.exists(target):
      os.unlink(target)
    pdf = book.GeneratePDF(type_in_header=False, include_index=True, generate=True)
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

@app.route('/image/<path:image>')
def image(image):
  img_file = os.path.join(utils.kImageDir, image)
  if image.endswith('.jpeg') or image.endswith('.jpg'):
    mimetype = 'image/jpeg'
  else:
    mimetype = 'image/png'
  return send_file(img_file, mimetype=mimetype)
  
@app.route('/js/<path:filename>')
def js(filename):
  js_file = os.path.join(utils.kJSDir, filename)
  if filename.endswith('.js'):
    return send_file(js_file, mimetype='text/javascript')
  else:
    return send_file(js_file, mimetype='text/css')
  
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
body {
background-color: #e8e6e0;
}
input[type="submit"], input[type="button"], input[type="reset"] {
padding: 4px 14px;
background-color: #3a6a3a;
color: #ffffff;
border: 1px solid #1a3a1a;
border-radius: 3px;
cursor: pointer;
font-size: 95%;
}
input[type="submit"]:hover, input[type="button"]:hover, input[type="reset"]:hover {
background-color: #4a7a4a;
}
select {
padding: 2px 4px;
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
margin:-12px -12px 0 -12px;
background:#2a4a2a;
}
#header img {
width:100%;
height:auto;
display:block;
}
#header img.fadein {
opacity:0;
transition:opacity 0.4s ease-in;
}
#header img.loaded {
opacity:1;
}
#main-menu {
background-color: #e8f0e8;
padding: 8px 12px;
border-bottom: 1px solid #88aa88;
margin: 0 -12px 12px;
}
.menu-item {
text-decoration:none;
color:#005511;
padding-bottom:0.5em;
}
.menu-item:hover, .menu-item-current:hover {
color:#993333;
text-decoration:none;
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
color:#004400;
}
h1.tune-title {
clear:both;
position:relative;
font-size:min(3.5vw, 38px);
color:#000000;
padding-right:20%;
}
h1.long-tune-title {
clear:both;
position:relative;
font-size:min(2.6vw, 28px);
color:#000000;
padding-right:20%;
}
h1.extra-long-tune-title {
clear:both;
position:relative;
font-size:min(2.5vw, 27px);
color:#000000;
padding-right:20%;
}
span.tune-type {
font-size:max(70%, 14px);
position:absolute;
right:calc(10px + clamp(18px, 3.1vw, 34px) + 10px);
top:2px;
}
span.tune-type-two-icons {
font-size:max(70%, 14px);
position:absolute;
right:calc(10px + 2 * (clamp(18px, 3.1vw, 34px) + 10px));
top:2px;
}
span.tune-type-three-icons {
font-size:max(70%, 14px);
position:absolute;
right:calc(10px + 3 * (clamp(18px, 3.1vw, 34px) + 10px));
top:2px;
}
span.tune-type-four-icons {
font-size:max(70%, 14px);
position:absolute;
right:calc(10px + 4 * (clamp(18px, 3.1vw, 34px) + 10px));
top:2px;
}
h2 {
padding-top:0.7em;
padding-bottom:0.5em;
color:#004400;
}
h2.index-section {
padding-top:1.0em;
padding-bottom:0.36em;
font-size:166%;
}
.index-group, .index-group * {
line-height:166%;
}
a {
outline-style:none;
color:#005511;
}
a:hover {
color:#993333;
text-decoration:underline;
}
#body {
position:relative;
margin:12px auto;
padding:0 12px;
max-width:1079px;
background-color: #ffffff;
}
#footer {
clear:both;
background-color: #e8f0e8;
padding: 14px 12px;
margin: 0 -12px 0;
border-top: 1px solid #88aa88;
font-size: 85%;
color: #556655;
}
.footer-auth {
float:right;
margin-top:-4px;
}
.footer-auth b, .footer-auth span {
font-size:100%;
}
.footer-logout {
padding:1px 6px;
font-size:75%;
background-color:#3a6a3a;
color:#ffffff;
border:1px solid #1a3a1a;
border-radius:3px;
cursor:pointer;
}
.footer-logout:hover {
background-color:#4a7a4a;
}
@media only screen and (max-width: 500px) {
.footer-auth {
float:none;
display:block;
margin-top:8px;
}
}
div.tune-break {
clear:both;
height:20px;
}
img.action-icon-1 {
position:absolute;
right:10px;
top:5px;
width:clamp(18px, 3.1vw, 34px);
height:clamp(18px, 3.1vw, 34px);
}
img.action-icon-2 {
position:absolute;
right:calc(10px + clamp(18px, 3.1vw, 34px) + 10px);
top:5px;
width:clamp(18px, 3.1vw, 34px);
height:clamp(18px, 3.1vw, 34px);
}
img.action-icon-3 {
position:absolute;
right:calc(10px + 2 * (clamp(18px, 3.1vw, 34px) + 10px));
top:5px;
width:clamp(18px, 3.1vw, 34px);
height:clamp(18px, 3.1vw, 34px);
}
img.action-icon-4 {
position:absolute;
right:calc(10px + 3 * (clamp(18px, 3.1vw, 34px) + 10px));
top:5px;
width:clamp(18px, 3.1vw, 34px);
height:clamp(18px, 3.1vw, 34px);
}
img.notes {
position:relative;
left:-0.1in;
top:0in;
width:48%;
margin-top:20px;
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
font-size:min(3vw, 26px);
border:0px;  /* For Chrome and Safari */
border-left:2px solid #000;
border-right:2px solid #000;
margin-left:4px;
margin-top:50px;
margin-bottom:15px;
float:right;
width:48%;
table-layout:fixed;
}
table.chords td.first {
width:1.2em;
}
table.chords td.last {
width:1.2em;
}
div.chord-group {
float:right;
width:48%;
margin-top:70px;
margin-bottom:15px;
}
div.chord-group table.chords {
float:none;
width:100%;
margin-top:0;
margin-bottom:0;
margin-left:0;
}
div.chord-group-only {
clear:both;
float:left;
width:95%;
margin-top:2vw;
font-size:min(5.0vw, 54px);
}
div.chord-group-only table.chords-only {
float:none;
width:100%;
margin-top:0;
}
table.chords-only {
clear:both;
left:0in;
right:none;
font-size:min(5.0vw, 54px);
width:95%;
float:left;
margin-top:2vw;
}
tr.even {
background:#e8f0e8;
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
#body {
margin:5px;
padding:0 5px;
overflow-x:hidden;
}
#main-menu {
margin:0 -5px 12px;
}
#footer {
margin:0 -5px 0;
}
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
font-size:4.5vw;
width:calc(100% - 5px);
max-width:none;
table-layout:fixed;
float:left;
}
table.chords td.first {
width:1.2em;
}
table.chords td.last {
width:1.2em;
}
div.chord-group {
float:left;
width:calc(100% - 5px);
margin-top:5px;
}
div.chord-note {
font-size:4vw !important;
width:auto !important;
min-width:0 !important;
}
}
img.eye-candy {
height:auto;
}
img.eye-candy.fadein {
opacity:0;
transition:opacity 0.4s ease-in;
}
img.eye-candy.loaded {
opacity:1;
border:3px solid white;
outline:2px solid black;
}

@media only screen and (max-width: 640px) {
img.eye-candy {
display:none;
}
.section-index img.eye-candy {
display:block;
}
}
.section-index img.eye-candy {
width: min(41%, calc(100% - 510px)) !important;
}
.section-index h2 ~ a, .section-index h2 ~ span {
line-height: 200%;
}
@media only screen and (max-width: 735px) {
.section-index img.eye-candy {
display:none !important;
}
}

#audio-player {
display:none;
position:fixed;
bottom:0;
left:0;
width:100%;
z-index:1000;
background:#2a4a2a;
color:#e0e8e0;
font-family:'Trebuchet MS', Trebuchet, Arial, sans-serif;
font-size:14px;
align-items:center;
padding:8px 12px;
box-sizing:border-box;
box-shadow:0 -2px 8px rgba(0,0,0,0.3);
}
#audio-player > * {
margin-left:10px;
}
#audio-player > *:first-child {
margin-left:0;
}
#audio-player button {
background:none;
border:none;
color:#e0e8e0;
cursor:pointer;
font-size:18px;
padding:0 4px;
line-height:1;
}
#audio-player button:hover {
color:#ffffff;
}
#audio-player .ap-title {
flex:0 1 auto;
white-space:nowrap;
overflow:hidden;
text-overflow:ellipsis;
min-width:60px;
max-width:300px;
font-weight:bold;
}
#audio-player .ap-progress-track {
flex:1 1 auto;
height:6px;
background:#1a3a1a;
border-radius:3px;
cursor:pointer;
min-width:60px;
}
#audio-player .ap-progress-fill {
height:100%;
background:#6cb06c;
border-radius:3px;
width:0%;
pointer-events:none;
}
#audio-player .ap-time {
white-space:nowrap;
font-size:12px;
min-width:80px;
text-align:right;
}
#audio-player .ap-speed {
background:#1a3a1a;
color:#e0e8e0;
font-family:'Trebuchet MS', Trebuchet, Arial, sans-serif;
font-size:12px;
border:1px solid #6cb06c;
border-radius:3px;
padding:2px 4px;
cursor:pointer;
}
#audio-player .ap-close {
font-size:20px;
}
@media only screen and (max-width: 500px) {
#audio-player .ap-title {
max-width:120px;
}
#audio-player .ap-time {
display:none;
}
}

/* Login popup overlay */
#login-overlay {
position:fixed;
top:0; left:0; right:0; bottom:0;
background:rgba(0,0,0,0.5);
z-index:2000;
display:flex;
align-items:center;
justify-content:center;
}
#login-popup {
background:#ffffff;
border-radius:8px;
max-width:400px;
width:90%;
padding:30px;
box-shadow:0 4px 20px rgba(0,0,0,0.3);
position:relative;
}
#login-close {
position:absolute;
top:10px; right:14px;
background:none;
border:none;
font-size:24px;
cursor:pointer;
color:#666;
padding:0;
line-height:1;
}
#login-close:hover {
color:#333;
}
#login-popup h2 {
margin:0 0 10px 0;
padding:0;
color:#004400;
}
.login-instructions {
font-size:100%;
color:#555;
margin-bottom:15px;
}
#login-email {
width:100%;
padding:8px 10px;
font-size:100%;
border:1px solid #ccc;
border-radius:4px;
box-sizing:border-box;
margin-bottom:12px;
}
#login-submit {
padding:8px 20px;
background-color:#3a6a3a;
color:#ffffff;
border:1px solid #1a3a1a;
border-radius:4px;
cursor:pointer;
font-size:100%;
width:100%;
}
#login-submit:hover {
background-color:#4a7a4a;
}
#login-message {
margin-top:12px;
font-size:95%;
min-height:1.4em;
}
#login-message.error {
color:#cc0000;
}
#login-message.success {
color:#006600;
}
button.login-trigger {
padding:4px 14px;
background-color:#3a6a3a;
color:#ffffff;
border:1px solid #1a3a1a;
border-radius:3px;
cursor:pointer;
font-size:95%;
}
button.login-trigger:hover {
background-color:#4a7a4a;
}
a.green-button {
display:inline-block;
padding:4px 14px;
background-color:#3a6a3a;
color:#ffffff;
border:1px solid #1a3a1a;
border-radius:3px;
font-size:95%;
text-decoration:none;
}
a.green-button:hover {
background-color:#4a7a4a;
color:#ffffff;
text-decoration:none;
}
.user-email-display {
font-style:italic;
color:#666;
font-size:90%;
}

/* Tune editor styles */
.edit-form label {
display:inline-block;
width:100px;
font-weight:bold;
vertical-align:top;
padding-top:4px;
}
.edit-form .field-row {
margin-bottom:8px;
}
.edit-form .title-row {
display:flex;
align-items:center;
gap:10px;
margin-bottom:8px;
}
.edit-form .title-field {
flex:1;
min-width:0;
display:flex;
align-items:center;
gap:6px;
}
.edit-form .title-field .title-input {
flex:1;
min-width:0;
}
.edit-form .key-field {
flex:0 0 auto;
white-space:nowrap;
}
.edit-form .key-editor-container {
position:relative;
display:inline-block;
}
.edit-form .key-display-btn {
font-size:100%;
padding:3px 8px;
border:1px solid #999;
border-radius:3px;
background:#fff;
cursor:pointer;
min-width:80px;
text-align:left;
}
.edit-form .key-display-btn:hover {
border-color:#3a6a3a;
}
.edit-form .key-editor-dropdown {
display:none;
position:absolute;
top:100%;
left:0;
z-index:100;
background:#fff;
border:1px solid #999;
border-radius:3px;
box-shadow:0 2px 8px rgba(0,0,0,0.15);
padding:8px;
min-width:200px;
}
.edit-form .key-editor-dropdown.open {
display:block;
}
.edit-form .key-editor-row {
margin-bottom:4px;
white-space:nowrap;
}
.edit-form .key-editor-row select {
font-size:95%;
padding:2px 4px;
margin-right:4px;
}
.edit-form .type-field {
flex:0 0 auto;
white-space:nowrap;
}
.edit-form input[type="text"],
.edit-form textarea,
.edit-form select {
font-size:100%;
padding:3px 6px;
border:1px solid #999;
border-radius:3px;
}
.edit-form input[type="text"]:focus,
.edit-form textarea:focus,
.edit-form select:focus {
border-color:#3a6a3a;
outline:none;
}
.edit-form .wide-input {
width:60%;
min-width:280px;
}
.edit-form .medium-input {
width:120px;
}
.edit-form textarea.description-field {
width:80%;
min-width:280px;
min-height:100px;
}
.edit-form .type-menu-container {
display:inline-block;
position:relative;
}
.edit-form .type-menu-btn {
padding:3px 10px;
font-size:100%;
border:1px solid #999;
border-radius:3px;
background:#fff;
cursor:pointer;
min-width:160px;
text-align:left;
}
.edit-form .type-menu-btn:hover {
border-color:#3a6a3a;
}
.edit-form .type-menu-dropdown {
display:none;
position:absolute;
top:100%;
right:0;
z-index:100;
background:#fff;
border:1px solid #999;
border-radius:3px;
box-shadow:0 2px 8px rgba(0,0,0,0.15);
padding:6px 8px;
column-count:2;
column-gap:8px;
}
.edit-form .type-menu-dropdown.open {
display:block;
}
.edit-form .type-menu-item {
display:block;
padding:3px 8px;
cursor:pointer;
font-weight:normal;
white-space:nowrap;
break-inside:avoid;
}
.edit-form .type-menu-item:hover {
background:#e8f0e8;
}
.edit-form .type-menu-item input {
margin-right:6px;
}
.edit-form .section-header {
font-weight:bold;
font-size:110%;
margin-top:16px;
margin-bottom:8px;
border-bottom:1px solid #ccc;
padding-bottom:4px;
}
.edit-form .url-row {
margin-bottom:4px;
}
.edit-form .url-row input {
width:55%;
min-width:250px;
}
.edit-form .url-test-btn {
background:#3a6a3a;
color:white;
border:1px solid #1a3a1a;
border-radius:3px;
padding:2px 8px;
cursor:pointer;
margin-left:4px;
font-size:90%;
}
.edit-form .url-test-btn:hover {
background:#4a7a4a;
}
.edit-form .url-test-btn:disabled {
background:#999;
cursor:default;
}
.edit-form .url-remove-btn {
background:#cc3333;
color:white;
border:1px solid #993333;
border-radius:3px;
padding:2px 8px;
cursor:pointer;
margin-left:4px;
font-size:90%;
}
.edit-form .url-remove-btn:hover {
background:#dd4444;
}
.edit-form .add-btn {
background:#3a6a3a;
color:white;
border:1px solid #1a3a1a;
border-radius:3px;
padding:3px 10px;
cursor:pointer;
font-size:90%;
margin-top:4px;
}
.edit-form .add-btn:hover {
background:#4a7a4a;
}
.edit-form .notes-layout {
display:flex;
gap:10px;
flex-wrap:wrap;
}
.edit-form .notes-editor-pane {
flex:1;
min-width:300px;
}
.edit-form .notes-editor-pane textarea {
font-family:monospace;
font-size:95%;
}
.edit-form .notes-preview-pane {
flex:1;
min-width:300px;
position:relative;
}
.edit-form .chord-layout {
display:flex;
gap:10px;
flex-wrap:wrap;
}
.edit-form .chord-editor-pane {
flex:1;
min-width:300px;
}
.edit-form .chord-preview-pane {
flex:1;
min-width:300px;
text-align:right;
}
.edit-form .chord-preview-pane table.chords-preview {
border:0px;
border-left:2px solid #000;
border-right:2px solid #000;
border-collapse:collapse;
margin-left:auto;
table-layout:fixed;
font-size:min(3vw, 26px);
}
.edit-form .chord-preview-pane table.chords-preview td {
padding-right:1.0em;
line-height:120%;
}
.edit-form .chord-preview-pane table.chords-preview td.last-chord {
padding-right:0.5em;
}
.edit-form .chord-preview-pane table.chords-preview td.last {
text-align:right;
padding-right:3px;
width:1.2em;
}
.edit-form .chord-preview-pane table.chords-preview td.first {
padding-left:3px;
padding-right:0.5em;
width:1.2em;
}
.edit-form .chord-preview-pane tr.even {
background:#e8f0e8;
}
.edit-form .chord-preview-pane .chord-note {
font-style:italic;
text-align:left;
margin:4px 0;
font-size:min(3vw, 26px);
}
.edit-form .chord-structure-controls {
margin:8px 0;
}
.edit-form .chord-structure-controls button {
margin-right:8px;
}
.edit-form .part-wrapper {
margin-bottom:4px;
}
.edit-form .part-header {
font-weight:bold;
padding:4px 0;
margin-top:8px;
background:#e8f0e8;
padding-left:6px;
width:50%;
}
.edit-form .part-remove-btn {
background:#cc3333;
color:white;
border:1px solid #993333;
border-radius:3px;
font-size:80%;
padding:1px 5px;
cursor:pointer;
font-weight:bold;
}
.edit-form .part-remove-btn:hover {
background:#aa1111;
}
.edit-form table.edit-chords {
border-collapse:collapse;
margin:4px 0 2px 0;
}
.edit-form table.edit-chords td {
padding:2px 4px;
}
.edit-form table.edit-chords input[type="text"] {
width:70px;
font-size:100%;
padding:2px 4px;
}
.edit-form .row-ctl-btn {
font-size:80%;
padding:1px 5px;
margin:0 1px;
border:1px solid #999;
border-radius:3px;
cursor:pointer;
background:#f0f0f0;
font-weight:bold;
}
.edit-form .add-measure-btn {
color:#3a6a3a;
border-color:#3a6a3a;
}
.edit-form .remove-measure-btn {
color:#cc3333;
border-color:#993333;
}
.edit-form .remove-row-btn {
color:white;
background:#cc3333;
border-color:#993333;
margin-left:4px;
}
.edit-form .inline-fields {
display:inline-block;
margin-right:20px;
}
.edit-form .inline-fields label {
width:auto;
margin-right:6px;
}

/* Visual Editor - Mode Toggle */
.edit-form .ve-mode-toggle {
margin-bottom:8px;
display:flex;
gap:0;
}
.edit-form .ve-mode-btn {
padding:5px 14px;
border:1px solid #999;
background:#f0f0f0;
color:#333;
cursor:pointer;
font-size:90%;
font-weight:bold;
}
.edit-form .ve-mode-btn:first-child {
border-radius:3px 0 0 3px;
}
.edit-form .ve-mode-btn:last-child {
border-radius:0 3px 3px 0;
border-left:none;
}
.edit-form .ve-mode-btn.ve-mode-active {
background:#3a6a3a;
color:white;
border-color:#1a3a1a;
}

/* Visual Editor - Toolbar Palette */
.edit-form .ve-toolbar {
display:flex;
flex-wrap:wrap;
align-items:center;
gap:4px;
padding:6px 8px;
background:#f5f5f0;
border:1px solid #ccc;
border-radius:4px;
margin-bottom:8px;
}
.edit-form .ve-tool-group {
display:flex;
gap:2px;
align-items:center;
padding-right:6px;
border-right:1px solid #ddd;
}
.edit-form .ve-tool-group:last-child {
border-right:none;
padding-right:0;
}
.edit-form .ve-tool-btn {
display:inline-flex;
align-items:center;
justify-content:center;
min-width:28px;
min-height:28px;
padding:2px 4px;
border:1px solid #bbb;
border-radius:3px;
background:white;
cursor:pointer;
color:#333;
font-size:14px;
line-height:1;
touch-action:none;
user-select:none;
-webkit-user-select:none;
}
.edit-form .ve-tool-btn:hover {
background:#e8f0e8;
border-color:#3a6a3a;
}
.edit-form .ve-tool-btn.ve-tool-active {
background:#3a6a3a;
color:white;
border-color:#1a3a1a;
}
.edit-form .ve-tool-btn.ve-tool-active svg {
color:white;
}
.edit-form .ve-tool-btn svg {
display:block;
}
.edit-form .ve-tool-btn.ve-acc-icon {
font-size:19px;
}
.ve-property-panel .ve-prop-btn.ve-acc-icon {
font-size:16px;
}
.ve-rubber-band {
position:fixed;
border:1px dashed #4A90D9;
background:rgba(74, 144, 217, 0.1);
pointer-events:none;
z-index:1000;
}
.ve-scissors-active #ve-preview-container {
cursor:crosshair;
}
.ve-scissors-active #ve-preview-container svg {
cursor:crosshair;
}
.edit-form .ve-tool-del {
font-size:11px;
font-weight:bold;
}

/* Visual Editor - Preview Container & Staff */
.edit-form .ve-staff-area {
cursor:crosshair;
}
.ve-part-container {
margin-bottom:4px;
}
.ve-part-label {
font-size:12px;
font-weight:bold;
color:#3a6a3a;
padding:2px 6px;
background:#f0f4f0;
border:1px solid #ddd;
border-bottom:none;
border-radius:3px 3px 0 0;
display:inline-flex;
align-items:center;
gap:4px;
cursor:grab;
user-select:none;
-webkit-user-select:none;
touch-action:none;
}
.ve-part-label-remove {
font-size:14px;
font-weight:bold;
padding:0 3px;
border:none;
background:none;
color:#993333;
cursor:pointer;
line-height:1;
}
.ve-part-label-remove:hover {
color:#cc0000;
}
.ve-add-part-btn {
font-size:12px;
padding:3px 10px;
border:1px solid #3a6a3a;
border-radius:3px;
background:#e8f0e8;
color:#3a6a3a;
cursor:pointer;
font-weight:bold;
margin-top:4px;
display:inline-block;
}
.ve-add-part-btn:hover {
background:#d0e0d0;
}
.ve-part-render {
border:1px solid #ddd;
border-radius:0 3px 3px 3px;
}
.ve-part-render svg {
max-width:100%;
display:block;
}
.edit-form .ve-staff-area svg {
max-width:100%;
display:block;
}

/* Visual Editor - Ghost element during drag */
.ve-drag-ghost {
position:fixed;
pointer-events:none;
opacity:0.6;
z-index:1000;
background:rgba(58,106,58,0.1);
border:1px solid #3a6a3a;
border-radius:3px;
padding:2px;
}

/* Visual Editor - Pitch label */
.ve-pitch-label {
position:fixed;
pointer-events:none;
z-index:1001;
background:rgba(0,0,0,0.8);
color:white;
font-size:11px;
padding:1px 5px;
border-radius:3px;
white-space:nowrap;
font-family:monospace;
}

/* Visual Editor - Insertion marker */
.ve-insertion-marker {
stroke:#cc3333;
stroke-width:1.5;
stroke-dasharray:4,3;
pointer-events:none;
}

/* Visual Editor - Selection */
.ve-selected .abcjs-note,
.ve-selected .abcjs-rest,
.ve-selected .abcjs-bar {
fill:#cc3333 !important;
stroke:#cc3333 !important;
}
#ve-preview-container .abcjs-note,
#ve-preview-container .abcjs-rest {
cursor:pointer;
}
.ve-bar-hitarea,
.ve-beam-hitarea {
pointer-events:all;
fill:transparent !important;
stroke:none !important;
cursor:pointer;
}
.ve-note-highlight,
.ve-note-highlight * {
fill:#cc3333 !important;
stroke:#cc3333 !important;
stroke-width:1.5 !important;
}
.ve-note-highlight path[class*="abcjs-tie"],
.ve-note-highlight path[class*="abcjs-slur"] {
fill:none !important;
stroke:#cc3333 !important;
}

/* Visual Editor - Property Indicator */
.ve-prop-indicator {
position:absolute;
z-index:199;
background:#f0f0f0;
border:1px solid #999;
border-radius:3px;
cursor:pointer;
font-size:14px;
line-height:20px;
width:20px;
height:20px;
text-align:center;
color:#555;
user-select:none;
}
.ve-prop-indicator:hover {
background:#e0e0e0;
border-color:#666;
color:#333;
}

/* Visual Editor - Property Panel */
.edit-form .ve-property-panel {
position:absolute;
z-index:200;
background:white;
border:1px solid #999;
border-radius:4px;
box-shadow:0 2px 8px rgba(0,0,0,0.2);
padding:6px 8px;
min-width:160px;
}
.ve-prop-header {
display:flex;
justify-content:flex-end;
margin-bottom:2px;
}
.ve-prop-close {
background:none;
border:none;
cursor:pointer;
font-size:20px;
line-height:16px;
color:#555;
padding:0 3px;
font-weight:bold;
}
.ve-prop-close:hover {
color:#cc3333;
}
.ve-property-panel .ve-prop-row {
display:flex;
gap:3px;
margin-bottom:4px;
align-items:center;
flex-wrap:wrap;
}
.ve-property-panel .ve-prop-row:last-child {
margin-bottom:0;
}
.ve-property-panel .ve-prop-label {
font-size:11px;
font-weight:bold;
color:#666;
min-width:40px;
}
.ve-property-panel .ve-prop-btn {
padding:2px 6px;
border:1px solid #bbb;
border-radius:3px;
background:#f8f8f8;
cursor:pointer;
font-size:12px;
min-width:24px;
text-align:center;
}
.ve-property-panel .ve-prop-btn:hover {
background:#e8f0e8;
}
.ve-property-panel .ve-prop-btn.ve-prop-active {
background:#3a6a3a;
color:white;
border-color:#1a3a1a;
}

/* Visual Editor - Part Drop Indicator (for drag reorder) */
.ve-part-drop-indicator {
height:3px;
background:#3a6a3a;
border-radius:2px;
margin:2px 0;
}

@media (max-width: 489px) {
.edit-form label {
width:80px;
font-size:95%;
}
.edit-form .wide-input,
.edit-form textarea.description-field,
.edit-form .url-row input {
width:90%;
min-width:0;
}
.edit-form table.edit-chords input[type="text"] {
width:50px;
}
}
@media (max-width: 700px) {
.edit-form .chord-preview-pane {
text-align:left;
}
.edit-form .chord-preview-pane table.chords-preview {
margin-left:0;
}
.edit-form .chord-preview-pane .chord-note {
text-align:left;
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
img.action-icon {
display:none;
}
#audio-player {
display:none !important;
}
#login-overlay {
display:none !important;
}
.footer-auth {
display:none !important;
}
    """
  return Response(css, mimetype='text/css')

@app.route('/events')
@app.route('/events/delete/<delete>')
@app.route('/events/undelete/<undelete>')
def events(delete=None, undelete=None):

  editor = HasCapability(kCapManageEvents)
   
  if delete and editor:
    utils.DeleteEvent(delete)
    return redirect('/events', code=303)
  if undelete and editor:
    utils.DeleteEvent(undelete, undelete=True)
    return redirect('/events', code=303)
  
  utils.PurgeDeletedEvents()
  
  parts = []
  parts.append(CH("Events", 1))
  
  parts.append("Events make it easier to play together as a group.  The group "
               "leader creates the event, adds sets to it, and specifies which set "
               "is currently being played.  Other musicians can watch the event "
               "and all the participating devices (ipads, phones, laptops, etc) will update "
               "as the event changes.")

  events = utils.ReadEvents()
  events.sort(key=lambda s:s.title)

  parts.append(CParagraph(CText("The following events have been created:", bold=1)))

  if events:
    for event in events:
      parts.extend([
        CText('&#9834; '),
        CText(event.title, href='/event/%s' % event.name),
        CBreak(),
      ])
  else:
    parts.append(CParagraph(CText("There are no active events right now.", italic=1)))
    
  if not editor:
    parts.append(LoginButton('/events'))
    parts.append(CDiv(style='clear:both'))
    return PageWrapper(parts, 'event')

  parts.append(CForm([
    CBreak(), 
    CText("Create a New Event:", bold=1),
    CBreak(1),
    CText("Title:"), CInput(type='TEXT', name='title', id='event-title', maxlength=200, style='width:55%'),
    CBreak(2),
    CInput(type='SUBMIT', value='Create'), 
  ], action='/event', method='POST', id="event-form"))
  
  parts.append(CBreak())
  
  inactive = utils.ReadEvents(deleted=True)
  if inactive:
    parts.append(CParagraph(CText("Recently deleted events:", bold=1)))
    for event in inactive:
      expires = time.strftime('%x %X', time.localtime(event.GetExpiration()))
      parts.extend([
        CSpan(event.title+' - Expires '+expires+' - '),
        CText("Undelete", href='/event/undelete/%s' % event.name),
        CBreak(), 
      ])
  
  parts.append(CDiv(style='clear:both'))

  return PageWrapper(parts, 'event')

@app.route('/event', methods=['POST'])
@app.route('/event/<sid>')
@app.route('/event/<sid>/add/<add>')
@app.route('/event/<sid>/add/<add>/replace/<old>')
@app.route('/event/<sid>/delete/<delete>')
@app.route('/event/<sid>/current/<curr>')
@app.route('/event/<sid>/status/<status>')
@app.route('/event/<sid>/select/<selector>')
def event(sid=None, add=None, delete=None, curr=None, old=None, status=None, selector=None):

  editor = HasCapability(kCapManageEvents)
  
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
    sid = utils.CreateEvent(title)
    
  event = utils.CEvent(sid)
  event.ReadEvent()
  
  if add is not None and editor:
    if old is not None:
      pos = event.sets.index(old)
      event.sets[pos] = add
    else:
      event.sets.append(add)
    event.WriteEvent()
    return redirect('/event/%s' % sid, code=303)
  
  if delete is not None and editor:
    event.sets.remove(delete)
    if event.current_set == delete:
      event.current_set = ''
    event.WriteEvent()
    return redirect('/event/%s' % sid, code=303)
    
  if curr is not None and editor:
    event.current_set = curr
    if event.on_air:
      for ptime in event.stats[curr][:]:
        if ptime > time.time() - 60 * 60:
          event.stats[curr].remove(ptime)
      event.stats[curr].append(time.time())
    event.WriteEvent()
    return redirect('/event/%s' % sid, code=303)

  if status is not None and editor:
    if status == 'on-air':
      event.on_air = 1
    else:
      event.on_air = 0
    event.WriteEvent()
    return redirect('/event/%s' % sid, code=303)
    
  if selector is not None and editor:
    if selector == 'random':
      if len(event.sets) == 0:
        new_set = None
      elif len(event.sets) == 1:
        new_set = event.sets[0]
      else:
        choice = random.randint(0, len(event.sets))
        while event.sets[choice] == event.current_set:
          choice = random.randint(0, len(event.sets))
        new_set = event.sets[choice]
    else:
      times = []
      for s in event.sets:
        if s in event.stats:
          ptime = sorted(event.stats[s])[-1]
        else:
          ptime = 0.0
        times.append((ptime, s))
      if times:
        new_set = sorted(times)[0][1]
      else:
        new_set = None
      
    if new_set:
      return redirect('/event/%s/current/%s' % (sid, new_set), code=303)
    else:
      return redirect('/event/%s' % sid, code=303)      
  
  if event.title:
    title = event.title
  else:
    title = "Deleted"
    
  parts = []
  parts.append(CH("Event: %s" % event.title, 1))
  parts.append(CParagraph(""))
  
  if not event.title:
    parts.extend([
      CParagraph("This event has been deleted"),
      CBreak(2),
      CText('Return to event list', href='/events'),
    ])
    return PageWrapper(parts, 'event', show_eye_candy=False)
    
  parts.extend(EventReloader(sid))
  
  if not event.current_set:
    c = 'None'
  else:
    c = get_set_title(event.current_set)

  parts.extend([
    CText("Now Playing: ", bold=1), 
    CSpan(c),
    CBreak(), 
    CText("Follow This Event:", bold=1),
    CNBSP(),
    CText("Notes", href='/watch/notes/%s' % sid), 
    CNBSP(), 
    CText("Chords", href='/watch/chords/%s' % sid), 
    CNBSP(), 
    CText("Both", href='/watch/%s' % sid),
    CBreak(), 
  ])
  
  if event.on_air:
    img = '/image/slider-on.png'
    status = "On the Air: Recording active set statistics."
    status_url = '/event/%s/status/off-air' % sid
  else:
    img = '/image/slider-off.png'
    status = "Off The Air"
    status_url = '/event/%s/status/on-air' % sid

  if editor:
    status_img = CImage(src=img, href=status_url)
  else:
    status_img = CImage(src=img)
    
  parts.extend(
    [
      CBreak(),
      CText("Status:", bold=1),
      CNBSP(), 
      status_img, 
      CNBSP(),
      CText(status)
    ])
  
  parts.append(CH("Available Sets:", 2))
  if not event.sets:
    parts.append(CText("No sets have been defined for this event", italic=1))
  else:
    if editor:
      parts.append(CParagraph("Click on a red dot to change the current set.  View a set with "
                              "melody reminders, chords, or both."))
      if event.on_air:
        parts.extend([
          CText("Select Set:"),
          CNBSP(),
          CText("Random", href='/event/%s/select/random' % sid), 
          CNBSP(),
          CText("Least Recent", href='/event/%s/select/oldest' % sid),
          CBreak(2), 
        ])
    else:
      parts.append(CParagraph("View a particular set with melody reminders, chords, or both:"))

    for s in event.sets:
      titles = get_set_title(s)
      
      url = '/sets/%s' % s
      if s == event.current_set:
        parts.append(CImage(src='/image/check-mark.png', style="height:1.0em"))
      elif editor:
        parts.append(CImage(src='/image/red-square.png', href="/event/%s/current/%s" % (sid, s),
                            style="height:1.0em"))
      else:
        parts.append(CImage(src='/image/red-square.png', style="height:1.0em"))
        
      parts.extend([
        CNBSP(2), 
        CText("Notes", href=url+'&pagetype=notes&event=%s' % sid), 
        CNBSP(), 
        CText("Chords", href=url+'&pagetype=chords&event=%s' % sid), 
        CNBSP(), 
        CText("Both", href=url+'&event=%s' % sid),
        CNBSP(), 
        CText("Print", href=url+'&event=%s&print=1' % sid),
        CNBSP(2), 
        CSpan(titles), 
      ])
      
      if event.stats[s]:
        ptime = sorted(event.stats[s])[-1]
        ltime = time.localtime(ptime)
        now = time.localtime(time.time())
        yr = time.strftime('%Y', ltime)
        if int(yr) != int(time.strftime('%Y', now)):
          lplayed = time.strftime('%b %d %Y', ltime)
        else:
          lplayed = time.strftime('%b %d', ltime)
        parts.extend([
          CText(' - '),
          CText('Played %ix last on %s' % (len(event.stats[s]), lplayed)), 
        ])
      
      if editor:
        parts.extend([
          CText(' - '),
          CText("Edit", href='/sets/sid/%s/edit/%s' % (sid, s)),
          CText(' - '), 
          CText("Delete", href='/event/%s/delete/%s' % (sid, s)),
        ])
      
      parts.append(CBreak())
    
  if editor:
    parts.append(CBreak(2))
    parts.append(CForm([
      CInput(type="SUBMIT", value="Add a Set"), 
    ], action='/sets/sid/%s' % sid, method='GET', id="add-set-form"))
  
  parts.extend([
    CBreak(), 
    CText('Print this event', href='/print/event/%s' % sid),
    CText('(this may take a while)'), 
    CBreak(), 
    CText('Return to event list', href='/events'),
    CBreak(), 
  ])
  if editor:
    parts.extend([
      CBreak(),
      CText('Delete this event', href='/events/delete/%s' % event.name),
    ])
  else:
    parts.append(CBreak())
    parts.append(LoginButton('/event/%s' % event.name))

  return PageWrapper(parts, 'event', show_eye_candy=False)

@app.route('/watch/<sid>')
@app.route('/watch/<type>/<sid>')
def watch(sid, type=None):
  
  if type is None:
    type = 'both'
    
  event = utils.CEvent(sid)
  event.ReadEvent()

  if event.title:
    title = event.title
  else:
    title = "Deleted"
    
  parts = []
  
  parts.extend(EventReloader(sid))
  
  parts.append(CText("Watching Event: %s" % title, bold=1))
  parts.append(CBreak(2))
  
  if not event.title:
    parts.append(CText("This event has been deleted", italic=1))
  elif not event.current_set:
    parts.append(CText("Please wait for a current set to be established", italic=1))
  else:
    tunes = event.current_set.split('&')
    
    import hashlib
    md5sum = hashlib.md5()
    for tune in tunes:
      md5sum.update(tune)
    name = 'C-' + md5sum.hexdigest()
    
    parts.extend(CreateTuneSetHTML(tunes, type))
  
  if not event.title:
    parts.append(CBreak(2))
    parts.append(CText("Return to event list", href="/events"))
  else:
    parts.append(CBreak(2))
    parts.append(CText("Return to set list", href="/event/%s" % sid))
  parts.append(CBreak())
  
  return PageWrapper(parts)

@app.route('/auth/send', methods=['POST'])
def auth_send():
  """AJAX endpoint: validate email, generate token, send magic link."""
  email = request.form.get('email', '').strip().lower()
  target = request.form.get('target', '/events')

  if not email or '@' not in email:
    return jsonify(ok=False, message='Please enter a valid email address.')

  # For admin targets, check if email is in admin list before sending
  admin_targets = ('/dev',)
  needs_admin = any(target.startswith(t) for t in admin_targets)
  if needs_admin and email not in GetAdminEmails():
    return jsonify(ok=False, message='Admin login required. This email is not authorized for admin access.')

  login_type = 'admin' if needs_admin else GetPermissionLevel(email)

  LogLogin('link-request', email, login_type)

  token = GenerateToken(email, target, login_type)

  if IsRateLimited(email):
    # Pretend we sent the email, with a delay to mask the difference
    LogLogin('rate-limited', email, login_type)
    time.sleep(random.uniform(1.0, 2.5))
  else:
    try:
      SendMagicLink(email, token, target)
      LogLogin('link-sent', email, login_type)
    except Exception as e:
      return jsonify(ok=False, message='Failed to send email. Please try again.')

  CleanExpiredTokens()

  return jsonify(ok=True, message='Check your email for a login link.')

@app.route('/auth/<token>')
def auth_verify(token):
  """Validate token, create session, redirect to target."""
  result = ValidateToken(token)
  if result is None:
    parts = [
      CH("Login Link Expired", 2),
      CParagraph("This login link has expired or has already been used."),
      LoginButton('/'),
      CBreak(),
      CText("Return Home", href='/'),
    ]
    return PageWrapper(parts, 'event', show_eye_candy=False)

  email, target, level = result
  session.permanent = True
  session['email'] = email
  session['permission_level'] = level
  session['login_time'] = time.time()

  LogLogin('login', email, level)

  return redirect(target, code=303)

@app.route('/authorize/<path:target>')
def authorize(target):
  """Compatibility route: redirect if logged in, otherwise show login popup via JS."""
  if IsLoggedIn():
    return redirect('/'+target, code=303)

  parts = [
    CH("Login Required", 2),
    CParagraph("Please log in to access this page."),
    '<script>document.addEventListener("DOMContentLoaded",function(){showLoginPopup("/%s");});</script>' % target,
  ]
  return PageWrapper(parts, 'event', show_eye_candy=False)

@app.route('/logout')
@app.route('/logout/')
@app.route('/logout/<path:target>')
def logout(target=''):
  Logout()
  return redirect('/'+target, code=303)

@app.route('/ajax/event/<sid>/current')
def ajax_event_current(sid):
  s = utils.CEvent(sid)
  s.ReadEvent()
  return s.current_set + '&' + str(len(s.sets))

def ReadEmailConfig():
  """Read email config file, return dict of key=value pairs."""
  config = {}
  if not os.path.exists(kEmailConf):
    return config
  with open(kEmailConf) as f:
    for line in f:
      line = line.strip()
      if '=' in line and not line.startswith('#'):
        key, val = line.split('=', 1)
        config[key.strip()] = val.strip()
  return config

def GetAdminEmails():
  """Return list of admin email addresses from config."""
  config = ReadEmailConfig()
  raw = config.get('admin_emails', '')
  return [e.strip().lower() for e in raw.split(',') if e.strip()]

def GetPermissionLevel(email):
  """Return 'admin' or 'regular' based on email."""
  if email.lower() in GetAdminEmails():
    return 'admin'
  return 'regular'

def IsLoggedIn():
  """Check if current session has a valid logged-in user."""
  email = session.get('email')
  login_time = session.get('login_time')
  if not email or not login_time:
    return False
  elapsed = time.time() - login_time
  if elapsed > kSessionLifetimeDays * 86400:
    return False
  return True

def HasCapability(capability):
  """Check if current session has a specific capability."""
  if not IsLoggedIn():
    return False
  level = session.get('permission_level', 'regular')
  caps = kPermissions.get(level, set())
  return capability in caps

def GetUserEmail():
  """Return logged-in user's email, or None."""
  if IsLoggedIn():
    return session.get('email')
  return None

def Logout():
  """Clear auth session keys."""
  for key in ('email', 'permission_level', 'login_time'):
    session.pop(key, None)

def GenerateToken(email, target, login_type):
  """Create a token file, return the token string.
  login_type is 'admin' or 'regular'."""
  raw = '%s-%s-%s' % (email, time.time(), os.urandom(16).encode('hex'))
  token = hashlib.sha256(raw.encode('utf-8')).hexdigest()
  path = os.path.join(kTokenDir, token + '.token')
  with open(path, 'w') as f:
    f.write('%s\n%s\n%s\n%s\n' % (email, target, time.time(), login_type))
  return token

def ValidateToken(token):
  """Read and delete token file. Return (email, target, level) or None."""
  path = os.path.join(kTokenDir, token + '.token')
  if not os.path.exists(path):
    return None
  with open(path) as f:
    lines = f.read().strip().split('\n')
  os.remove(path)
  if len(lines) < 4:
    return None
  email, target, created, level = lines[0], lines[1], float(lines[2]), lines[3]
  if time.time() - created > kTokenExpirySeconds:
    return None
  return (email, target, level)

def CleanExpiredTokens():
  """Remove expired token files."""
  now = time.time()
  for fn in os.listdir(kTokenDir):
    if not fn.endswith('.token'):
      continue
    path = os.path.join(kTokenDir, fn)
    try:
      with open(path) as f:
        lines = f.read().strip().split('\n')
      if len(lines) >= 3:
        created = float(lines[2])
        if now - created > kTokenExpirySeconds:
          os.remove(path)
    except:
      pass

def SendMagicLink(email, token, target):
  """Send a magic link email via SMTP.
  On Linux, shells out to system Python 3 for SSL support since the
  Python 2.7 virtualenv lacks it."""
  config = ReadEmailConfig()
  if not config.get('host'):
    raise Exception('Email not configured')

  if sys.platform == 'darwin':
    base_url = 'http://localhost:60080'
  else:
    base_url = 'http://music.cambridgeny.net'

  link = '%s/auth/%s' % (base_url, token)

  body = ('Click the link below to log in to Cambridge NY Traditional Music:\n\n'
          '%s\n\n'
          'This link expires in 1 hour and can only be used once.\n' % link)
  subject = 'Your Login Link - Cambridge NY Traditional Music'
  from_addr = config.get('from_address', config['username'])

  if sys.platform == 'darwin':
    # macOS dev: send directly
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = email
    server = smtplib.SMTP(config['host'], int(config.get('port', 587)))
    server.starttls()
    server.login(config['username'], config['password'])
    server.sendmail(from_addr, [email], msg.as_string())
    server.quit()
  else:
    # Linux production: use system Python 3 for SSL support
    import subprocess
    script = """
import smtplib
from email.mime.text import MIMEText
msg = MIMEText(%r)
msg['Subject'] = %r
msg['From'] = %r
msg['To'] = %r
server = smtplib.SMTP(%r, %d)
server.starttls()
server.login(%r, %r)
server.sendmail(%r, [%r], msg.as_string())
server.quit()
""" % (body, subject, from_addr, email,
       config['host'], int(config.get('port', 587)),
       config['username'], config['password'],
       from_addr, email)
    proc = subprocess.Popen(['/usr/bin/python3', '-c', script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode != 0:
      raise Exception('Email send failed: %s' % err)

def LogLogin(action, email, level=None):
  """Append a line to the login log, truncating if over 1MB."""
  timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
  if level == 'admin':
    label = '%s (admin)' % email
  else:
    label = email
  line = '%s  %-12s  %s\n' % (timestamp, action, label)

  # Truncate if over limit: keep the last half
  try:
    if os.path.exists(kLoginLog) and os.path.getsize(kLoginLog) > kLoginLogMaxBytes:
      with open(kLoginLog, 'r') as f:
        data = f.read()
      with open(kLoginLog, 'w') as f:
        f.write(data[len(data) // 2:])
  except:
    pass

  with open(kLoginLog, 'a') as f:
    f.write(line)

def IsRateLimited(email):
  """Return True if per-user or global rate limit exceeded in the last hour."""
  if not os.path.exists(kLoginLog):
    return False
  cutoff = time.time() - 3600
  user_count = 0
  global_count = 0
  try:
    with open(kLoginLog, 'r') as f:
      for line in f:
        if 'link-sent' not in line:
          continue
        parts = line.split('  ', 1)
        if len(parts) < 2:
          continue
        try:
          t = time.mktime(time.strptime(parts[0].strip(), '%Y-%m-%d %H:%M:%S'))
          if t >= cutoff:
            global_count += 1
            if email in line:
              user_count += 1
        except:
          pass
  except:
    pass
  return user_count >= kMaxEmailsPerHour or global_count >= kMaxGlobalEmailsPerHour

def EventReloader(sid):

  e = utils.CEvent(sid)
  e.ReadEvent()
  
  parts = []
  
  parts.append("""
<script src="/js/jquery-3.7.0.min.js"></script>
<script src="/js/ui/jquery-ui.min.js"></script>
""")
  
  parts.extend([
    """<script>
function CheckEvent() {
  $.ajax({
    url: "/ajax/event/%s/current",
    cache: false,
    success: function(txt){
      if (txt.trim() != "%s") {
        location.reload();
      }
    }
  });
}
$(document).ready(function() {
   setInterval(CheckEvent, 5000);
});
</script>""" % (sid, e.current_set + '&' + str(len(e.sets)))
             
  ])
  
  return parts

def _jpeg_dimensions(path):
  """Read width and height from a JPEG file header."""
  with open(path, 'rb') as f:
    f.read(2)  # SOI marker
    while True:
      marker, size = struct.unpack('>HH', f.read(4))
      if marker == 0xFFC0 or marker == 0xFFC2:  # SOF0 or SOF2
        f.read(1)  # precision
        height, width = struct.unpack('>HH', f.read(4))
        return width, height
      f.read(size - 2)
  return None, None

def LoginButton(target, label="Log in to create or edit events"):

  parts = [CBreak()]
  if label:
    parts.extend([CText(label, bold=1), CBreak(2)])
  parts.append('<button type="button" class="login-trigger" data-login-target="%s">Login</button>' % target)
  parts.append(CBreak(2))
  return CDiv(parts)

def FooterAuth():
  """Return auth status display for the footer, or empty string."""
  email = GetUserEmail()
  if not email:
    return ''
  return CSpan([
    CText('Logged in as: ', bold=1),
    CSpan(email, hclass='user-email-display'),
    CSpan(' (admin)', hclass='user-email-display') if session.get('permission_level') == 'admin' else '',
    CNBSP(2),
    '<button class="footer-logout" type="button" onclick="location.href=\'/logout\'+location.pathname">Logout</button>',
  ], hclass='footer-auth')
  
def PageWrapper(body, section=None, refresh=None, show_eye_candy=True, eye_candy_image=None):
  
  # Build html head
  title = "Cambridge NY Traditional Music"
  year = time.strftime("%Y", time.localtime())
  head = [
    CTitle(title),
    CMeta("text/html; charset=utf-8", http_equiv="Content-Type"),
    CMeta("Copyright (c) 1999-%s Stephan Deibel" % year, name="Copyright"),
    '<meta name="viewport" content="width=device-width, initial-scale=1">',
    '<link rel="stylesheet" type="text/css" href="/css/screen" media="screen" />',
    '<link rel="stylesheet" type="text/css" href="/css/print" media="print" />',
    '<script src="/js/player.js"></script>',
    '<script src="/js/login.js"></script>',
    '<script src="https://cdn.jsdelivr.net/npm/abcjs@6.6.2/dist/abcjs-basic-min.js"></script>',
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
      items.append(CNBSP(3))
  
    # Check for eye-candy image matching this section
    # Maps section name to (image filename, width percentage)
    kEyeCandySections = {
      'home': ('home', 37), 'local': ('local', 37),
      'dev': ('dev', 47), 'print': ('books', 33), 'event': ('events', 41),
      'session': ('sessions', 41),
    }
    eye_candy = ''
    if show_eye_candy and (eye_candy_image or section in kEyeCandySections):
      if eye_candy_image:
        img_name = eye_candy_image
        img_width = kEyeCandySections.get(section, (None, 41))[1]
      else:
        img_name, img_width = kEyeCandySections[section]
      img_path = os.path.join(utils.kImageDir, 'eye-candy', img_name + '.jpeg')
      if os.path.exists(img_path):
        nat_w, nat_h = _jpeg_dimensions(img_path)
        eye_candy = CImage(src='/image/eye-candy/%s.jpeg' % img_name,
                           hclass='eye-candy',
                           width=nat_w, height=nat_h,
                           style='float:right; width:%d%%; margin:0 0 10px 15px' % img_width)

    # Insert eye-candy image after the first CH heading so it
    # appears below the title rather than beside it
    if eye_candy and body:
      insert_at = 0
      for idx, item in enumerate(body):
        if isinstance(item, CH):
          insert_at = idx + 1
          break
      body = body[:insert_at] + [eye_candy] + body[insert_at:]

    body = [
      CDiv([CImage(src='/image/header.jpg', width=1090, height=100)], id='header'),
      CDiv(items, id='main-menu'),
    ] + body + [
      CDiv('', style='clear:both; height:20px'),
      CDiv([CText('Site Version %s - Maintained by Stephan Deibel' % kSiteVersion),
            FooterAuth()], id='footer'),
    ]
  
  body_div = CBody([CDiv(body, id="body", hclass='section-%s' % section if section else None),
    """<div id="audio-player">
<button class="ap-play">&#x25B6;</button>
<span class="ap-title"></span>
<div class="ap-progress-track"><div class="ap-progress-fill"></div></div>
<span class="ap-time">0:00 / 0:00</span>
<select class="ap-speed"><option value="1.0" selected>1.0x</option><option value="0.9">0.9x</option><option value="0.8">0.8x</option><option value="0.7">0.7x</option><option value="0.6">0.6x</option><option value="0.5">0.5x</option></select>
<button class="ap-close">&times;</button>
</div>""",
    """<div id="login-overlay" style="display:none">
<div id="login-popup">
<button id="login-close">&times;</button>
<h2>Login</h2>
<p class="login-instructions">Enter your email address and we'll send you a login link.</p>
<input type="email" id="login-email" placeholder="your@email.com" />
<button id="login-submit">Send Login Link</button>
<p id="login-message"></p>
<input type="hidden" id="login-target" value="" />
</div>
</div>""",
  ])
  
  html = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">"""
  html += str(CHTML([head, body_div], xmlns="http://www.w3.org/1999/xhtml"))
  
  return html
  
def CreateTuneSetHTML(tunes, pagetype='both', metadata=False):
  
  parts = []
  
  parts.append("""<style>
#body {
margin-top:0px;
}  
</style>""")
  for i, tune in enumerate(tunes):
    if i > 0:
      parts.append(CDiv(hclass='tune-break'))
    parts.extend(CreateTuneHTML(tune, pagetype, metadata))
  parts.append(CDiv(hclass='tune-break'))
  
  return parts

def CreateTuneSetPDF(name, title, subtitle, tunes):
  book = utils.CSetBook(name, title, subtitle, tunes)
  pdf = book.GeneratePDF(include_index=False, generate=True)
  return send_file(pdf, mimetype='application/pdf')
  
def CreateTuneHTML(name, pagetype='both', metadata=False, editor=False):

  obj = utils.CTune(name)
  try:
    obj.ReadDatabase()
    title = obj.title
  except SystemExit:
    title = "Unknown Tune"

  key_str = obj.GetKeyString()

  action_icons = obj.GetActionIcons()
  if obj.klass:
    if len(action_icons) == 1:
      klass_type = 'tune-type'
    elif len(action_icons) == 2:
      klass_type = 'tune-type-two-icons'
    elif len(action_icons) == 3:
      klass_type = 'tune-type-three-icons'
    else:
      klass_type = 'tune-type-four-icons'
    klass = CText(', '.join([utils.kSectionClasses[k] for k in obj.klass.split(',')]), italic=True, hclass=klass_type)
  else:
    klass = ''
    
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
    
  if obj.author and metadata:
    author = CDiv([CText('Author: {}'.format(obj.author), italic=True)])
  else:
    author = ''
    
  if obj.structure:
    structure = CDiv([CText('Structure: {}'.format(obj.structure), italic=True)])
  else:
    structure = ''

  if obj.origin and metadata:
    origin = CDiv([CText('Origin: {}'.format(obj.origin), italic=True)])
  else:
    origin = ''
    
  if obj.history and metadata:
    history = CParagraph(obj.history)
  else:
    history = ''
    
  if obj.url and metadata:
    urls = []
    url_list = obj.url.split('\n')
    for i, url in enumerate(url_list):
      urls.append(CText('Ref: '))
      urls.append(CText(url, href=url))
      urls.append(CBreak())
    urls = CDiv(''.join([str(u) for u in urls]), style='font-size:95%; padding-top:0.5em')
  else:
    urls = ''
    
  if obj.ref and metadata:
    refs = []
    ref_list = obj.ref.split('\n')
    for i, ref in enumerate(ref_list):
      refs.append(CText('Ref: '))
      refs.append(CText(ref))
      refs.append(CBreak())
    refs = CDiv(''.join([str(r) for r in refs]), style='font-size:95%; padding-top:0.5em')
  else:
    refs = ''
    
  if editor:
    edit_link = CDiv('<a href="/tune/%s/edit" class="green-button">Edit Tune</a>' % name, style='clear:right; float:right; margin-top:4px')
  else:
    edit_link = ''

  tune = CDiv([
    CH([
      title + ' - ' + key_str,
      klass,
    ] + obj.GetActionIcons(), 1, hclass=tclass),
    structure,
    author,
    origin,
    history,
    urls,
    refs,
    notes,
    chords,
    edit_link,
  ], hclass='tune')

  return [tune]
  
def GetNumColumns(chords):
  counts = collections.defaultdict(int)
  for part in reversed(chords):
    count = 0
    for measure in part:
      if measure in ('|:', ':|'):
        continue
      count += 1
    counts[count] += 1
  top_count = 0
  top_freq = 0
  for count, freq in counts.items():
    if freq > top_freq:
      top_freq = freq
      top_count = count
  count = top_count    
  if count / 5 * 5 == count:
    return 5
  elif count / 4 * 4 == count:
    return 4
  elif count / 2 * 2 == count:
    return count / 2
  else:
    return count
    
def ValidateChord(val):
  """Validate chord content.
  Valid: A-H (notes), b (flat, after A-H), # (sharp, after A-H),
  m (minor, after A-H/b/#/i), 7/6 (after A-H/b/#/m), 9 (after A-H/b/#/m/p),
  - (tie/sustain, after A-H/b/#/m/7/6), / ( ) (alternatives/optional),
  1-3 followed by : (alternate endings), Dim (diminished), sup (suspended)."""
  notes = 'ABCDEFGH'
  for i, c in enumerate(val):
    prev = val[i - 1] if i > 0 else ''
    nxt = val[i + 1] if i + 1 < len(val) else ''
    if c in notes:
      continue
    if c in '/()\n':
      continue
    if c in ('b', '#', '+') and prev in notes:
      continue
    if c == 'm' and (prev in notes or prev in ('b', '#', 'i')):
      continue
    if c in ('7', '6') and (prev in notes or prev in ('b', '#', 'm')):
      continue
    if c == '9' and (prev in notes or prev in ('b', '#', 'm', 'p')):
      continue
    if c == '-' and (prev in notes or prev in ('b', '#', 'm', '7', '6')):
      continue
    if c in '0123456789' and (nxt == '/' or prev == '/'):
      continue
    if c in ('1', '2', '3') and nxt == ':':
      continue
    if c == ':' and prev in ('1', '2', '3'):
      continue
    if c == 'i' and prev in notes:
      continue
    if c == 's' and (prev in notes or prev in ('b', '#')):
      continue
    if c == 'u' and prev == 's':
      continue
    if c == 'p' and prev == 'u':
      continue
  return val

def ChordsToHTML(chords, tclass='chords'):

    # Separate header/footer text (lines without |) from chart lines
    header_text = ''
    footer_text = ''
    if not isinstance(chords, list):
        lines = chords.splitlines()
        header_lines = []
        footer_lines = []
        chart_lines = []
        in_chart = False
        past_chart = False
        for line in lines:
            if '|' in line:
                in_chart = True
                past_chart = False
                chart_lines.append(line)
            elif in_chart:
                past_chart = True
                in_chart = False
                footer_lines.append(line)
            elif past_chart:
                footer_lines.append(line)
            else:
                header_lines.append(line)
        header_text = '\n'.join(header_lines).strip()
        footer_text = '\n'.join(footer_lines).strip()
        chords = utils.ParseChords('\n'.join(chart_lines))

    html = []
    part_class = 'even'
    max_line_len = 0
    target_columns = GetNumColumns(chords)
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
                elif len(row) == target_columns:
                    hclass = 'last-chord'
                row.append(CTD(measure, hclass=hclass))
            if len(row) == target_columns +1 and (i + 1 >= len(part) or part[i+1] != ':|'):
                row.append(CTD('', hclass='last'))
                max_line_len = max(max_line_len, len(row))
                html.append(CTR(row, hclass=part_class))
                row = []
            elif len(row) == target_columns + 2:
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

    table = CTable(html, width=None, hclass=tclass)

    if not header_text and not footer_text:
        return table

    if tclass == 'chords':
        note_style = 'font-size:min(3vw, 26px); text-align:left; overflow-wrap:break-word'
        note_class = 'chord-note'
    else:
        note_style = 'text-align:left; overflow-wrap:break-word'
        note_class = 'chord-note-only'
    parts = []
    if header_text:
        parts.append(CDiv(CText(header_text, italic=1), hclass=note_class, style=note_style))
    parts.append(table)
    if footer_text:
        parts.append(CDiv(CText(footer_text, italic=1), hclass=note_class, style=note_style))
    group_class = 'chord-group' if tclass == 'chords' else 'chord-group-only'
    return CDiv(parts, hclass=group_class)
  
gTuneCountCache = {}
def TuneCount(include_incomplete):

  if include_incomplete in gTuneCountCache:
    return gTuneCountCache[include_incomplete]
  
  tunes = utils.GetTuneIndex(include_incomplete)
  tune_count = 0
  seen_tunes = set()
  for section in tunes:
    for title, name in tunes[section]:
      if name in seen_tunes:
        continue
      seen_tunes.add(name)
      tune_count += 1

  gTuneCountCache[include_incomplete] = tune_count
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

  # This only makes sense when testing; on the server, the crontask is run by cron
  kWatchFilesToRegenerateBooks = False  
  if kWatchFilesToRegenerateBooks:
    
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
  else:
    app.debug = True
  if sys.platform == 'darwin':
    host = '0.0.0.0'
  else:
    host = 'music.cambridgeny.net'
  app.run(host=host, port=60080, use_reloader=True, extra_files=list(watch_files))

