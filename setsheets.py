# Generate cheat sheets for sets of tunes
# Written by Stephan R.A. Deibel
# Jan 2015

import os, sys
import tempfile

kExecutable = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bin/abcm2ps')
kDatabaseDir = os.path.join(os.path.dirname(__file__), 'db')

def error(txt):
    print(error)
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
        return self.type.capitalize()
    
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
%%%%rightmargin 11.5cm
%(notes)s
%%%%multicol new
%%%%textfont Monaco
%%%%leftmargin 11.5cm
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
    
    def __init__(self, names=[]):

        self.type = None
        self.tunes = []
        
        types = set()
        for name in names:
            obj = CTune(name)
            obj.ReadDatabase()
            types.add(obj.Type())
            self.tunes.append(obj)
            
        if len(types) > 1:
            self.type = "Mixed"
        else:
            self.type = types.pop()
            
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

%%%%scale 1.4
%%%%begintext
%s
%%%%endtext

""" % self.type.capitalize()

        parts = [kStart]
        for i, tune in enumerate(self.tunes):
            parts.append('\nX:%i\n'%i)
            parts.append(tune.MakeCardSmall())
            
        return ''.join(parts)

def GenerateLargeSheets(tunes):

    set = CTuneSet(tunes)

    abc = set.MakeNotesLarge()
    notes = __ABCToPostscript(abc)
    
    abc = set.MakeChordsLarge()
    chords = __ABCToPostscript(abc)
    
    return notes, chords

def GenerateSmallSheet(tunes):
    
    set = CTuneSet(tunes)
    abc = set.MakeCardSmall()
    
    return __ABCToPostscript(abc)

def __ABCToPostscript(abc):
    
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

    
if __name__ == '__main__':
    args = sys.argv[1:]

    if '--large' in args:
        args.remove('--large')
        notes, chords = GenerateLargeSheets(args)
        cmd = 'open %s %s' % (notes, chords)
        os.system(cmd)
    else:
        sheet = GenerateSmallSheet(args)
        cmd = 'open %s' % sheet
        os.system(cmd)
