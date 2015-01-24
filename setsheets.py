# Generate cheat sheets for sets of tunes
# Written by Stephan R.A. Deibel
# Jan 2015

import os, sys
import tempfile

kExecutable = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin/abcm2ps')
kDatabaseDir = os.path.join(os.path.dirname(__file__), 'db')

def error(txt):
    print(txt)
    sys.exit(1)
    
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
                self.notes += spec + line
                notes_part += 1
    
            elif part == 2:
                self.chords += line
    
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
                
        d['fullkey'] = self.__FullKey()
                
        return d
                
    def Type(self):
        if self.type == 'waltz':
            return 'Waltzes'
        else:
            return self.type.capitalize() + 's'
    
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
%%%%scale 2.2
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
%%%%leftmargin 3.75in
%%%%scale 1.2
%%%%begintext

%(chords)s
%%%%endtext
%%%%multicol end
"""

        notes = self.__NotesWithMeterOnEachLine()
        d = self.AsDict().copy()
        d['notes'] = notes
    
        return kFormat % d

    def __FullKey(self):
        key = self.key
        if key.lower().find('modal') > 0:
            pass
        elif key.endswith('m'):
            key = key[:-1] + ' Minor'
        else:
            key = key + ' Major'
        return key

    def __NotesWithMeterOnEachLine(self):
        notes = self.notes.splitlines()
        notes = [n + '\n' for n in notes]
        meter = 'M:%s\n' % self.meter
        notes = meter.join(notes)
        return notes
        
class CTuneSet:
    
    def __init__(self, names=[], header='', footer=''):

        self.type = None
        self.tunes = []
        self.header = header
        self.footer = footer
        
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
        
        kStart = """%%%%scale 2.0
%%%%begintext
%s
%%%%endtext

""" % self.type
        
        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('X:%i\n'%i)
            parts.append(tune.MakeNotesLarge())
    
        return ''.join(parts)

    def MakeChordsLarge(self):

        kStart = """%%%%scale 2.0
%%%%begintext
%s
%%%%endtext

""" % self.type

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\n')
            if i > 0:
                prepend_title = '\n'
            else:
                prepend_title = ''
            parts.append(tune.MakeChordsLarge(prepend_title))

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

""" % (self.header, self.footer, self.type.capitalize())

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeCardSmall())
            
        return ''.join(parts)

def GenerateLargeSheets(tunes):

    set = CTuneSet(tunes)

    abc = set.MakeNotesLarge()
    notes = _ABCToPostscript(abc)
    
    abc = set.MakeChordsLarge()
    chords = _ABCToPostscript(abc)
    
    return notes, chords

def GenerateSmallSheet(tunes):
    
    set = CTuneSet(tunes)
    abc = set.MakeCardSmall()
    
    return _ABCToPostscript(abc)

def _ABCToPostscript(abc):
    
    f, fn = tempfile.mkstemp(suffix='.abc')
    f = os.fdopen(f, 'w')
    f.write(abc)
    f.close()

    ps_fn = os.path.splitext(fn)[0] + '.ps'
    cmdline = [kExecutable, fn, '-O', ps_fn]
    cmdline = ' '.join(cmdline)

    os.system(cmdline)
    if not os.path.exists(ps_fn):
        error("Could not create Postscript file %s" % ps_fn)

    return ps_fn

class CBook:
    
    def __init__(self, name):
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
        for i, line in enumerate(lines[5:]):
            if not line.strip():
                continue
            tunes = line.split()
            title = [self.title, self.subtitle, self.date, 'Page %i' % (len(
    self.pages) + 1)]
            title = [t.strip() for t in title]
            title = '%s - %s\\n%s - %s' % tuple(title)
            tuneset = CTuneSet(tunes, title, self.contact)
            self.pages.append(tuneset)
            
    def GenerateLarge(self):
        pages = []
        for page in self.pages:
            abc = page.MakeNotesLarge()
            notes = _ABCToPostscript(abc)
            abc = page.MakeChordsLarge()
            chords = _ABCToPostscript(abc)
            pages.extend([notes, chords])
            
        return pages
    
    def GenerateSmall(self):
        pages = []
        for page in self.pages:
            abc = page.MakeCardSmall()
            pages.append(_ABCToPostscript(abc))
            
        return pages
        
        
if __name__ == '__main__':
    args = sys.argv[1:]

    # Generating a book
    if '--book' in args:
        args.remove('--book')
        if '--large' in args:
            args.remove('--large')
            name = args[0]
            book = CBook(name)
            pages = book.GenerateLarge()
        else:
            name = args[0]
            book = CBook(name)
            pages = book.GenerateSmall()

        cmd = 'open %s' % ' '.join(pages)
        os.system(cmd)

    # Generating a single pair of large-format pages
    elif '--large' in args:
        args.remove('--large')
        notes, chords = GenerateLargeSheets(args)
        cmd = 'open %s %s' % (notes, chords)
        os.system(cmd)
        
    # Generating a single small format page
    else:
        sheet = GenerateSmallSheet(args)
        cmd = 'open %s' % sheet
        os.system(cmd)
