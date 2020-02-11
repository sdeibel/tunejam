# Generate a book of all the sets, sorted by category and alphabetically

import time

from setsheets import *
import utils

class CAllBookBySection(utils.CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'All Tunes - By Type'
        self.type_in_header = True
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = 'all-by-section'
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

            for i in range(0, len(tunes), 3):
                page_tunes = [tunes[i][1]]
                if i + 1 < len(tunes):
                    page_tunes.append(tunes[i+1][1])
                if i + 2 < len(tunes):
                    page_tunes.append(tunes[i+2][1])
                title = [self.title, self.subtitle, self.date]
                title = [t.strip() for t in title]
                title = '%s - %s - %s' % tuple(title)
                tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
                self.pages.append(tuneset)
                
    def GeneratePDF(self, generate=False):
        return utils.CBook.GeneratePDF(self, type_in_header=True, generate=generate)
        
class CAllBookByTime(utils.CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'All Tunes - By Time Signature'
        self.type_in_header = True
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = 'all-by-time'
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

            for i in range(0, len(tunes), 3):
                page_tunes = [tunes[i][1]]
                if i + 1 < len(tunes):
                    page_tunes.append(tunes[i+1][1])
                if i + 2 < len(tunes):
                    page_tunes.append(tunes[i+2][1])
                title = [self.title, section_name, self.date]
                title = [t.strip() for t in title]
                title = '%s - %s - %s' % tuple(title)
                tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
                self.pages.append(tuneset)
                
    def GeneratePDF(self, generate=False):
        return utils.CBook.GeneratePDF(self, type_in_header=False, generate=generate)
        
class CAllBook(utils.CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'All Tunes - Alphabetical'
        self.date = time.strftime("%d %B %Y", time.localtime())
        self.contact = 'http://music.cambridgeny.net'
        self.name = 'all'
        self.url = self.name

        files = os.listdir(utils.kDatabaseDir)
        files = [os.path.join(utils.kDatabaseDir, f) for f in files if f.endswith('.spec')]

        tunes = set()
        for section, section_name, class_name in utils.kSections:
            if section == 'incomplete':
                continue
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

        self.pages = []
        for i in range(0, len(tunes), 3):
            page_tunes = [tunes[i][1]]
            if i + 1 < len(tunes):
                page_tunes.append(tunes[i+1][1])
            if i + 2 < len(tunes):
                page_tunes.append(tunes[i+2][1])
            title = [self.title, self.subtitle, self.date]
            title = [t.strip() for t in title]
            title = '%s - %s - %s' % tuple(title)
            tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
            self.pages.append(tuneset)
            
if __name__ == '__main__':
    
    book = CAllBook()
    pages = book.GenerateSmall()

    import time
    time.sleep(10.0)
    
    cmd = 'open %s' % ' '.join(pages)
    os.system(cmd)
