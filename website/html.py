#########################################################################
""" html.py    -- Simple HTML generation utils

Copyright (c) 1999-2002, Archaeopteryx Software, Inc.  All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to permit
persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
#########################################################################

import string

#-----------------------------------------------------------------------
def MakeHTMLColor(color):

  if type(color) is type(()):
    color_str = "#%02x%02x%02x" % color
  else:
    color_str = str(color)
    if color_str[0] != '#':
      color_str = '#' + color
  return color_str
  
#-----------------------------------------------------------------------
class CTag:
  """
  tag=tagname
  body=text to place between <tag> and </tag>
  item_sep=separator to apply to subsequently append()'ed body
  attribs=hclass, id
  """

  kNewlineTags = ('html', 'head', 'title', 'div', 'p', 'ul', 'li')
  kOrphanTags = ('meta', 'img', 'input', 'hr')
  kAttribOnlyTags = ('nowrap',)
  
  def __init__(self, tag='', body=None, item_sep='', **attribs):
    
    self.item_sep = item_sep
    self.body = []
    
    anames = attribs.keys()[:]
    anames.sort()
    if attribs.has_key('id'):
      anames.remove('id')
      if attribs['id'] is not None:
        anames.insert(0, 'id')
    if attribs.has_key('hclass'):
      anames.remove('hclass')
      if attribs['hclass'] is not None:
        anames.insert(0, 'class')      
        attribs['class'] = attribs['hclass']
      del attribs['hclass']

    if attribs.has_key('bgcolor'):
      attribs['bgcolor'] = MakeHTMLColor(attribs['bgcolor'])
    if attribs.has_key('fgcolor'):
      attribs['fgcolor'] = MakeHTMLColor(attribs['fgcolor'])

    tattribs = []
    for a in anames:
      if a not in self.kAttribOnlyTags:
        tattribs.append('%s="%s"' % (a.replace('_', '-'), str(attribs[a])))
      else:
        tattribs.append(a)
    tattribs = ' '.join(tattribs)
    if len(tattribs) > 0:
      tattribs = ' ' + tattribs

    if tag in self.kOrphanTags:
      start_slash = ' /'
    else:
      start_slash = ''
    self.start = '<%s%s%s>' % (tag, tattribs, start_slash)
    self.end = '</%s>' % tag
    if tag in self.kNewlineTags:
      self.start = '\n%s\n' % self.start
      self.end = '\n%s\n' % self.end

    if tag in self.kOrphanTags:
      self.end = ''
      
    self.append(body)
      
  def append(self, body):
    if body is not None:
      if type(body) in (type(()), type([])):
        self.body.extend(body)
      else:
        self.body.append(body)
    
  def __str__(self):
    return self.start + self.item_sep.join([str(x) for x in self.body]) + self.end
    
#-----------------------------------------------------------------------
class CHTML(CTag):
  
  def __init__(self, body=None, **attribs):
    CTag.__init__(self, 'html', body, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CHead(CTag):
  
  def __init__(self, body=None, **attribs):
    CTag.__init__(self, 'head', body, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CTitle(CTag):
  
  def __init__(self, body=None, **attribs):
    CTag.__init__(self, 'title', body, **attribs)

#-----------------------------------------------------------------------
class CDiv(CTag):
  """Attribs: hclass, id"""
    
  def __init__(self, body=None, **attribs):
    self.div_id = attribs.get('id', None)
    CTag.__init__(self, 'div', body, '\n', **attribs)
    
  def __str__(self):
    if self.div_id is not None:
      return CTag.__str__(self) + "  <!-- %s -->\n" % self.div_id
    else:
      return CTag.__str__(self) + '\n'

#-----------------------------------------------------------------------
class CIFrame(CTag):
  """Attribs: hclass, id"""
    
  def __init__(self, body=None, **attribs):
    self.frame_id = attribs.get('id', None)
    CTag.__init__(self, 'iframe', body, '\n', **attribs)
    
  def __str__(self):
    return CTag.__str__(self) + '\n'
    
#-----------------------------------------------------------------------
class CSpan(CTag):
  """Attribs: hclass, id"""
  
  def __init__(self, body=None, **attribs):
    CTag.__init__(self, 'span', body, **attribs)
    
#-----------------------------------------------------------------------
class CMeta(CTag):
  """Attribs:  hclass, id, name, http_equiv"""
    
  def __init__(self, body, **attribs):
    attribs['content'] = body
    CTag.__init__(self, 'meta', **attribs)
    
#-----------------------------------------------------------------------
class CExtStyle(CTag):
  
  def __init__(self, style_sheet):    
    CTag.__init__(self, 'style', " @import url(%s);" % style_sheet, type="text/css")

#-----------------------------------------------------------------------
class CBody(CTag):
  """Attribs:  hclass, id, bgcolor"""
  def __init__(self, body=None, **attribs):
    CTag.__init__(self, 'body', body, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CTable(CTag):
  """Attribs: hclass, id, width=99%, border=0, cellpadding=0, cellspacing=0, bgcolor"""

  def __init__(self, body=None, **attribs):

    # Common defaults
    if not attribs.has_key('cellpadding'):
      attribs['cellpadding'] = 0
    if not attribs.has_key('cellspacing'):
      attribs['cellspacing'] = 0
    if not attribs.has_key('border'):
      attribs['border'] = 0
    if not attribs.has_key('width'):
      attribs['width'] = '99%'
    elif attribs['width'] is None:
      del attribs['width']
      
    CTag.__init__(self, 'table', body, '\n', **attribs)

  def append(self, body):
    if body is None:
      return
    if not isinstance(body, CTR):
      if type(body) in (type(()), type([])):
        def ensure_tr(x):
          if isinstance(x, CTR):
            return x
          else:
            return CTR(x)
        body = map(ensure_tr, body)
      else:
        body = CTR(body)
    CTag.append(self, body)
    
#-----------------------------------------------------------------------
class CTR(CTag):
  """Attribs: align (left, right), valign (top, bottom), bgcolor"""
  
  def __init__(self, body=None, **attribs):
    
    CTag.__init__(self, 'tr', body, **attribs)

  def append(self, body):
    if body is None:
      return
    if type(body) in (type(()), type([])):
      def ensure_td(x):
        if isinstance(x, CTD):
          return x
        else:
          return CTD(x)
      body = map(ensure_td, body)
    elif not isinstance(body, CTD):
      body = CTD(body)
    CTag.append(self, body)
    
#-----------------------------------------------------------------------
class CTD(CTag):
  """Attribs: colspan, rowspan, align (left, right), valign (top, bottom),
  nowrap, background (image), height, width"""
  
  def __init__(self, body=None, **attribs):
    
    CTag.__init__(self, 'td', body, **attribs)

#-----------------------------------------------------------------------
class CTH(CTD):
  """Attribs: colspan, rowspan, align, valign, nowrap, background (image),
  height, width"""

  def __init__(self, body=None, **attribs):
    
    CTag.__init__(self, 'th', body, **attribs)
  
#-----------------------------------------------------------------------
class CH(CTD):
  """Heading <H#></H#>.  Attribs: hclass, id, title_level"""
  
  def __init__(self, body, title_level, **attribs):

    CTag.__init__(self, 'th', body, **attribs)

    if attribs.has_key('hclass') and attribs['hclass'] is not None:
      hclass = ' class="%s"' % attribs['hclass']
    else:
      hclass = ''
    if attribs.has_key('id'):
      id = ' id="%s"' % attribs['id']
    else:
      id = ''
      
    self.start = '<h%i%s%s>' % (title_level, hclass, id)
    self.end = '</h%i>' % title_level
    
  def __str__(self):
    return self.start + ''.join([str(b) for b in self.body]) + self.end
    
