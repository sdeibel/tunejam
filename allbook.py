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
        self.contact = 'http://cambridgeny.net/music'
        self.name = 'all-by-section'
        self.url = self.name
    
        self.pages = []
        for section, section_name in utils.kSections:
            if section == 'incomplete':
                continue
            try:
                files = os.listdir(os.path.join(utils.kDatabaseDir, section))
            except OSError:
                continue
            tunes = []
            for fn in files:
                if fn.endswith('.spec'):
                    name = fn[:-len('.spec')]
                    tune = utils.CTune(name)
                    tune.ReadDatabase()
                    if not tune.chords or not tune.notes:
                        continue
                    title = tune.title
                    if title.lower().startswith('the '):
                        title = title[4:]
                    elif title.lower().startswith('a '):
                        title = title[2:]
                    tunes.append((title, name))
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
        self.contact = 'http://cambridgeny.net/music'
        self.name = 'all-by-time'
        self.url = self.name
    
        self.pages = []
        for section_name, types in utils.kTimeSignatures:
            all_files = []
            for section in types:
                try:
                    files = os.listdir(os.path.join(utils.kDatabaseDir, section))
                    files = [os.path.join(utils.kDatabaseDir, section, f) for f in files if f.endswith('.spec')]
                    all_files.extend(files)
                except OSError:
                    continue
            tunes = []
            for fn in all_files:
                name = os.path.basename(fn)[:-len('.spec')]
                tune = utils.CTune(name)
                tune.ReadDatabase()
                if not tune.chords or not tune.notes:
                    continue
                title = tune.title
                if title.lower().startswith('the '):
                    title = title[4:]
                elif title.lower().startswith('a '):
                    title = title[2:]
                tunes.append((title, name))
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
        self.contact = 'http://cambridgeny.net/music'
        self.name = 'all'
        self.url = self.name

        tunes = []
        for section, section_name in utils.kSections:
            if section == 'incomplete':
                continue
            try:
                files = os.listdir(os.path.join(utils.kDatabaseDir, section))
            except OSError:
                continue
            for fn in files:
                if fn.endswith('.spec'):
                    name = fn[:-len('.spec')]
                    tune = utils.CTune(name)
                    tune.ReadDatabase()
                    if not tune.chords or not tune.notes:
                        continue
                    title = tune.GetSortTitle()
                    tunes.append((title, name))
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
