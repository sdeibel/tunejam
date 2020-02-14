# Generate a book containg full sheet music

import time
from setsheets import *
import utils

class CSheetBook(utils.CBook):

  def __init__(self, tunes, title='', subtitle=''):

    if len(tunes) == 1:
      tune = utils.CTune(tunes[0])
      tune.ReadDatabase()
      self.title = tune.title
      if tune.author:
        self.subtitle = tune.author
      else:
        self.subtitle = ''
      link_name = tune.name
      page_title = ''
    else:
      self.title = title
      self.subtitle = subtitle
      link_name = 'all'
      page_title = title
      
    self.type_in_header = False
    self.date = time.strftime("%d %B %Y", time.localtime())

    self.contact = 'http://music.cambridgeny.net/sheet/print/%s' % link_name
    self.name = 'sheet-%s' % link_name
    self.url = 'sheet/print/%s' % link_name

    self.pages = []
    for name in tunes:
      tune = utils.CTune(name)
      tune.ReadDatabase()
      title = [tune.title, self.date]
      title = [t.strip() for t in title]
      title = '%s - %s' % tuple(title)
      if len(tunes) == 1:
        page_ref = 'http://music.cambridgeny.net/sheet/print/%s' % name
      else:
        page_ref = 'http://music.cambridgeny.net/sheet/print/all'
      page = utils.CSheetPage(name, page_title, page_ref, len(tunes) >1)
      self.pages.append(page)
