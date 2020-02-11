# Generate a flip book for making tune sets

import time
from setsheets import *
import utils

class CFlipBook(utils.CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'Set Flip Book - By Type'
        self.type_in_header = True
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = 'flip'
        self.url = self.name
    
        files = os.listdir(utils.kDatabaseDir)
        files = [os.path.join(utils.kDatabaseDir, f) for f in files if f.endswith('.spec')]

        self.pages = []
        for section, section_name, class_name in utils.kSections:
            if section == 'incomplete':
                continue
            tunes = set()
            for fn in files:
                name = os.path.basename(fn[:-len('.spec')])
                tune = utils.CTune(name)
                tune.ReadDatabase()
                if not tune.chords or not tune.notes:
                    continue
                if section not in tune.klass:
                    continue
                title = tune.GetSortTitle()
                tunes.add((title, name))
                
            tunes = list(tunes)
            tunes.sort()
            
            for title, name in tunes:
                page_tunes = [name, name, name]
                title = [self.title, self.subtitle, self.date]
                title = [t.strip() for t in title]
                title = '%s - %s - %s' % tuple(title)
                tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
                self.pages.append(tuneset)

class CFlipBookByTime(utils.CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'Set Flip Book - By Time Signature'
        self.type_in_header = True
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = 'flip-by-time'
        self.url = self.name
    
        files = os.listdir(utils.kDatabaseDir)
        files = [os.path.join(utils.kDatabaseDir, f) for f in files if f.endswith('.spec')]

        self.pages = []
        for section_name, types in utils.kTimeSignatures:
            tunes = set()
            for fn in files:
                name = os.path.basename(fn)[:-len('.spec')]
                tune = utils.CTune(name)
                tune.ReadDatabase()
                if not tune.chords or not tune.notes:
                    continue
                if not any(k in types for k in tune.klass.split(',')):
                    continue
                title = tune.GetSortTitle()
                tunes.add((title, name))
                
            tunes = list(tunes)
            tunes.sort()
            
            for title, name in tunes:
                page_tunes = [name, name, name]
                title = [self.title, section_name, self.date]
                title = [t.strip() for t in title]
                title = '%s - Set Flip Book - %s - %s' % tuple(title)
                tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
                self.pages.append(tuneset)

if __name__ == '__main__':
    
    book = CFlipBook()
    pages = book.GenerateSmall()

    import time
    time.sleep(10.0)
    
    cmd = 'open %s' % ' '.join(pages)
    os.system(cmd)
