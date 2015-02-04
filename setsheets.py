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

    def MakeFlipBook(self, pos):
        """Generate form of cheat sheet card used in flip book"""

        if pos > 0:
            spacer = '\n'
        else:
            spacer = ''
            
        kFormat = """%%%%textfont Times-Roman
%%%%scale 5.0
T:%(tune_type)s: %(title)s - %(fullkey)s
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
%%%%rightmargin 0.5in
%%%%scale 0.8
%%%%begintext right
%(spacer)s%(chords)s
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
        d['spacer'] = spacer
        d['notes'] = notes
        d['vspacer'] = '\n' * 9
        d['tune_type'] = self.type.capitalize()

        return kFormat % d

    def __FullKey(self):
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

def GenerateLargeSheets(tunes):

    set = CTuneSet(tunes)

    abc = set.MakeNotesLarge()
    notes = ABCToPostscript(abc)
    
    abc = set.MakeChordsLarge()
    chords = ABCToPostscript(abc)
    
    return notes, chords

def GenerateSmallSheet(tunes):
    
    set = CTuneSet(tunes)
    abc = set.MakeCardSmall()
    
    return ABCToPostscript(abc)

def ABCToPostscript(abc):
    
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

    os.remove(fn)
    return ps_fn

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
            setnum = 'Set %i' % set_num
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
    
    def GenerateSmall(self):
        pages = []
        for page in self.pages:
            abc = page.MakeCardSmall()
            pages.append(ABCToPostscript(abc))
            
        return pages
        
        
if __name__ == '__main__':
    args = sys.argv[1:]

    # Generating a book
    if '--book' in args:
        args.remove('--book')
        if '--large' in args:
            args.remove('--large')
            name = args[0]
            book = CBook(name, large=True)
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
