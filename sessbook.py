# Generate a flip book for making tune sets

import time
from setsheets import *
import utils

class CSessionBook(utils.CBook):

  def __init__(self, session):

    assert isinstance(session, utils.CSession)
    
    self.title = session.title
    self.subtitle = ''
    self.type_in_header = False
    self.date = time.strftime("%d %B %Y", time.localtime())
    self.contact = 'http://music.cambridgeny.net/session/%s' % session.name
    self.name = 'session-%s' % session.name
    self.url = 'session/%s' % session.name

    self.pages = []
    for tunes in session.sets:
      page_tunes = tunes.split('&')
      title = [self.title, self.date]
      title = [t.strip() for t in title]
      title = '%s - %s' % tuple(title)
      tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
      self.pages.append(tuneset)
