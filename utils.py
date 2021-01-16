import os
import stat
import setsheets
import tempfile
import sys
import time
import collections
from html import * 

# Configuration
kFontSize = 18
kFontName = 'TrebuchetMS'
kBoldFontName = 'TrebuchetMSBold'
if sys.platform == 'darwin':
    kFontLoc = '/Library/Fonts/Trebuchet MS.ttf'
    kBoldFontLoc = '/Library/Fonts/Trebuchet MS Bold.ttf'
else:
    kFontLoc = '/usr/share/fonts/webcore/trebuc.ttf'
    kBoldFontLoc = '/usr/share/fonts/webcore/trebucbd.ttf'
kUseCache = True
kDebugBookGeneration = False

# Set up reportlab fonts
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
kFont = TTFont(kFontName, kFontLoc)
kBoldFont = TTFont(kBoldFontName, kBoldFontLoc)
pdfmetrics.registerFont(kFont)
pdfmetrics.registerFont(kBoldFont)

kBaseDir = os.path.dirname(os.path.dirname(__file__))
kExecutable = os.path.join(kBaseDir, 'bin/abcm2ps')
kDatabaseDir = os.path.join(os.path.dirname(__file__), 'db')
kSheetMusicDir = os.path.join(os.path.dirname(__file__), 'tunes')
kImageDir = os.path.join(os.path.dirname(__file__), 'images')
kRecordingsDir = os.path.join(os.path.dirname(__file__), 'recordings')
kCacheLoc = os.path.join(os.path.dirname(__file__), 'website', 'cache')
kSaveLoc = os.path.join(os.path.dirname(__file__), 'website', 'saved-sets')
kEventsLoc = os.path.join(os.path.dirname(__file__), 'website', 'events')
kEventArchiveLoc = os.path.join(kEventsLoc, 'archive')
kJSDir = os.path.join(os.path.dirname(__file__), 'website', 'js')

if not os.path.exists(kEventArchiveLoc):
    os.mkdir(kEventArchiveLoc)
        
from reportlab import rl_config
rl_config.warnOnMissingFontGlyphs = 0

kSections = [
    ('reel', 'Reels', 'Reel'),
    ('jig', 'Jigs', 'Jig'),
    ('slip', 'Slip Jigs', 'Slip Jig'), 
    ('rag', 'Rags', 'Rag'),
    ('march', 'Marches', 'March'),
    ('waltz', 'Waltzes', 'Waltz'),
    ('polka', 'Polkas', 'Polka'),
    ('polska', 'Polskas', 'Polska'),
    ('hornpipe', 'Hornpipes', 'Hornpipe'),
    ('strathspey', 'Strathspeys', 'Strathspey'),
    ('rant', 'Rants', 'Rant'), 
    ('slide', 'Slides', 'Slide'), 
    ('other', 'Others', 'Other'),
    ('air', 'Airs', 'Air'), 
    ('incomplete', 'Incomplete Listings', ''), 
]

kSectionTitles = {name: title for name, title, class_name in kSections}
kSectionClasses = {name: class_name for name, title, class_name in kSections}

kTimeSignatures = [
    ('2/4 and 4/4', ('reel', 'rag', 'march', 'hornpipe', 'polka', 'strathspey')),
    ('6/8', ('jig',)),
    ('9/8', ('slip', )), 
    ('3/4', ('waltz', 'polska', )),
    ('Other Tunes', ('other', )), 
]

