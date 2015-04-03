import os
import setsheets
import tempfile
import sys

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
kImageDir = os.path.join(os.path.dirname(__file__), 'images')
kRecordingsDir = os.path.join(os.path.dirname(__file__), 'recordings')
kJSDir = os.path.join(os.path.dirname(__file__), 'website', 'js')

from reportlab import rl_config
rl_config.warnOnMissingFontGlyphs = 0

kSections = [
    ('reel', 'Reels'),
    ('jig', 'Jigs'),
    ('slip', 'Slip Jigs'), 
    ('rag', 'Rags'),
    ('march', 'Marches'),
    ('waltz', 'Waltzes'),
    ('hornpipe', 'Hornpipes'),
    ('other', 'Other'),
]

kSectionTitles = {name: title for name, title in kSections}

class CTune:
    def __init__(self, name):
        self.type = None
        self.name = name
        self.title = None
        self.key = None
        self.unit = '1/4'
        self.meter = '4/4'
        self.notes = ''
        self.chords = ''
        
    def ReadDatabase(self):
        """Read one file from the tunes database.  Returns CTune named tuple"""
        
        if self.notes:
            return
        
        fn = self.name + '.spec'
        
        fullpath = None
        type_dirs = os.listdir(kDatabaseDir)
        for td in type_dirs:
            if td.startswith('.'):
                continue
            fullpath = os.path.join(kDatabaseDir, td, fn)
            if os.path.isfile(fullpath):
                self.type = td
                break
            else:
                fullpath = None

        if fullpath is None:
            error("Could not find spec for %s" % self.name)
            
        f = open(fullpath)
        lines = f.readlines()
        f.close()
    
        kFieldMap = {
            'T': 'title',
            'K': 'key',
            'L': 'unit',
            'M': 'meter',
        }
        
        kPartMap = {
            0: 'A',
            1: 'B',
            2: 'C',
            3: 'D',
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
                        setattr(self, field, line[2:].strip())
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
    
            if line.startswith('T:'):
                self.title = line[2:].strip()
            elif line.startswith('K:'):
                self.key = line[2:].strip()
    
        if part != 2:
            error("Missing one or more parts: %s" % fullpath)
        
    def AsDict(self):
        d = {}
        for attrib in dir(self):
            if not attrib.startswith('_'):
                d[attrib] = getattr(self, attrib)
                
        d['fullkey'] = self._FullKey()
                
        return d
                
    def Type(self):
        if self.type == 'waltz':
            return 'Waltzes'
        elif self.type == 'march':
            return 'Marches'
        elif self.type == 'slip':
            return 'Slip Jigs'
        else:
            return self.type.capitalize() + 's'
    
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
        for enc in ['.mp3', '.m4a']:
            recording = os.path.join(kRecordingsDir, self.name+enc)
            if os.path.isfile(recording):
                if enc == '.mp3':
                    mtype = 'audio/mpeg'
                else:
                    mtype = 'audio/x-m4a'
                return '/recording/' + self.name + enc, mtype, recording
        return None, None, None
    
    def MakeNotes(self):
        """Generate only the notes for the tune, as ABC"""

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
        
    def MakeNotesSVGFile(self):
    
        try:
            self.ReadDatabase()
        except:
            return None
        
        abc = self.MakeNotes()
        svg_file = ABCToPostscript(abc, svg=True)
        
        return svg_file
        
    def MakeNotesSVG(self):

        svg_file = self.MakeNotesSVGFile()
        
        f = open(svg_file)
        svg = f.read()
        f.close()
        
        return svg
    
    def MakeNotesEPSFile(self):
        
        try:
            self.ReadDatabase()
        except:
            return None
        
        abc = self.MakeNotes()
        eps_file = ABCToPostscript(abc, eps=True)
        
        return eps_file
        
    def MakeNotesPNGFile(self):
        
        eps_file = self.MakeNotesEPSFile()
        png_file = tempfile.mktemp(suffix=".png")
        bin_dir = '%s/bin' % kBaseDir
        cmd = 'PATH=$PATH:%s %s/convert -density 600 -depth 8 -alpha opaque %s %s' % (bin_dir, bin_dir, eps_file, png_file)
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
        if self.type == 'slip':
            d['tune_type'] = 'Slip Jig'
        else:
            d['tune_type'] = self.type.capitalize()

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
        f, filename = tempfile.mkstemp(suffix='.eps')
        renderPS.drawToFile(drawing, filename)
        #os.system('open %s' % filename)
        
        return filename
        
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
            types.append(obj.type)
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

    def MakeCardPDF(self):
                
        f, filename = tempfile.mkstemp(suffix='.pdf')
        
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
    
        notes_width = 3.75*inch
        chords_width = 3.75*inch
        
        story=[]

        for i, tune in enumerate(self.tunes):

            fulltitle = tune.title + ' - ' + tune._FullKey()
            if len(fulltitle) < 55:
                title = Paragraph(fulltitle, style["Heading1"])
            else:
                title = Paragraph(fulltitle, style["Heading2"])
            ttable = Table([[title]], colWidths=[7.5*inch], rowHeights=[0.5*inch])
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
            
            notes_png_file = tune.MakeNotesPNGFile()
            notes_image = Image(notes_png_file, notes_width, 2.5*inch, kind='bound', hAlign='LEFT')
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
            
            rows = [[notes_image, chords_drawing]]
            table = Table(rows, vAlign='TOP', colWidths=[notes_width, chords_width], rowHeights=[2.833*inch])
            table.setStyle(TableStyle([
                ('ALIGN',(0, 0),(0, 0),'LEFT'), 
                ('ALIGN',(1, 0),(1, 0),'RIGHT'), 
                ('VALIGN',(0, 0),(-1,-1),'TOP'), 
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
        h = 10
        f = Frame(0.50*inch, 0.50*inch, 7.5*inch, 10.0*inch, leftPadding=0,
                  bottomPadding=0, rightPadding=0, topPadding=0, showBoundary=0)
        f.addFromList(story, pdf)
    
        # Close page and save to disk
        pdf.save()
        
        os.system("open %s" % filename)
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
    
    def __init__(self, name, large=False):
        self.title = ''
        self.subtitle = ''
        self.date = ''
        self.contact = ''
        
        fn = os.path.join(kDatabaseDir, name+'.book')
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
            title = [t.strip() for t in title]
            title = '%s - %s\\n%s' % tuple(title)
            tuneset = CTuneSet(tunes, title, self.contact, setnum)
            self.pages.append(tuneset)
            set_num += 1
            
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
            
    def GeneratePDF(self):
        pages = []
        for page in self.pages:
            pdf = page.MakeCardPDF()
            pages.append(pdf)
            
        pdf = ConcatenatePDFFiles(pages)
        
        return pdf

def GetTuneIndex():
    idx = {}

    for section, section_name in kSections:
        try:
            files = os.listdir(os.path.join(kDatabaseDir, section))
        except OSError:
            continue
        tunes = []
        for fn in files:
            if fn.endswith('.spec'):
                name = fn[:-len('.spec')]
                tune = CTune(name)
                tune.ReadDatabase()
                title = tune.title
                if title.lower().startswith('the '):
                    title = title[4:]
                elif title.lower().startswith('a '):
                    title = title[2:]
                tunes.append((title, name))
        tunes.sort()
        
        idx[section] = tunes
        
    return idx

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

def ABCToPostscript(abc, svg=False, eps=False):
    
    f, fn = tempfile.mkstemp(suffix='.abc')
    f = os.fdopen(f, 'w')
    f.write(abc)
    f.close()

    if svg:
        svg_arg = '-X -m 0 -w 4in'
        ps_fn = os.path.splitext(fn)[0] + '.svg'
    elif eps:
        svg_arg = '-E -m 0 -w 3.75in'
        ps_fn = os.path.splitext(fn)[0] + '.eps'
    else:
        svg_arg = ''
        ps_fn = os.path.splitext(fn)[0] + '.ps'
    cmdline = [kExecutable, fn, svg_arg, '-O', ps_fn]
    cmdline = ' '.join(cmdline)

    os.system(cmdline)
    
    if svg:
        if not os.path.exists(ps_fn):
            ps_fn = ps_fn[:-4] + '001.svg'
    elif eps:
        if not os.path.exists(ps_fn):
            ps_fn = ps_fn[:-4] + '001.eps'
    else:
        if not os.path.exists(ps_fn):
            ps_fn = ps_fn[:-3] + '001.ps'
        
    if not os.path.exists(ps_fn):
        error("Could not create Postscript file %s" % ps_fn)

    os.remove(fn)
    return ps_fn

def ConcatenatePDFFiles(files):
    output = tempfile.mktemp(suffix='.pdf')
    bindir = '%s/bin' % kBaseDir
    cmd = "PATH=$PATH:%s gs -dBATCH -dNOPAUSE -q -sDEVICE=pdfwrite -sOutputFile=%s " % (bindir, output)
    cmd += ' '.join(files)
    os.system(cmd)
    return output
    
def error(txt):
    print(txt)
    sys.exit(1)
    

