#!/usr/bin/env python
"""Test that editing only the title in the tune editor produces
a spec file that differs only in the T: line.

This simulates the full round-trip: read spec -> build form data as
the editor would display it -> change only title -> apply form data
as tune_save does -> write spec -> compare.

Usage:  python test_roundtrip.py [tune_name ...]
Default tests 'queens_jig'.
"""

import sys, os, shutil, textwrap, collections

# Set up paths so utils.py can find html.py and we can find utils.py
_src_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _src_dir)
sys.path.insert(0, os.path.join(_src_dir, 'website'))

import utils

kHistoryWrapWidth = 85


def _get_num_columns(parsed):
  """Same logic as GetNumColumns in tunejam.py."""
  counts = collections.defaultdict(int)
  for part in reversed(parsed):
    count = sum(1 for m in part if m not in ('|:', ':|'))
    counts[count] += 1
  top_count = 0
  top_freq = 0
  for count, freq in counts.items():
    if freq > top_freq:
      top_freq = freq
      top_count = count
  count = top_count
  if count / 5 * 5 == count:
    return 5
  elif count / 4 * 4 == count:
    return 4
  elif count / 2 * 2 == count:
    return count / 2
  else:
    return count


def _reconstruct_chords(form):
  """Same logic as _ReconstructChords in tunejam.py."""
  num_parts = int(form.get('num_parts', 0))
  header_text = form.get('chord_header', '').strip()
  footer_text = form.get('chord_footer', '').strip()

  if num_parts == 0:
    return ''

  line_data = []
  max_columns = 0
  for p in range(num_parts):
    num_rows = int(form.get('rows_in_part_%d' % p, 2))
    has_repeat = form.get('repeat_%d' % p) == '1'
    for r in range(num_rows):
      chords = []
      c = 0
      while True:
        val = form.get('chord_%d_%d_%d' % (p, r, c), None)
        if val is None:
          break
        chords.append(val.strip())
        c += 1
      if not chords:
        chords = ['']
      if len(chords) > max_columns:
        max_columns = len(chords)
      is_first_row = (r == 0)
      is_last_row = (r == num_rows - 1)
      has_open = has_repeat and is_first_row
      has_close = has_repeat and is_last_row
      is_part_start = is_first_row and not has_open
      line_data.append((has_open, has_close, is_part_start, chords))

  has_any_chords = any(c for _, _, _, chords in line_data for c in chords)
  if not has_any_chords and not header_text and not footer_text:
    return ''

  col_widths = [0] * max_columns
  for _, _, _, chords in line_data:
    for i, c in enumerate(chords):
      col_widths[i] = max(col_widths[i], len(c))

  any_close = any(d[1] for d in line_data)
  result_lines = []

  if header_text:
    result_lines.append(header_text)

  for has_open, has_close, is_part_start, chords in line_data:
    if has_open:
      prefix = '|:'
    elif is_part_start:
      prefix = '| '
    else:
      prefix = '  '
    padded = [c.ljust(col_widths[i]) if i < len(col_widths) else c
              for i, c in enumerate(chords)]
    line = prefix + ' ' + ' | '.join(padded)
    if has_close:
      line += ' :|'
    elif any_close:
      line += '  |'
    else:
      line += ' |'
    result_lines.append(line)

  if footer_text:
    result_lines.append(footer_text)

  return '\n'.join(result_lines)