class CTune:
    def __init__(self, name):
        self.name = name
        self.title = None
        self.structure = None
        self.author = None
        self.klass = None
        self.origin = None
        self.history = None
        self.comment = None
        self.url = None
        self.ref = None
        self.key = None
        self.unit = ''
        self.meter = ''
        self.notes = ''
        self.chords = ''
        self.sheet = ''
        
    def ReadDatabase(self):
        """Read one file from the tunes database.  Returns CTune named tuple"""
        
        if self.title:
            return
        
        fullpath = self._GetSpecFile()
        if fullpath is None:
            error("Could not find spec for %s" % self.name)
            
        f = open(fullpath)
        lines = f.readlines()
        f.close()
    
        kFieldMap = {
            'T': 'title',
            'A': 'author',
            'C': 'klass',
            'O': 'origin',
            'H': 'history',
            '#': 'comment',
            'U': 'url',
            'R': 'ref',
            'K': 'key',
            'L': 'unit',
            'M': 'meter',
            'S': 'structure',
        }
        
        kPartMap = {
            0: 'A',
            1: 'B',
            2: 'C',
            3: 'D',
            4: 'E',
            5: 'F',
            6: 'G',
            7: 'H',
            8: 'I',
            9: 'J',
        }
    
        part = 0
        notes_part = 0
        for line in lines:
            if line.startswith('#'):
                continue
            if line.strip() == '--':
                part += 1
    
            elif part == 0:
                found = False
                for key, field in kFieldMap.items():
                    if line.startswith('%s:'%key):
                        existing = getattr(self, field, None)
                        if existing:
                            value = existing + '\n' + line[len(key)+1:].strip()
                        else:
                            value = line[len(key)+1:].strip()
                        if key == 'K':
                            value = value.split()
                            value = value[0]
                        setattr(self, field, value)
                        found = True
                        break
                if not found:
                    error("Invalid line: %s: %s" % (fullpath, line))
                    
            elif part == 1:
                spec = '"%s part"' % kPartMap[notes_part]
                if self.key.find('/') > 0:
                    keys = self.key.split('/')
                    curr_key = keys[notes_part]
                    self.notes += 'K:%s\n' % curr_key
                self.notes += spec + line
                notes_part += 1
    
            elif part == 2:
                self.chords += line.rstrip() + '\n'
    
        if part != 2:
            error("Missing one or more parts: %s" % fullpath)
            
        if self.klass is None:
            self.klass = 'unknown'        

    def _GetSpecFile(self):
        
        fn = self.name + '.spec'        
        fullpath = os.path.join(kDatabaseDir, fn)
        if os.path.isfile(fullpath):
            return fullpath
        else:
            return None
        
    def _GetSheetMusicFile(self):
        
        fn = self.name + '.abc'        
        fullpath = os.path.join(kSheetMusicDir, fn)
        if os.path.isfile(fullpath):
            return fullpath
        else:
            return None
        
    def AsDict(self):
        d = {}
        for attrib in dir(self):
            if not attrib.startswith('_'):
                d[attrib] = getattr(self, attrib)
                
        d['fullkey'] = self._FullKey()
                
        return d
                
                
    def Type(self):
        return self.klass.split(',')[0].capitalize()
    
    def TypePlural(self):
        ttype = self.klass.split(',')[0]
        if ttype == 'waltz':
            return 'Waltzes'
        elif ttype == 'march':
            return 'Marches'
        elif ttype == 'slip':
            return 'Slip Jigs'
        else:
            return ttype.capitalize() + 's'
    
    def GetKeyString(self):
        keys = self.key
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
        return key_str
    
    def GetRecording(self):
        # Prefer mp3 because idiotically m4a does not work in Safari
        for enc in ['.mp3', '.m4a']:
            recording = os.path.join(kRecordingsDir, self.name+enc)
            if os.path.isfile(recording):
                if enc == '.mp3':
                    mtype = 'audio/mpeg'
                else:
                    mtype = 'audio/x-m4a'
                return '/recording/' + self.name + enc, mtype, recording
        return None, None, None
    
    def GetActionIcons(self, index=False, icons=['sheet', 'print', 'abc', 'play']):
        
        all_actions = {
            'sheet': self.__GetSheetIcon,
            'print': self.__GetPrintIcon,
            'abc': self.__GetABCIcon,
            'play': self.__GetPlayIcon,
        }
        
        if index:
            to_try = [all_actions[i] for i in icons]
        else:
            to_try = [all_actions[i] for i in reversed(icons)]
            
        retval = []
        for action in to_try:
            icon = action(index, len(retval) + 1)
            if icon:
                retval.append(icon)
                
        return retval
    
    def __GetSheetIcon(self, index, pos):
        hclass, size = self.__GetIconInfo(index, pos)
        if self.ReadSheetMusic() is not None:
            sheet = CImage(src='/image/notes.png', hclass=hclass,
                           href='/sheet/view/%s' % self.name, width=size, height=size)
        else:
            sheet = ''

        return sheet

    def __GetPrintIcon(self, index, pos):
        hclass, size = self.__GetIconInfo(index, pos)
        if self.ReadSheetMusic() is not None:
            sheet = CImage(src='/image/print-icon.png', hclass=hclass,
                           href='/sheet/print/%s' % self.name, width=size, height=size)
        else:
            sheet = ''

        return sheet

    def __GetABCIcon(self, index, pos):
        hclass, size = self.__GetIconInfo(index, pos)
        if self.ReadSheetMusic() is not None:
            sheet = CImage(src='/image/abc.png', hclass=hclass,
                           href='/sheet/abc/%s' % self.name, width=size, height=size)
        else:
            sheet = ''

        return sheet

    def __GetPlayIcon(self, index, pos):
        self.ReadDatabase()
        recording, mimetype, filename = self.GetRecording()
        hclass, size = self.__GetIconInfo(index, pos)
        if recording is not None:
            play = CImage(src='/image/speaker_louder_32.png', hclass=hclass,
                          href='/recording/%s' % self.name, width=size, height=size)
        elif not index:
            play = CImage(src='/image/speaker_louder_disabled_32.png', hclass=hclass,
                          width=size, height=size)
        else:
            play = ''

        return play

    def __GetIconInfo(self, index, pos):
        if index:
            hclass = 'action-icon-index'
            size = 16
        else:
            hclass = 'action-icon-%i' % pos
            size = 32
        return hclass, size

    def MakeNotes(self):
        """Generate only the reminder for the tune, as ABC"""

        kFormat = """X:0
K:%(key)s
L:%(unit)s
M:%(meter)s
%(notes)s
"""
        notes = self.__NotesWithMeterOnEachLine()
        d = self.AsDict().copy()
        d['notes'] = notes
        
        return kFormat % d
        
    def ReadSheetMusic(self):
        """Get the notes for this tune, in ABC, or None if not available"""

        if self.sheet:
            return self.sheet
        
        fn = self._GetSheetMusicFile()
        if fn is None:
            return None
        
        with open(fn, 'r') as f:
            self.sheet = f.read()
            return self.sheet
        
    def MakeNotesSVGFile(self):
    
        try:
            self.ReadDatabase()
        except:
            return None
        
        abc = self.MakeNotes()
        target, up_to_date = self._GetCacheFile('notes.svg')
        if not up_to_date:
            ABCToPostscript(abc, svg=True, target=target)
        
        return target
        
    def MakeNotesEPSFile(self):
        
        try:
            self.ReadDatabase()
        except:
            return None
        
        abc = self.MakeNotes()
        target, up_to_date = self._GetCacheFile('notes.eps')
        if not up_to_date:
            ABCToPostscript(abc, eps=True, target=target)
        
        return target
        
    def MakeSheetMusicEPSFile(self):
        
        try:
            self.ReadDatabase()
        except:
            return None
        
        abc = self.ReadSheetMusic()
        target, up_to_date = self._GetCacheFile('sheet.eps')
        if not up_to_date:
            ABCToPostscript(abc, eps=True, target=target, width='7in')
        
        return target
        
    def MakeNotesPNGFile(self, density=600):
        
        eps_file = self.MakeNotesEPSFile()
        png_file, up_to_date = self._GetCacheFile('notes.png')
        if up_to_date:
            return png_file
        
        bin_dir = '%s/bin' % kBaseDir
        cmd = 'PATH=$PATH:%s convert -density %i -depth 8 -monochrome %s %s' % (bin_dir, density, eps_file, png_file)
        os.system(cmd)
        
        return png_file
        
    def MakeSheetMusicPNGFile(self, density=600):
        
        eps_file = self.MakeSheetMusicEPSFile()
        png_file, up_to_date = self._GetCacheFile('sheet.png')
        if up_to_date:
            return png_file
        
        bin_dir = '%s/bin' % kBaseDir
        cmd = 'PATH=$PATH:%s convert -density %i -depth 8 -monochrome %s %s' % (bin_dir, density, eps_file, png_file)
        os.system(cmd)
        
        return png_file
        
    def MakeNotesLarge(self):
        """Generate large form of notes"""

        kFormat = """%%%%scale 2.0
%%%%begintext
%(title)s - %(fullkey)s
%%%%endtext
%%%%scale 0.9
K:%(key)s
L:%(unit)s
M:%(meter)s
%(notes)s
"""
        notes = self.__NotesWithMeterOnEachLine()
        d = self.AsDict().copy()
        d['notes'] = notes
        
        return kFormat % d
        
    def MakeChordsLarge(self, prepend_title=''):
        """Generate large form of chords, in abc format"""
        
        kFormat = """%%%%scale 2.0
%%%%textfont Times-Roman
%%%%begintext
%(prepend_title)s%(title)s - %(fullkey)s - %(meter)s
%%%%endtext
%%%%textfont Monaco
%%%%scale 1.4
%%%%begintext
%(chords)s
%%%%endtext
"""
        d = self.AsDict().copy()
        d['prepend_title'] = prepend_title
        
        return kFormat % d
    
    def MakeCardSmall(self):
        """Generate small form of cheat sheet card"""
        
        kFormat = """%%%%textfont Times-Roman
%%%%scale 5.0
T:%(title)s - %(fullkey)s
%%%%scale 0.9
K:%(key)s
L:%(unit)s
M:%(meter)s
%%%%multicol start
%%%%leftmargin 0.25in
%%%%rightmargin 5.0in
%(notes)s
%%%%multicol new
%%%%textfont Monaco
%%%%rightmargin 0.5in
%%%%scale 1.0
%%%%begintext right
%(chords)s
%%%%endtext
%%%%multicol end
"""

        notes = self.__NotesWithMeterOnEachLine()
        d = self.AsDict().copy()
        d['notes'] = notes
        chords = d['chords'].strip().splitlines()
        if len(chords) < 8:
            chords += [''] * (8 - len(chords))
        chords = '\n'.join(chords)
        d['chords'] = chords
        
        return kFormat % d

    def MakeCardRing(self):
        """Generate ring form of cheat sheet card"""
        
        kFormat = """%%%%textfont Times-Roman
%%%%scale 3.0
T:
T:%(title)s - %(fullkey)s
%%%%scale 0.9
K:%(key)s
L:%(unit)s
M:%(meter)s
%%%%multicol start
%%%%leftmargin 2.5in
%%%%rightmargin 3.5in
%%%%scale 0.7
%(notes)s
%%%%multicol new
%%%%textfont Monaco
%%%%rightmargin 0.5in
%%%%scale 0.8
%%%%begintext right

%(chords)s
%%%%endtext
%%%%multicol end
"""

        notes = self.__NotesWithMeterOnEachLine()
        d = self.AsDict().copy()
        d['notes'] = notes
        chords = d['chords'].strip().splitlines()
        if len(chords) < 11:
            chords += [''] * (11 - len(chords))
        chords = '\n'.join(chords)
        d['chords'] = chords
        
        return kFormat % d

    def MakeFlipBook(self, pos):
        """Generate form of cheat sheet card used in flip book"""

        kFormat = """%%%%textfont Times-Roman
%%%%scale 5.0
T:%(title)s - %(fullkey)s - %(tune_type)s
%%%%scale 0.8
K:%(key)s
L:%(unit)s
M:%(meter)s
%%%%multicol start
%%%%leftmargin 1.0in
%%%%rightmargin 4.5in
%(notes)s
%%%%multicol new
%%%%textfont Monaco
%%%%rightmargin 0.75in
%%%%scale 0.9
%%%%begintext right
%(chords)s
%%%%endtext
%%%%multicol new
%%%%textfont Monaco
%%%%rightmargin 0.25in
%%%%scale 1.0
%%%%begintext right
%(vspacer)s
%%%%endtext
%%%%multicol end
"""

        notes = self.__NotesWithMeterOnEachLine()
        d = self.AsDict().copy()
        d['notes'] = notes
        d['vspacer'] = '\n' * 9
        d['tune_type'] = self.Type()

        return kFormat % d

    def MakeChordsDrawing(self):
        
        # Import necessary modules
        from reportlab.lib import colors
        from reportlab.graphics.shapes import Drawing, Rect, Line, String
    
        # Set up font

        hpadding = kFont.stringWidth("N", kFontSize)
        
        # Create parts / chords table
        chords = ParseChords(self.chords)
        parts = []
        row_count = 0
        col_chars = [''] * 6
        
        def row_append(row, s):
            col = len(row)
            if kFont.stringWidth(s, kFontSize) > kFont.stringWidth(col_chars[col], kFontSize):
                col_chars[col] = s
            row.append(s)
            
        for i, part in enumerate(chords):
            rows = []
            row = []
            for i, measure in enumerate(part):
                if measure != '|:' and not row:
                    row_append(row, '')
                if measure == '|:':
                    row_append(row, ':')
                elif measure == ':|':
                    row_append(row, ':')
                else:
                    row_append(row, measure)
                if len(row) == 5 and (i + 1 >= len(part) or part[i+1] != ':|'):
                    row_append(row, '')
                    rows.append(row)
                    row = []
                elif len(row) == 6:
                    rows.append(row)
                    row = []
            if row:
                rows.append(row)
                
            parts.append(rows)
            row_count += len(rows)
            rows = []
            
        # Compute column widths
        col_widths = [0] * 6
        for i, chars in enumerate(col_chars):
            chars_width = kFont.stringWidth(chars, kFontSize)
            if i in (0, 5):
                col_widths[i] = chars_width
            else:
                col_widths[i] = chars_width + 2 * hpadding
        
        # Determine size of chord chart
        if row_count > 6:
            row_height = kFontSize * 1.4
        elif row_count > 4:
            row_height = kFontSize * 1.6
        else:
            row_height = kFontSize * 1.8
        width = sum(col_widths)
        height = row_height * row_count

        # Create drawing
        drawing = Drawing(width, height)
        
        # Draw chord chart
        v_pos = height
        for i, part in enumerate(parts):
            part_height = len(part) * row_height
            
            # Shade every other part
            if i % 2 == 0:
                r = Rect(0, v_pos-part_height, width, part_height)
                r.fillColor = colors.lightgrey
                r.strokeWidth = 0
                drawing.add(r)
                
            # Draw chords
            for row in part:
                hpos = 0
                vtextpos = v_pos - row_height + kFontSize / 2
                for j, chord in enumerate(row):
                    if chord == ':':
                        if j == 0:
                            cpos = hpos + kFontSize / 3
                        elif j == 5:
                            cpos = hpos - kFontSize / 3
                        else:
                            cpos = hpos + kFontSize / 2
                        s = String(cpos, vtextpos, chord)
                        s.fontName = kFontName
                        s.fontSize = kFontSize
                        drawing.add(s)
                    else:
                        s = String(hpos+kFontSize/2, vtextpos, chord)
                        s.fontName = kFontName
                        s.fontSize = kFontSize
                        drawing.add(s)
                    hpos += col_widths[j]
                v_pos -= row_height

        # Draw lines on right and left
        line_width = kFontSize / 6
        line = Line(line_width/2, 0, line_width/2, height)
        line.strokeWidth = line_width
        line.strokeColor = colors.black
        drawing.add(line)
        line = Line(width - line_width/2, 0, width - line_width/2, height)
        line.strokeWidth = line_width
        line.strokeColor = colors.black
        drawing.add(line)
        
        return drawing
        
    def MakeChordsEPS(self):
        
        drawing = self.MakeChordsDrawing()
                
        # Render drawing to EPS file
        filename, up_to_date = self._GetCacheFile('chords.eps')
        if not up_to_date:
            renderPS.drawToFile(drawing, filename)
        
        return filename
        
    def _GetCacheFile(self, basename):
        
        dirname = os.path.join(kCacheLoc, 'tune')
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        
        fn = os.path.join(dirname, self.name+'-'+basename)
        if not os.path.exists(fn):
            return fn, False
        
        if not kUseCache:
            return fn, False
        
        spec_file = self._GetSpecFile()
        if IsFileNewer(spec_file, fn):
            return fn, False
        sheet_music_file = self._GetSheetMusicFile()
        if sheet_music_file and IsFileNewer(sheet_music_file, fn):
            return fn, False
        
        return fn, True
            
    def _FullKey(self):
        key = self.key
        if key.lower().find('modal') > 0:
            pass
        elif key.endswith('m'):
            key = key[:-1] + ' Minor'
        elif key.endswith('mix'):
            key = key[:-3] + ' Modal'
        else:
            key = key + ' Major'
        return key
    
    def GetSortTitle(self):
        title = self.title
        if title.lower().startswith(('the ', 'les ')):
            title = title[4:]
        elif title.lower().startswith(('le ', )):
            title = title[3:]
        elif title.lower().startswith(('a ', "l'", )):
            title = title[2:]
        elif title.lower().startswith(("l'", )):
            title = title[1:]
        return title
    
    def __NotesWithMeterOnEachLine(self):
        notes = self.notes.splitlines()
        notes = [n + '\n' for n in notes]
        meter = 'M:%s\n' % self.meter
        new_notes = []
        for note in notes:
            if len(note) > 1 and note[1] == ':':
                new_notes.append(note)
            else:
                new_notes.append(meter)
                new_notes.append(note)
        return ''.join(new_notes)

