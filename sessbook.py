# Generate a flip book for making tune sets

import time
from setsheets import *
import utils

class CEventBook(utils.CBook):

  def __init__(self, event):

    assert isinstance(event, utils.CEvent)
    
    self.title = event.title
    self.subtitle = ''
    self.type_in_header = False
    self.date = time.strftime("%d %B %Y", time.localtime())
    self.contact = 'http://music.cambridgeny.net/event/%s' % event.name
    self.name = 'event-%s' % event.name
    self.url = 'event/%s' % event.name

    self.pages = []
    for tunes in event.sets:
      page_tunes = tunes.split('&')
      title = [self.title, self.date]
      title = [t.strip() for t in title]
      title = '%s - %s' % tuple(title)
      tuneset = utils.CTuneSet(page_tunes, title, self.contact, '')
      self.pages.append(tuneset)