def build_save_form_data(obj):
  """Build the POST form data that the tune editor would submit,
  exactly mirroring what _build_tune_form puts in the HTML form."""

  data = {}

  # Simple text fields
  data['title'] = obj.title or ''
  data['key'] = obj.key or ''
  data['meter'] = obj.meter or '4/4'
  data['unit'] = obj.unit or '1/8'
  data['author'] = obj.author or ''
  data['origin'] = obj.origin or ''
  data['structure'] = obj.structure or ''
  data['ref'] = obj.ref or ''

  # History -- the form displays unwrapped text
  if obj.history:
    data['history'] = ' '.join(line.strip() for line in obj.history.split('\n'))
  else:
    data['history'] = ''

  # Tune type checkboxes -- set the ones matching obj.klass
  if obj.klass:
    for klass in obj.klass.split(','):
      data['klass_%s' % klass.strip()] = '1'

  # URLs -- one field per URL line
  if obj.url:
    for i, url in enumerate(u.strip() for u in obj.url.split('\n') if u.strip()):
      data['url_%d' % i] = url

  # ABC notes
  data['raw_notes'] = obj.raw_notes or ''

  # Chords -- parse into structured form fields (same as _build_tune_form)
  chord_parts = []
  header_text = ''
  footer_text = ''
  num_columns = 4

  if obj.chords and obj.chords.strip():
    chord_lines = obj.chords.strip().splitlines()
    header_lines = []
    footer_lines = []
    chart_lines = []
    in_chart = False
    past_chart = False
    for line in chord_lines:
      if '|' in line:
        in_chart = True
        past_chart = False
        chart_lines.append(line)
      elif in_chart:
        past_chart = True
        in_chart = False
        footer_lines.append(line)
      elif past_chart:
        footer_lines.append(line)
      else:
        header_lines.append(line)
    header_text = '\n'.join(header_lines)
    footer_text = '\n'.join(footer_lines)

    chart_text = '\n'.join(chart_lines)
    parsed = utils.ParseChords(chart_text)
    num_columns = _get_num_columns(parsed)

    for part in parsed:
      has_repeat = '|:' in part or ':|' in part
      cells = [m for m in part if m not in ('|:', ':|')]
      rows = []
      row = []
      for cell in cells:
        row.append(cell)
        if len(row) == num_columns:
          rows.append(row)
          row = []
      if row:
        rows.append(row)
      chord_parts.append({'rows': rows, 'repeat': has_repeat})

  if not chord_parts:
    ttype = obj.klass.split(',')[0] if obj.klass else 'reel'
    defaults = utils.kDefaultsByType.get(ttype, utils.kDefaultsByType['reel'])
    nc = defaults['measures'] / defaults['rows']
    num_columns = nc
    for p in range(2):
      rows = []
      for r in range(defaults['rows']):
        rows.append([''] * nc)
      chord_parts.append({'rows': rows, 'repeat': True})

  data['num_parts'] = str(len(chord_parts))
  data['chord_header'] = header_text
  data['chord_footer'] = footer_text

  for p_idx, cp in enumerate(chord_parts):
    data['rows_in_part_%d' % p_idx] = str(len(cp['rows']))
    data['repeat_%d' % p_idx] = '1' if cp['repeat'] else '0'
    for r_idx, row in enumerate(cp['rows']):
      for c_idx, cell in enumerate(row):
        data['chord_%d_%d_%d' % (p_idx, r_idx, c_idx)] = cell

  return data


def apply_form_data(tune_name, form_data):
  """Apply form data to a CTune object, same as tune_save() does."""
  obj = utils.CTune(tune_name)
  obj.ReadDatabase()
  original_history = obj.history

  obj.title = form_data.get('title', obj.title or '').strip()
  obj.key = form_data.get('key', obj.key or '').strip()
  obj.meter = form_data.get('meter', obj.meter or '').strip()
  obj.unit = form_data.get('unit', obj.unit or '').strip()
  obj.author = form_data.get('author', '').strip() or None
  obj.origin = form_data.get('origin', '').strip() or None
  obj.structure = form_data.get('structure', '').strip() or None
  obj.ref = form_data.get('ref', '').strip() or None

  # History processing (same as _process_history)
  new_text = form_data.get('history', '').strip() or None
  if new_text is None:
    obj.history = None
  else:
    new_unwrapped = ' '.join(new_text.split())
    if original_history:
      orig_unwrapped = ' '.join(original_history.split())
      if new_unwrapped == orig_unwrapped:
        obj.history = original_history
      else:
        obj.history = '\n'.join(textwrap.wrap(new_unwrapped, kHistoryWrapWidth))
    else:
      obj.history = '\n'.join(textwrap.wrap(new_unwrapped, kHistoryWrapWidth))

  # Tune types -- preserve original order
  selected = set()
  for sname, stitle, slabel in utils.kSections:
    if sname == 'incomplete':
      continue
    if form_data.get('klass_%s' % sname):
      selected.add(sname)
  if selected:
    orig_types = [t.strip() for t in (obj.klass or '').split(',') if t.strip()]
    types = [t for t in orig_types if t in selected]
    for t in selected:
      if t not in types:
        types.append(t)
    obj.klass = ','.join(types)
  else:
    obj.klass = 'other'

  # URLs
  urls = []
  for key in sorted(form_data.keys()):
    if key.startswith('url_'):
      val = form_data.get(key, '').strip()
      if val:
        urls.append(val)
  obj.url = '\n'.join(urls) if urls else None

  # Notes
  raw_notes = form_data.get('raw_notes', '')
  if raw_notes.strip():
    obj.raw_notes = raw_notes.rstrip('\n') + '\n'
  else:
    obj.raw_notes = ''

  # Chords
  obj.chords = _reconstruct_chords(form_data)

  obj.WriteSpec()
  return obj


