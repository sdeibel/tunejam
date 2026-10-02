#!/usr/bin/env python
#coding:utf-8
"""Tests for the compact set-page tune info popup helpers."""

import os
import sys
import unittest

_src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _src_dir)
sys.path.insert(0, os.path.join(_src_dir, 'website'))

import utils
import tunejam


class CTuneInfoPopupTests(unittest.TestCase):

  def test_escape_html(self):
    self.assertEqual(tunejam._EscapeHTML('a <b> & "c"'),
                     'a &lt;b&gt; &amp; &quot;c&quot;')
    self.assertEqual(tunejam._EscapeHTML(''), '')
    self.assertEqual(tunejam._EscapeHTML(None), '')

  def test_popup_body_empty_without_metadata(self):
    obj = utils.CTune('__missing_tune_for_test__')
    obj.author = None
    obj.origin = None
    obj.history = None
    obj.url = None
    obj.ref = None
    self.assertEqual(tunejam._TuneInfoPopupBody(obj), '')

  def test_popup_body_includes_fields(self):
    obj = utils.CTune('__fake__')
    obj.author = 'Someone'
    obj.origin = 'Here'
    obj.history = 'Once upon\na time'
    obj.url = 'https://example.com/tune\nhttps://example.com/other'
    obj.ref = 'Book p.12'
    body = tunejam._TuneInfoPopupBody(obj)
    self.assertTrue('Author: Someone' in body)
    self.assertTrue('Origin: Here' in body)
    self.assertTrue('Once upon a time' in body)
    self.assertTrue('href="https://example.com/tune"' in body)
    self.assertTrue('Book p.12' in body)

  def test_popup_body_escapes_history(self):
    obj = utils.CTune('__fake__')
    obj.author = None
    obj.origin = None
    obj.history = 'A <script>alert(1)</script> & more'
    obj.url = None
    obj.ref = None
    body = tunejam._TuneInfoPopupBody(obj)
    self.assertFalse('<script>' in body)
    self.assertTrue('&lt;script&gt;' in body)
    self.assertTrue('&amp; more' in body)

  def test_real_tune_has_popup_content(self):
    obj = utils.CTune('queens_jig')
    obj.ReadDatabase()
    body = tunejam._TuneInfoPopupBody(obj)
    self.assertTrue(body)
    self.assertTrue('Author:' in body or 'Origin:' in body or 'tune-info-history' in body)

  def test_icon_and_overlay_ids_match(self):
    icon = tunejam._TuneInfoIconHTML('queens_jig', 2)
    overlay = tunejam._TuneInfoOverlayHTML('queens_jig', '<p>hi</p>')
    self.assertTrue('data-tune-info="tune-info-overlay-queens_jig"' in icon)
    self.assertTrue('id="tune-info-overlay-queens_jig"' in overlay)
    self.assertTrue('tune-info-icon' in icon)
    self.assertTrue('action-icon-2' in icon)


if __name__ == '__main__':
  unittest.main()