#-----------------------------------------------------------------------
class CText(CTag):
  """Used for bits of text with local styling.  Attribs: hclass, id, font, 
  size, color, href, onclick, bold, italic, underline, title_level.  Better to use
  CDiv()."""
  
  def __init__(self, body, **attribs):

    if type(body) in (list, tuple):
      body = ''.join([str(s) for s in body])
      
    if attribs.has_key('hclass') and attribs['hclass'] is not None:
      hclass = ' class="%s"' % attribs['hclass']
    else:
      hclass = ''
    if attribs.has_key('id') and attribs['id'] is not None:
      id = ' id="%s"' % attribs['id']
    else:
      id = ''
      
    nospan = 'nospan' in attribs
    if nospan:
      del attribs['nospan']
      
    start = []
    if not nospan and (hclass != '' or id != ''):
      start.append('<span%s%s>' % (hclass, id))
    
    if attribs.has_key('onclick') and attribs['onclick']:
      onclick = ' onClick="%s"' % attribs['onclick']
    else:
      onclick = ''

    if attribs.has_key('href') and attribs['href']:
      start.append('<a href="%s"%s%s%s>' % (attribs['href'], hclass, id, onclick))
    if attribs.has_key('hname'):
      start.append('<a name="%s">' % attribs['hname'])
    if attribs.has_key('title_level'):
      start.append('<h%s%s%s>' % (attribs['title_level'], hclass, id))
    had_font = 0
    if attribs.has_key('font') or attribs.has_key('size') or attribs.has_key('color'):
      start.append('<font')
      if attribs.has_key('font'):
        start.append(' name="%s"' % attribs['font'])
        del attribs['font']
      if attribs.has_key('size'):
        start.append(' size="%s"' % str(attribs['size']))
        del attribs['size']
      if attribs.has_key('color'):
        start.append(' color="%s"' % attribs['color'])
        del attribs['color']
      start.append('>')
      had_font = 1
    if attribs.get('bold', 0):
      start.append('<b>')
    if attribs.has_key('italic'):
      start.append('<i>')
    if attribs.has_key('underline'):
      start.append('<u>')
        
    end = []
    if attribs.has_key('underline'):
      end.append('</u>')
      del attribs['underline']
    if attribs.has_key('italic'):
      end.append('</i>')
      del attribs['italic']
    if attribs.has_key('bold'):
      end.append('</b>')
      del attribs['bold']
    if had_font:
      end.append('</font>')
    if attribs.has_key('title_level'):
      end.append('</h%s>' % attribs['title_level'])
      del attribs['title_level']
    if attribs.has_key('hname'):
      end.append('</a>')
      del attribs['hname']
    if attribs.has_key('href'):
      end.append('</a>')
      del attribs['href']
    if not nospan and (hclass != '' or id != ''):
      end.append('</span>')
    
    self.body = ''.join(start) + str(body) + ''.join(end)
    
  def __str__(self):
    return self.body
    