def test_title_only_roundtrip(tune_name):
  """Test that changing only the title produces a diff only on the T: line."""

  # Read the original spec file
  obj = utils.CTune(tune_name)
  obj.ReadDatabase()
  spec_path = obj._GetSpecFile()

  original_content = open(spec_path).read()
  original_lines = original_content.splitlines()

  # Build form data as the editor would
  form_data = build_save_form_data(obj)

  # Change only the title
  new_title = obj.title + ' TEST'
  form_data['title'] = new_title

  # Back up original file
  backup_path = spec_path + '.test_backup'
  shutil.copy2(spec_path, backup_path)

  try:
    apply_form_data(tune_name, form_data)

    # Read back and compare
    new_content = open(spec_path).read()
    new_lines = new_content.splitlines()

    # Find differences, separating content changes from whitespace-only changes
    max_lines = max(len(original_lines), len(new_lines))
    content_diffs = []
    whitespace_diffs = []
    for i in range(max_lines):
      orig = original_lines[i] if i < len(original_lines) else '<missing>'
      new = new_lines[i] if i < len(new_lines) else '<missing>'
      if orig != new:
        if orig.rstrip() == new.rstrip():
          whitespace_diffs.append((i + 1, orig, new))
        else:
          content_diffs.append((i + 1, orig, new))

    # Report results
    ok = True
    if len(content_diffs) == 0:
      print('FAIL: %s -- no content differences found (title change was not applied!)' % tune_name)
      ok = False
    elif len(content_diffs) == 1 and content_diffs[0][1].startswith('T:') and content_diffs[0][2].startswith('T:'):
      line_num, orig, new = content_diffs[0]
      print('PASS: %s -- only the T: line changed (line %d)' % (tune_name, line_num))
      print('  Before: %s' % orig)
      print('  After:  %s' % new)
    else:
      print('FAIL: %s -- %d content line(s) differ (expected only the T: line to change):' % (tune_name, len(content_diffs)))
      for line_num, orig, new in content_diffs:
        print('  Line %d:' % line_num)
        print('    Before: %s' % repr(orig))
        print('    After:  %s' % repr(new))
      ok = False

    if whitespace_diffs:
      print('  NOTE: %d line(s) have trailing whitespace differences (cosmetic):' % len(whitespace_diffs))
      for line_num, orig, new in whitespace_diffs:
        print('    Line %d: %d trailing space(s) removed' % (line_num, len(orig) - len(orig.rstrip())))

    return ok

  finally:
    # Restore original file
    shutil.move(backup_path, spec_path)


if __name__ == '__main__':
  tune_names = sys.argv[1:] if len(sys.argv) > 1 else ['queens_jig']
  all_ok = True
  for tune_name in tune_names:
    ok = test_title_only_roundtrip(tune_name)
    if not ok:
      all_ok = False
  sys.exit(0 if all_ok else 1)
