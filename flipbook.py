# Generate a flip book for making tune sets

from setsheets import *

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

class CFlipBook(CBook):

    def __init__(self):
        
        self.title = 'Hubbard Hall Tune Jam'
        self.subtitle = 'Set Flip Book'
        self.date = 'DRAFT February 4, 2015 DRAFT'
        self.contact = 'http://cambridgeny.net/music'
    
        self.pages = []
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
            
            for title, name in tunes:
                page_tunes = [name, name, name]
                title = [self.title, self.subtitle, self.date]
                title = [t.strip() for t in title]
                title = '%s - %s\\n%s' % tuple(title)
                tuneset = CTuneSet(page_tunes, title, self.contact, '')
                self.pages.append(tuneset)

    def GenerateSmall(self):
        pages = []
        for page in self.pages:
            abc = page.MakeFlipBook()
            pages.append(ABCToPostscript(abc))

        return pages


if __name__ == '__main__':
    
    book = CFlipBook()
    pages = book.GenerateSmall()

    import time
    time.sleep(10.0)
    
    cmd = 'open %s' % ' '.join(pages)
    os.system(cmd)
