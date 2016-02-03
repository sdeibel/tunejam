import os
import stat
import setsheets
import tempfile
import sys
import time

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
kImageDir = os.path.join(os.path.dirname(__file__), 'images')
kRecordingsDir = os.path.join(os.path.dirname(__file__), 'recordings')
kCacheLoc = os.path.join(os.path.dirname(__file__), 'website', 'cache')
kSaveLoc = os.path.join(os.path.dirname(__file__), 'website', 'saved-sets')
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
    ('strathspey', 'Strathspeys'), 
    ('other', 'Other'),
    ('incomplete', 'Incomplete Listings'), 
]

kSectionTitles = {name: title for name, title in kSections}

kTimeSignatures = [
    ('2/4 and 4/4', ('reel', 'rag', 'march', 'hornpipe', 'strathspey')),
    ('6/8', ('jig',)),
    ('9/8', ('slip', )), 
    ('3/4', ('waltz',)),
    ('Other Tunes', ('other', )), 
]

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
        
        fullpath = self._GetSpecFile()
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

    def _GetSpecFile(self):
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
        return fullpath
        
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
        target, up_to_date = self._GetCacheFile('notes.svg')
        if not up_to_date:
            ABCToPostscript(abc, svg=True, target=target)
        
        return target
        
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
        target, up_to_date = self._GetCacheFile('notes.eps')
        if not up_to_date:
            ABCToPostscript(abc, eps=True, target=target)
        
        return target
        
    def MakeNotesPNGFile(self):
        
        eps_file = self.MakeNotesEPSFile()
        png_file, up_to_date = self._GetCacheFile('notes.png')
        if up_to_date:
            return png_file
        
        bin_dir = '%s/bin' % kBaseDir
        cmd = 'PATH=$PATH:%s convert -density 600 -depth 8 -monochrome %s %s' % (bin_dir, eps_file, png_file)
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
        filename, up_to_date = self._GetCacheFile('chords.eps')
        if not up_to_date:
            renderPS.drawToFile(drawing, filename)
        
        return filename
        
    def _GetCacheFile(self, basename):
        
        dirname = os.path.join(kCacheLoc, 'tune', self.type)
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
        if title.lower().startswith('the '):
            title = title[4:]
        elif title.lower().startswith('a '):
            title = title[2:]
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
    
        notes_width = 3.25*inch
        chords_width = 3.75*inch
        
        story=[]
        
        for i, tune in enumerate(self.tunes):

            fulltitle = tune.title + ' - ' + tune.type.capitalize() + ' - ' + tune._FullKey()
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
                ttype = self.tunes[0].Type()
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
        self.date = time.strftime("%d %B %Y %H:%M:%S", time.localtime())
        self.contact = 'http://cambridgeny.net/music'
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
            
    def GeneratePDF(self, type_in_header=False, include_index=True):
            
        target, up_to_date = self._GetCacheFile('.pdf')
        if up_to_date:
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
            
            fulltitle = tune.title + ' - ' + tune.type.capitalize() + ' - ' + tune._FullKey()
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
        
        return fn, not kDebugBookGeneration
        
class CSetBook(CBook):
    
    def __init__(self, name, title, subtitle, tunes):
        self.title = title
        self.subtitle = subtitle
        self.date = time.strftime("%d %B %Y %H:%M:%S", time.localtime())
        self.contact = 'http://cambridgeny.net/music'
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

def GetTuneIndex(include_incomplete):
    idx = {}

    incomplete_tunes = []
    for section, section_name in kSections:
        if section == 'incomplete':
            continue
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
                if not include_incomplete and (not tune.chords or not tune.notes):
                    continue
                title = tune.title
                if title.lower().startswith('the '):
                    title = title[4:]
                elif title.lower().startswith('a '):
                    title = title[2:]
                pfx = ''
                if not tune.chords.strip() or not tune.notes.strip():
                    title = tune.Type() + ': ' + title
                    incomplete_tunes.append((title, name))
                else:
                    tunes.append((title, name))

        tunes.sort()
        
        idx[section] = tunes

    if incomplete_tunes:
        incomplete_tunes.sort()
        idx['incomplete'] = incomplete_tunes
    
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

def ABCToPostscript(abc, svg=False, eps=False, target=None):

    f, fn = tempfile.mkstemp(suffix='.abc')
    f = os.fdopen(f, 'w')
    f.write(abc)
    f.close()

    if svg:
        svg_arg = '-X -m 0 -w 4in'
        if target is None:
            target = os.path.splitext(fn)[0] + '.svg'
    elif eps:
        svg_arg = '-E -m 0 -w 3.75in'
        if target is None:
            target = os.path.splitext(fn)[0] + '.eps'
    else:
        svg_arg = ''
        if target is None:
            target = os.path.splitext(fn)[0] + '.ps'
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
    os.system(cmd)

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
    
def error(txt):
    print(txt)
    sys.exit(1)
    

