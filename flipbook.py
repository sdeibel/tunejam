# Generate a flip book for making tune sets

import time
from setsheets import *
import utils

class CFlipBook(utils.CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'Set Flip Book'
        self.type_in_header = True
        self.date = time.strftime("%d %B %Y %H:%M:%S", time.localtime())
        self.contact = 'http://cambridgeny.net/music'
        self.name = 'flip'
        self.url = self.name
    
        self.pages = []
        for section, section_name in utils.kSections:
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
                    title = tune.title
                    if title.lower().startswith('the '):
                        title = title[4:]
                    elif title.lower().startswith('a '):
                        title = title[2:]
                    tunes.append((title, name))
            tunes.sort()
            
            for title, name in tunes:
                page_tunes = [name, name, name]
                title = [self.title, self.subtitle, self.date]
                title = [t.strip() for t in title]
                title = '%s - %s\\n%s' % tuple(title)
                tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
                self.pages.append(tuneset)

    #def GenerateSmall(self):
        #pages = []
        #for page in self.pages:
            #abc = page.MakeFlipBook()
            #pages.append(utils.ABCToPostscript(abc))

        #return pages


if __name__ == '__main__':
    
    book = CFlipBook()
    pages = book.GenerateSmall()

    import time
    time.sleep(10.0)
    
    cmd = 'open %s' % ' '.join(pages)
    os.system(cmd)