class CTuneSet:
    
    def __init__(self, names=[], header='', footer='', setnum=''):

        self.type = None
        self.tunes = []
        self.header = header
        self.footer = footer
        self.setnum = setnum
        
        types = []
        for name in names:
            obj = CTune(name)
            obj.ReadDatabase()
            types.append(obj.Type())
            self.tunes.append(obj)
            
        if len(set(types)) > 1:
            self.type = "Mixed (%s)" % ', '.join(types)
        else:
            self.type = self.tunes[0].Type()
            
    def MakeNotesLarge(self):
        
        kStart = """textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"
%%%%scale 2.0
%%%%begintext
%s
%%%%endtext

""" % (self.header, self.footer, self.__SetType())
        
        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('X:%i\n'%i)
            parts.append(tune.MakeNotesLarge())
    
        return ''.join(parts)

    def _GetCacheFile(self, resource):
        
        dirname = os.path.join(kCacheLoc, 'tuneset')
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        
        fn = '-'.join([t.name for t in self.tunes]) + resource
        fn = os.path.join(dirname, fn)
        if not os.path.exists(fn):
            return fn, False
        if not kUseCache:
            return fn, False
        
        for tune in self.tunes:
            spec_file = tune._GetSpecFile()
            if IsFileNewer(spec_file, fn):
                return fn, False
        
        return fn, not kDebugBookGeneration
            
    def __SetType(self):
        stype = self.type
        if self.setnum:
            stype += ' - ' + self.setnum
        return stype

    def MakeChordsLarge(self):

        kStart = """%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"
%%%%scale 2.0
%%%%begintext
%s
%%%%endtext

""" % (self.header, self.footer, self.__SetType())

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\n')
            if i > 0:
                prepend_title = '\n'
            else:
                prepend_title = ''
            parts.append(tune.MakeChordsLarge(prepend_title))

        return ''.join(parts)
        
    def MakeCardRing(self):
        
        kStart = """%%%%textfont Monaco
%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"

%%%%scale 1.4
%%%%begintext
%s
%%%%endtext

""" % ('', '', '')

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeCardRing())
            
        return ''.join(parts)

    def MakeCardSmall(self):
        
        kStart = """%%%%textfont Monaco
%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"

%%%%scale 1.4
%%%%begintext
%s
%%%%endtext

""" % (self.header, self.footer, self.__SetType())

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeCardSmall())
            
        return ''.join(parts)

    def MakeCardPDF(self, page_num=None, show_type=False):
                
        filename, up_to_date = self._GetCacheFile(resource='.pdf')
        # Does not work to cache pages since header/footer vary by book and
        # some books share pages w/ same three tunes in same order
        #if up_to_date:
            #return filename
        
        # Set up
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Frame, Preformatted, Table, Spacer, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        
        pdf = Canvas(filename, pagesize=letter)
        pdf.setFont('TrebuchetMS', kFontSize)
        style = getSampleStyleSheet()
        style.add(ParagraphStyle(
            name='Bold',
            parent=style['BodyText'],
            fontName = 'TrebuchetMSBold',
            bulletFontName = 'TrebuchetMS',
            fontSize=kFontSize-1,
        ))
        style['BodyText'].fontName = 'TrebuchetMS'
        style['BodyText'].bulletFontName = 'TrebuchetMS'
        style['BodyText'].fontSize = kFontSize
        style['Heading1'].fontName = 'TrebuchetMSBold'
        style['Heading1'].fontSize = kFontSize
        style['Heading1'].fontName = 'TrebuchetMSBold'
        style['Heading1'].fontSize = kFontSize - 1
        
        header_footer_font_size = 8
        
        style.add(ParagraphStyle(
            name='HeaderFooter',
            parent=style['Normal'],
            fontName='TrebuchetMS',
            fontSize=header_footer_font_size,
            firstLineIndent=0,
            leftIndent=0,
        ))
    
        reminder_width = 3.25*inch
        chords_width = 3.75*inch
        
        story=[]
        
        for i, tune in enumerate(self.tunes):

            fulltitle = tune.title + ' - ' + tune.Type() + ' - ' + tune._FullKey()
            if len(fulltitle) < 55:
                title = Paragraph(fulltitle, style["Heading1"])
            else:
                title = Paragraph(fulltitle, style["Heading2"])
            ttable = Table([[title]], colWidths=[7.0*inch], rowHeights=[0.5*inch])
            ttable.setStyle(TableStyle([
                ('ALIGN',(0, 0),(0, 0),'LEFT'), 
                ('VALIGN',(0, 0),(-1,-1),'TOP'), 
                ('LEFTPADDING', (0, 0), (-1, -1), 0.1*inch), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 0), 
                ('TOPPADDING', (0, 0), (-1, -1), 0), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                # For debugging
                #( 'INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                #( 'BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
            story.append(ttable)
            
            reminder_png_file = tune.MakeNotesPNGFile()
            reminder_image = Image(reminder_png_file, reminder_width, 2.5*inch, kind='bound', hAlign='LEFT')
            chords_drawing = tune.MakeChordsDrawing()
            
            # Make sure chords fit in alloted space
            x, y, width, height = chords_drawing.getBounds()
            factor = None
            if width > chords_width:
                factor = (chords_width) / width
            if height > 2.5 * inch:
                h_factor = (2.5 * inch) / height
                if factor is None or h_factor < factor:
                    factor = h_factor
            if factor:
                chords_drawing.scale(factor, factor)
                x, y, new_width, new_height = chords_drawing.getBounds()
                chords_drawing.translate((width-new_width)/factor, (height-new_height)/factor)
            
            rows = [[reminder_image, chords_drawing]]
            table = Table(rows, vAlign='TOP', colWidths=[reminder_width, chords_width], rowHeights=[2.833*inch])
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0),(0, 0),'LEFT'), 
                ('ALIGN', (1, 0),(1, 0),'RIGHT'), 
                ('VALIGN', (0, 0),(-1,-1),'TOP'), 
                ('LEFTPADDING', (0, 0), (-1, -1), 0), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 0), 
                ('TOPPADDING', (0, 0), (-1, -1), 0), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                # For debugging
                #( 'INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                #( 'BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
            story.append(table)

        # Place body into frame
        f = Frame(1.0*inch, 0.5*inch, 7.0*inch, 10.0*inch, leftPadding=0,
                  bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
        f.addFromList(story, pdf)
        
        # Add page number
        if page_num is not None:
            if show_type:
                ttype = self.tunes[0].TypePlural()
                pageno = '%s - Page %i' % (ttype, page_num)
            else:
                pageno = 'Page %i' % page_num
            pageno_width = kFont.stringWidth(pageno, header_footer_font_size)
            pageno = Paragraph(pageno, style['HeaderFooter'])
            ptable = Table([[pageno]], colWidths=[pageno_width], rowHeights=[0.25*inch])
            ptable.setStyle(TableStyle([
                ('ALIGN', (0, 0),(0, 0),'RIGHT'), 
                ('VALIGN', (0, 0),(-1,-1),'TOP'), 
                ('LEFTPADDING', (0, 0), (-1, -1), 0), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 0), 
                ('TOPPADDING', (0, 0), (-1, -1), 0), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                # For debugging
                #( 'INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                #( 'BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
            f = Frame(8.0*inch-pageno_width, 10.5*inch, pageno_width, 0.25*inch, leftPadding=0,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(ptable, pdf)
            
        # Add header/footer
        if self.header:
            header = Paragraph(self.header, style['HeaderFooter'])
            f = Frame(1.0*inch, 10.5*inch, 7.0*inch, 0.25*inch, leftPadding=0.1*inch,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(header, pdf)

        if self.footer:
            footer = Paragraph(self.footer, style['HeaderFooter'])
            f = Frame(1.0*inch, 0.25*inch, 7.0*inch, 0.25*inch, leftPadding=0.1*inch,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(footer, pdf)
    
        # Close page and save to disk
        pdf.save()
        
        return filename
        
    def MakeFlipBook(self):

        kStart = """%%%%textfont Monaco
%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"

%%%%scale 1.2
%%%%leftmargin 1.0in
%%%%begintext

%%%%endtext

""" % (self.header, self.footer)

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeFlipBook(i))

        return ''.join(parts)

class CSheetPage:
    
    def __init__(self, name, header='', footer='', show_pagenum=False):

        self.header = header
        self.footer = footer
        self.show_pagenum = show_pagenum
        
        self.tunes = [CTune(name)]
        self.tunes[0].ReadDatabase()
            
    def MakeNotesLarge(self):
        
        kStart = """textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"
%%%%scale 2.0
%%%%begintext
%s
%%%%endtext

""" % (self.header, self.footer, self.__SetType())
        
        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('X:%i\n'%i)
            parts.append(tune.MakeNotesLarge())
    
        return ''.join(parts)

    def _GetCacheFile(self, resource):
        
        dirname = os.path.join(kCacheLoc, 'tuneset')
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        
        fn = self.tunes[0].name + resource
        fn = os.path.join(dirname, fn)
        if not os.path.exists(fn):
            return fn, False
        if not kUseCache:
            return fn, False
        
        spec_file = self.tunes[0]._GetSpecFile()
        if IsFileNewer(spec_file, fn):
            return fn, False
        
        return fn, not kDebugBookGeneration
            
    def __SetType(self):
        stype = self.type
        if self.setnum:
            stype += ' - ' + self.setnum
        return stype

    def MakeChordsLarge(self):

        kStart = """%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"
%%%%scale 2.0
%%%%begintext
%s
%%%%endtext

""" % (self.header, self.footer, self.__SetType())

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\n')
            if i > 0:
                prepend_title = '\n'
            else:
                prepend_title = ''
            parts.append(tune.MakeChordsLarge(prepend_title))

        return ''.join(parts)
        
    def MakeCardRing(self):
        
        kStart = """%%%%textfont Monaco
%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"

%%%%scale 1.4
%%%%begintext
%s
%%%%endtext

""" % ('', '', '')

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeCardRing())
            
        return ''.join(parts)

    def MakeCardSmall(self):
        
        kStart = """%%%%textfont Monaco
%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"

%%%%scale 1.4
%%%%begintext
%s
%%%%endtext

""" % (self.header, self.footer, self.__SetType())

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeCardSmall())
            
        return ''.join(parts)

    def MakeCardPDF(self, page_num=None, show_type=False):
                
        filename, up_to_date = self._GetCacheFile(resource='-sheet.pdf')
        # Does not work to cache pages since header/footer vary by book and
        # some books share pages w/ same three tunes in same order
        #if up_to_date:
            #return filename
        
        # Set up
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Frame, Preformatted, Table, Spacer, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        
        pdf = Canvas(filename, pagesize=letter)
        pdf.setFont('TrebuchetMS', kFontSize)
        style = getSampleStyleSheet()
        style.add(ParagraphStyle(
            name='Bold',
            parent=style['BodyText'],
            fontName = 'TrebuchetMSBold',
            bulletFontName = 'TrebuchetMS',
            fontSize=kFontSize-1,
        ))
        style['BodyText'].fontName = 'TrebuchetMS'
        style['BodyText'].bulletFontName = 'TrebuchetMS'
        style['BodyText'].fontSize = kFontSize
        style['Heading1'].fontName = 'TrebuchetMSBold'
        style['Heading1'].fontSize = kFontSize
        style['Heading1'].fontName = 'TrebuchetMSBold'
        style['Heading1'].fontSize = kFontSize - 1
        
        header_footer_font_size = 8
        
        style.add(ParagraphStyle(
            name='HeaderFooter',
            parent=style['Normal'],
            fontName='TrebuchetMS',
            fontSize=header_footer_font_size,
            firstLineIndent=0,
            leftIndent=0,
        ))
    
        story=[]
        
        tune = self.tunes[0]
        
        sheet_png_file = tune.MakeSheetMusicPNGFile()
        sheet_image = Image(sheet_png_file, 7.0*inch, 9.5*inch, kind='bound', hAlign='LEFT')
        story.append(sheet_image)

        # Place body into frame
        f = Frame(1.0*inch, 0.5*inch, 7.0*inch, 10.0*inch, leftPadding=0,
                  bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
        f.addFromList(story, pdf)
        
        # Add page number
        if page_num is not None and self.show_pagenum:
            pageno = 'Page %i' % page_num
            pageno_width = kFont.stringWidth(pageno, header_footer_font_size)
            pageno = Paragraph(pageno, style['HeaderFooter'])
            ptable = Table([[pageno]], colWidths=[pageno_width], rowHeights=[0.25*inch])
            ptable.setStyle(TableStyle([
                ('ALIGN', (0, 0),(0, 0),'RIGHT'), 
                ('VALIGN', (0, 0),(-1,-1),'TOP'), 
                ('LEFTPADDING', (0, 0), (-1, -1), 0), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 0), 
                ('TOPPADDING', (0, 0), (-1, -1), 0), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                # For debugging
                #( 'INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                #( 'BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
            f = Frame(8.0*inch-pageno_width, 10.5*inch, pageno_width, 0.25*inch, leftPadding=0,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(ptable, pdf)
            
        # Add header/footer
        if self.header:
            header = Paragraph(self.header, style['HeaderFooter'])
            f = Frame(1.0*inch, 10.5*inch, 7.0*inch, 0.25*inch, leftPadding=0.1*inch,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(header, pdf)

        if self.footer:
            footer = Paragraph(self.footer, style['HeaderFooter'])
            f = Frame(1.0*inch, 0.25*inch, 7.0*inch, 0.25*inch, leftPadding=0.1*inch,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(footer, pdf)
    
        # Close page and save to disk
        pdf.save()
        
        return filename
        
    def MakeFlipBook(self):

        kStart = """%%%%textfont Monaco
%%%%textfont Times-Roman
%%%%headerfont Times-Roman 12
%%%%header "%s"
%%%%footerfont Times-Roman 12
%%%%footer "%s"

%%%%scale 1.2
%%%%leftmargin 1.0in
%%%%begintext

%%%%endtext

""" % (self.header, self.footer)

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeFlipBook(i))

        return ''.join(parts)

class CBook:
    
    def __init__(self, name, title='', subtitle='', type_in_header=False, large=False):
        
        if name.endswith('.book'):
            fn = name
            name = os.path.basename(name)[:-len('.book')]
        else:
            fn = os.path.join(kDatabaseDir, name+'.book')

        self.title = title
        self.subtitle = subtitle
        self.type_in_header = type_in_header
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = name
        self.url = 'book/%s' % name
        
        if not os.path.isfile(fn):
            error("Could not find book %s" % name)
        f = open(fn)
        lines = f.readlines()
        f.close()

        if len(lines) < 6:
            error("Malformed or empty book %s" % fn)
        self.title, self.subtitle, self.date, self.contact = lines[:4]
        if not lines[4].strip() == '--':
            error("Malformed book %s: Missing -- after header" % fn)
            
        self.pages = []
        set_num = 1
        for i, line in enumerate(lines[5:]):
            if not line.strip() or line.startswith('#'):
                set_num = 1
                continue
            tunes = line.split()
            #setnum = 'Set %i' % set_num
            setnum = ''
            title = [self.title, self.subtitle, self.date]
            title = [t.strip() for t in title if t.strip()]
            title = ' - '.join(tuple(title))
            tuneset = CTuneSet(tunes, title, self.contact, setnum)
            self.pages.append(tuneset)
            set_num += 1
            
    def AllTunes(self):
        pages = []
        for page in self.pages:
            pages.extend([t.name for t in page.tunes])
        return pages
    
    def GenerateLarge(self):
        pages = []
        for page in self.pages:
            abc = page.MakeNotesLarge()
            notes = ABCToPostscript(abc)
            abc = page.MakeChordsLarge()
            chords = ABCToPostscript(abc)
            pages.extend([notes, chords])
            
        return pages
    
    def GenerateRing(self):
        pages = []
        for page in self.pages:
            abc = page.MakeCardRing()
            pages.append(ABCToPostscript(abc))
            
        return pages
    
    def GenerateSmall(self):
        pages = []
        for page in self.pages:
            abc = page.MakeCardSmall()
            pages.append(ABCToPostscript(abc))
            
        return pages
            
    def GeneratePDF(self, type_in_header=False, include_index=True, generate=False):
            
        target, up_to_date = self._GetCacheFile('.pdf')
        if (not generate and os.path.exists(target)) or up_to_date:
            return target

        pages = []
        for i, page in enumerate(self.pages):
            pdf = page.MakeCardPDF(i+1, show_type=type_in_header)
            pages.append(pdf)

        if include_index:
            pages.extend(self.GeneratePDFIndex())
        
        ConcatenatePDFFiles(pages, target)
        return target
    
    def GeneratePDFIndex(self):
        
        # Set up
        from reportlab.pdfgen.canvas import Canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Frame, Preformatted, Table, Spacer, TableStyle, Image
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors

        style = getSampleStyleSheet()
        style.add(ParagraphStyle(
            name='Bold',
            parent=style['BodyText'],
            fontName = 'TrebuchetMSBold',
            bulletFontName = 'TrebuchetMS',
            fontSize=kFontSize-1,
        ))
        style['BodyText'].fontName = 'TrebuchetMS'
        style['BodyText'].bulletFontName = 'TrebuchetMS'
        style['BodyText'].fontSize = kFontSize
        style['Heading1'].fontName = 'TrebuchetMSBold'
        style['Heading1'].fontSize = kFontSize
        style['Heading1'].fontName = 'TrebuchetMSBold'
        style['Heading1'].fontSize = kFontSize - 1

        header_footer_font_size = 8

        style.add(ParagraphStyle(
            name='HeaderFooter',
            parent=style['Normal'],
            fontName='TrebuchetMS',
            fontSize=header_footer_font_size,
            firstLineIndent=0,
            leftIndent=0,
        ))
        
        style.add(ParagraphStyle(
            name='Index',
            parent=style['Normal'],
            fontName='TrebuchetMS',
            fontSize=12,
            firstLineIndent=0,
            leftIndent=0,
            spaceBefore=0.1*inch, 
        ))        
 
        import collections
        contents = collections.defaultdict(list)
        tunes = {}
        for i, page in enumerate(self.pages):
            for tune in page.tunes:
                tunes[tune.name] = tune
                contents[tune.name].append(i+1)
        
        index = []
        for name in contents:
            tune = tunes[name]
            index.append((tune.GetSortTitle(), tune))
        index.sort()

        cur_page = []
        pages = [cur_page]
        for ignore, tune in index:
            
            fulltitle = tune.title + ' - ' + tune.Type() + ' - ' + tune._FullKey()
            pnums = set(contents[tune.name])
            pnums = list(pnums)
            pnums.sort()
            if len(pnums) > 1:
                p = 'Pages ' + ', '.join([str(i) for i in pnums])
            else:
                p = 'Page ' + str(pnums[0])
            title = Paragraph(fulltitle + ' - %s' % p, style["Index"])
            cur_page.append(title)
            if len(cur_page) >= 37:
                cur_page = []
                pages.append(cur_page)
        if len(pages[-1]) == 0:
            pages = pages[:-1]

        retval = []
        for i, page in enumerate(pages):
            
            filename, ignore = self._GetCacheFile('-index-%i.pdf' % (i+1,))
            
            pdf = Canvas(filename, pagesize=letter)
            pdf.setFont('TrebuchetMS', kFontSize)
    
            story=[]
            story.extend(page)
            
            # Place body into frame
            f = Frame(1.0*inch, 0.5*inch, 7.0*inch, 10.0*inch, leftPadding=0,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.addFromList(story, pdf)
    
            # Add page number
            pageno = 'Index %i' % (i + 1,)
            pageno_width = kFont.stringWidth(pageno, header_footer_font_size)
            pageno = Paragraph(pageno, style['HeaderFooter'])
            ptable = Table([[pageno]], colWidths=[pageno_width], rowHeights=[0.25*inch])
            ptable.setStyle(TableStyle([
                ('ALIGN', (0, 0),(0, 0),'RIGHT'), 
                ('VALIGN', (0, 0),(-1,-1),'TOP'), 
                ('LEFTPADDING', (0, 0), (-1, -1), 0), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 0), 
                ('TOPPADDING', (0, 0), (-1, -1), 0), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                # For debugging
                #( 'INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                #( 'BOX', (0,0), (-1,-1), 0.25, colors.black),
            ]))
            f = Frame(8.0*inch-pageno_width, 10.5*inch, pageno_width, 0.25*inch, leftPadding=0,
                      bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
            f.add(ptable, pdf)
    
            # Add header/footer
            if self.pages[0].header:
                header = Paragraph(self.pages[0].header, style['HeaderFooter'])
                f = Frame(1.0*inch, 10.5*inch, 7.0*inch, 0.25*inch, leftPadding=0.1*inch,
                          bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
                f.add(header, pdf)
    
            if self.pages[0].footer:
                footer = Paragraph(self.pages[0].footer, style['HeaderFooter'])
                f = Frame(1.0*inch, 0.25*inch, 7.0*inch, 0.25*inch, leftPadding=0.1*inch,
                          bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
                f.add(footer, pdf)
    
            # Close page and save to disk
            pdf.save()
            retval.append(filename)

        return retval
        
    def _GetCacheFile(self, book_type):
        
        dirname = os.path.join(kCacheLoc, 'book')
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        
        fn = os.path.join(dirname, self.name + book_type)
        if not os.path.exists(fn):
            return fn, False
        if not kUseCache:
            return fn, False
                        
        book_file = os.path.join(kDatabaseDir, self.name+'.book')
        if os.path.isfile(book_file) and IsFileNewer(book_file, fn):
            return fn, False
        
        for page in self.pages:
            for tune in page.tunes:
                spec_file = tune._GetSpecFile()
                if IsFileNewer(spec_file, fn):
                    return fn, False
                tune_file = tune._GetSheetMusicFile()
                if tune_file and IsFileNewer(tune_file, fn):
                    return fn, False
                
        for sfn in GetSourceFiles():
            if IsFileNewer(sfn, fn):
                return fn, False
        
        return fn, not kDebugBookGeneration
        
class CSetBook(CBook):
    
    def __init__(self, name, title, subtitle, tunes):
        self.title = title
        self.subtitle = subtitle
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = name
        self.url = 'book/%s' % self.name
        
        self.pages = []

        def append_page(page, setnum):
            title = [self.title, self.subtitle, self.date]
            title = [t.strip() for t in title if t.strip()]
            title = ' - '.join(tuple(title))
            tuneset = CTuneSet(page, title, self.contact, setnum)
            self.pages.append(tuneset)
            
        setnum = 1
        page = []
        for tune in tunes:
            page.append(tune)
            if len(page) == 3:
                append_page(page, setnum)
                setnum += 1
                page = []
                
        if page:
            append_page(page, setnum)

class CEvent:
    
    def __init__(self, name):
        self.name = name
        self.title = ''
        self.sets = []
        self.current_set = ''
        self.on_air = 0
        self.stats = collections.defaultdict(list)
        
    def ReadEvent(self, deleted=False):
        if deleted:
            dirname = kEventArchiveLoc
        else:
            dirname = kEventsLoc
            
        fn = os.path.join(dirname, self.name+'.evt')
        if not os.path.exists(fn):
            return
        
        f = open(fn, 'r')
        lines = f.read()
        f.close()
        
        lines = lines.split('\n')
        self.title = lines[0]
        self.current_set = lines[1]
        self.on_air = int(lines[2])
        
        self.sets = []
        curr_set = None
        for l in lines[3:]:
            if l == l.lstrip() and l.strip():
                self.sets.append(l)
                curr_set = l
            elif l.strip():
                assert curr_set is not None
                self.stats[curr_set].append(float(l.strip()))
        
    def WriteEvent(self):
        fn = os.path.join(kEventsLoc, self.name+'.evt')
        lines = [
            self.title,
            self.current_set, 
            str(self.on_air), 
        ]
        for sid in self.sets:
            lines.append(sid)
            for ptime in self.stats[sid]:
                lines.append('  ' + str(ptime))
                
        f = open(fn, 'w')
        f.write('\n'.join(lines))
        f.close()
        
    def GetExpiration(self):
        
        fn = os.path.join(kEventArchiveLoc, self.name+'.evt')
        if not os.path.exists(fn):
            return None
        
        mod_time = os.stat(fn)[stat.ST_MTIME]
        return mod_time + kEventExpiration        

def ReadEvents(deleted=False):

    if deleted:
        dirname = kEventArchiveLoc
    else:
        dirname = kEventsLoc
        
    files = os.listdir(dirname)

    events = []
    for fn in files:
        if fn.endswith('.evt'):
            event = CEvent(fn[:-len('.evt')])
            event.ReadEvent(deleted=deleted)
            events.append(event)
            
    return events

def CreateEvent(title):
    
    parts = title.split()
    first = [p[0] for p in parts]
    name = ''.join(first)
    event_file = os.path.join(kEventsLoc, name+'.evt')
    i = 0
    while os.path.exists(event_file):
        i += 1
        event_file = os.path.join(kEventsLoc, name + ('-%i' % i) +'.evt')
    if i:
        name = name + '-%i' % i
        
    name = name.lower()
    
    event = CEvent(name)
    event.title = title
    event.WriteEvent()
    
    return name
        
def DeleteEvent(sid, undelete=False):
    
    event_fn = os.path.join(kEventsLoc, sid+'.evt')
    archive_fn = os.path.join(kEventArchiveLoc, sid+'.evt')

    if not undelete:
        fn1 = event_fn
        fn2 = archive_fn
    else:
        fn1 = archive_fn
        fn2 = event_fn
        
    if not os.path.exists(fn1):
        return

    f = open(fn1, 'r')
    txt = f.read()
    f.close()
    
    f = open(fn2, 'w')
    f.write(txt)
    f.close()
    
    os.unlink(fn1)
    
kEventExpiration = 7 * 24 * 60 * 60
def PurgeDeletedEvents():
    
    events = os.listdir(kEventArchiveLoc)
    for event in events:
        if not event.endswith('.evt'):
            continue
        fn = os.path.join(kEventArchiveLoc, event)
        mod_time = os.stat(fn)[stat.ST_MTIME]
        if mod_time < time.time() - kEventExpiration:
            os.unlink(fn)
        
def GetTuneIndex(include_incomplete):

    incomplete_tunes = []
    tunes_by_class = collections.defaultdict(list)
    for fn in os.listdir(kDatabaseDir):
        if fn.startswith('.') or not fn.endswith('.spec'):
            continue
        
        name = fn[:-len('.spec')]
        tune = CTune(name)
        tune.ReadDatabase()
        if not include_incomplete and (not tune.chords or not tune.notes):
            continue
        title = tune.GetSortTitle()
        if not tune.chords.strip() or not tune.notes.strip():
            incomplete_tunes.append((title, name))
        else:
            for klass in tune.klass.split(','):
                tunes_by_class[klass.lower()].append((title, name))                    
                    
    for klass, tunes in tunes_by_class.items():
        tunes.sort()
        
    if incomplete_tunes:
        incomplete_tunes.sort()
        tunes_by_class['incomplete'] = incomplete_tunes
    
    return tunes_by_class

def ParseChords(chords):

    parts = []
    curr_part = []
    repeat_seen = False
    for line in chords.splitlines():
        measures = line.split(' ')
        for i, measure in enumerate(measures):
            measure = measure.strip()
            if i == 0 and measure in ('|', '|:') and curr_part:
                parts.append(curr_part)
                curr_part = []
            if measure and measure != '|':
                curr_part.append(measure)
    if curr_part:
        parts.append(curr_part)
        
    return parts

def ABCToPostscript(abc, svg=False, eps=False, target=None, width=None):

    f, fn = tempfile.mkstemp(suffix='.abc')
    f = os.fdopen(f, 'w')
    f.write(abc)
    f.close()

    if svg:
        if width is None:
            width = '4in'
        svg_arg = '-X -m 0 -w ' + width
        if target is None:
            target = os.path.splitext(fn)[0] + '.svg'
    elif eps:
        if width is None:
            width = '3.75in'
        svg_arg = '-E -m 0 -w ' + width
        if target is None:
            target = os.path.splitext(fn)[0] + '.eps'
    else:
        svg_arg = ''
        if target is None:
            target = os.path.splitext(fn)[0] + '.ps'
            
    if os.path.exists(target):
        os.unlink(target)
    
    cmdline = [kExecutable, fn, svg_arg, '-O', target]
    cmdline = ' '.join(cmdline)

    os.system(cmdline)
    
    if not os.path.exists(target):
        if svg:
            wrote_to = target[:-4] + '001.svg'
        elif eps:
            wrote_to = target[:-4] + '001.eps'
        else:
            wrote_to = target[:-3] + '001.ps'
        if os.path.exists(wrote_to):
            # Another process may do this at the same time
            try:
                os.rename(wrote_to, target)
            except:
                assert os.path.exists(target)
        
    if not os.path.exists(target):
        error("Could not create Postscript file %s" % target)

    os.remove(fn)
    return target

def ConcatenatePDFFiles(files, target):
    bindir = '%s/bin' % kBaseDir
    cmd = "PATH=$PATH:%s gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=%s " % (bindir, target)
    cmd += ' '.join(files)
    cmd = cmd.replace('&', '\\&')
    os.system(cmd)
    
def GetWatchFiles(book):
    """Get the dependencies for the given book, so we can decided whether
    we need to rebuild them based on modtimes"""

    watch_files = set()
    
    watch_files.add(os.path.join(kDatabaseDir, book.name+'.book'))
    
    for page in book.pages:
        for tune in page.tunes:
            watch_files.add(tune._GetSpecFile())

    watch_files.update(GetSourceFiles())
    
    return watch_files

def GetSourceFiles():
    
    dirs = [
        os.path.dirname(__file__),
        os.path.join(os.path.dirname(__file__), 'website'), 
    ]

    source_files = set()

    for dirname in dirs:
        files = os.listdir(dirname)
        for fn in files:
            if fn.endswith('.py'):
                source_files.add(os.path.join(dirname, fn))

    return source_files

def IsFileNewer(name1, name2):
    """ Returns whether file with name1 is newer than file with name2.  Returns
    0 if name1 doesn't exist and returns 1 if name2 doesn't exist. """

    if not os.path.exists(name1):
        return 0
    if not os.path.exists(name2):
        return 1

    mod_time1 = os.stat(name1)[stat.ST_MTIME]
    mod_time2 = os.stat(name2)[stat.ST_MTIME]
    return (mod_time1 > mod_time2)
    
kCGI = False
def error(txt):
    if kCGI:
        raise RuntimeError(txt)
    else:
        print(txt)
        sys.exit(1)
    