#-----------------------------------------------------------------------
class CBreak(CTag):
  """Manually inserted body break.  Attribs: skip, rule_size.  Better
  to use CHR an CSS styles."""
  
  def __init__(self, skip=1, rule_size=0, hclass=''):

    if hclass:
      hclass = ' class="%s"' % hclass
    else:
      hclass = ''
    if rule_size > 0:
      rule = '<hr noshade size="%s"%s>' % (str(rule_size), hclass)
    else:
      rule = ''
    self.body = '%s\n%s\n' % (('<br %s/>' % hclass) * skip, rule)

  def __str__(self):
    return self.body

#-----------------------------------------------------------------------
class CHR(CTag):
  """Horizontal rule, usually hidden in styled pages"""

  def __init__(self, **attribs):
    CTag.__init__(self, 'hr', None, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CParagraph(CTag):
  
  def __init__(self, body, **attribs):
    CTag.__init__(self, 'p', body, '\n', **attribs)

#-----------------------------------------------------------------------
class CNBSP:
  
  def __init__(self, count=1):
    self.body = '&nbsp;' * count
    
  def __str__(self):
    return self.body

#-----------------------------------------------------------------------
class CAcronym(CTag):
  """Attribs: colspan, rowspan, align, valign, nowrap, background (image),
  height, width"""

  def __init__(self, text, title, **attribs):

    attribs['title'] = title
    CTag.__init__(self, 'acronym', text, **attribs)
  
#-----------------------------------------------------------------------
class CImage(CTag):
  """Attribs: class, id, src, alt, width, height, border=0, href, onclick"""
  
  def __init__(self, **attribs):

    href = attribs.get('href')
    if href is not None:
      del attribs['href']
    self.href = href
    onclick = attribs.get('onclick')
    if onclick is not None:
      del attribs['onclick']
    self.onclick = onclick
    onmouseover = attribs.get('onmouseover')
    if onmouseover is not None:
      del attribs['onmouseover']
    self.onmouseover = onmouseover
    onmouseout = attribs.get('onmouseout')
    if onmouseout is not None:
      del attribs['onmouseout']
    self.onmouseout = onmouseout
    if not attribs.has_key('border'):
      attribs['border'] = 0
    self.hclass = attribs.get('hclass')
    self.id = attribs.get('id')

    CTag.__init__(self, 'img', **attribs)

  def __str__(self):
    img = CTag.__str__(self)
    if self.href is not None:
      hattribs = []
      if self.onclick is not None:
        hattribs.append('onclick="%s"' % self.onclick)
      if self.onmouseover is not None:
        hattribs.append('onmouseover="%s"' % self.onmouseover)
      if self.onmouseout is not None:
        hattribs.append('onmouseout="%s"' % self.onmouseout)
      if self.hclass is not None:
        hattribs.append('class="%s"' % self.hclass)
      if self.id is not None:
        hattribs.append('id="%s"' % self.id)        
      hattribs = ' '.join(hattribs)
      if len(hattribs) > 0:
        hattribs = ' ' + hattribs
      img = '<a href="%s"%s>%s</a>' % (self.href, hattribs, img)
    return img
  
#-----------------------------------------------------------------------
class CTBody(CTag):
  def __init__(self, body, **attribs):
    CTag.__init__(self, 'tbody', body, **attribs)
    
#-----------------------------------------------------------------------
class CColGroup(CTag):
  def __init__(self, body, **attribs):
    CTag.__init__(self, 'colgroup', body, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CCol(CTag):
  """Attribs: hclass, id"""
  def __init__(self, body=None, **attribs):
    CTag.__init__(self, 'col', body, '\n', **attribs)

#-----------------------------------------------------------------------
class CForm(CTag):
  """Attribs: hclass, id, action, method"""
  def __init__(self, body, **attribs):
    CTag.__init__(self, 'form', body, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CLabel(CTag):
  """Attribs: hfor (replaced w/ 'for')"""
  def __init__(self, label, **attribs):
    
    if attribs.has_key('hfor'):
      attribs['for'] = attribs['hfor']
      del attribs['hfor']
    CTag.__init__(self, 'label', label, '\n', **attribs)
    
#-----------------------------------------------------------------------
class CInput(CTag):
  """Attribs: hclass, id, type, size, maxlength, name, value, onclick"""
  def __init__(self, **attribs):
    self.checked = 0
    if attribs.has_key('checked'):
      self.checked = attribs['checked']
      del attribs['checked']
    if not attribs.has_key('hclass') and attribs.has_key('type'):
      attribs['hclass'] = attribs['type']
    if attribs.has_key('onclick'):
      attribs['onClick'] = attribs['onclick']
      del attribs['onclick']
    CTag.__init__(self, 'input', None, '\n', **attribs)

  def __str__(self):
    s = CTag.__str__(self)
    if self.checked:
      s = s[:-2] + ' checked />'
    return s

#-----------------------------------------------------------------------
class CSelect(CTag):
  """Items is a dict of value:desc for unordered selector or list of
  (value, desc) for ordered selector.  Current is the current value
  if any.  first_value and desc can be added to head of selector 
  (like "-- Select Address --" type entry). Attribs: name, hclass, id"""
  def __init__(self, items, current=None, first_value=None, first_desc=None, 
               **attribs):
    
    sitems = []
    if first_value is not None:
      sitems.append(COption(first_value, first_desc, (current is None)))
      
    # Dict for unordered list
    if isinstance(items, dict):
      values = [(value, key) for key, value in items.items()]
      values.sort()
      for value, key in values:
        sitems.append(COption(key, value, key==current))
        
    # List of tuples for ordered list
    else:
      for key, value in items:
        sitems.append(COption(key, value, key==current))
        
    body = '\n'.join([str(s) for s in sitems])
      
    CTag.__init__(self, 'select', body, '\n', **attribs)
  
#-----------------------------------------------------------------------
class COption:
  """Attribs: value, selected, hclass, id"""
  def __init__(self, value, desc, selected):
    self.value = value
    self.desc = desc
    if selected:
      self.selected = ' selected'
    else:
      self.selected = ''
    
  def __str__(self):
    return '<option value="%s"%s>%s</option>' % (str(self.value), self.selected, self.desc)

#-----------------------------------------------------------------------
class CTextArea(CTag):
  """Attribs: rows, cols, type, name, hclass, id"""
  def __init__(self, body, **attribs):
    if not attribs.has_key('type'):
      attribs['type'] = 'text'
    if not attribs.has_key('rows'):
      attribs['rows'] = 5
    if not attribs.has_key('cols'):
      attribs['cols'] = 40
    CTag.__init__(self, 'textarea', body, '\n', **attribs)

#-----------------------------------------------------------------------
class CItem(CTag):
  def __init__(self, content, **attribs):
    if isinstance(content, list):
      CTag.__init__(self, 'li', content, **attribs)
    else:
      CTag.__init__(self, 'li', [content], **attribs)
    
#-----------------------------------------------------------------------
class CList(CTag):
  """Attribs: hclass, id"""
  def __init__(self, items, ordered=0, **attribs):
    if ordered:
      tag = "ol"
    else:
      tag = "ul"
    li_items = []
    for item in items:
      if isinstance(item, CItem):
        li_items.append(str(item))
      else:
        li_items.append(str(CItem(item)))
    body = "".join(li_items)
    CTag.__init__(self, tag, body, '\n', **attribs)

  
