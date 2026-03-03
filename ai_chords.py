"""Chord detection via ChordMini API and chord-to-bar mapping.

Runs as a subprocess under the ai_venv Python 3 environment.
Sends an MP3 to the ChordMini API for chord recognition and beat
detection, then maps timestamped chords to bar positions using
downbeat boundaries.
"""
import sys
import json
import os
import time as time_mod

try:
  import requests
  HAS_REQUESTS = True
except ImportError:
  HAS_REQUESTS = False

CHORDMINI_URL = 'https://chordmini-backend-191567167632.us-central1.run.app'


def chordmini_notation_to_simple(chord_str):
  """Convert ChordMini colon notation to simple chord name.

  ChordMini returns chords like 'D:maj', 'A:min', 'G:7', 'N'.
  We need simple names like 'D', 'Am', 'G7'.
  """
  if chord_str == 'N' or not chord_str:
    return None

  if ':' not in chord_str:
    return chord_str

  root, quality = chord_str.split(':', 1)

  quality_map = {
    'maj': '',
    'min': 'm',
    'dim': 'dim',
    'aug': 'aug',
    '7': '7',
    'maj7': 'maj7',
    'min7': 'm7',
    'dim7': 'dim7',
    'hdim7': 'm7b5',
    'sus2': 'sus2',
    'sus4': 'sus4',
    'maj6': '6',
    'min6': 'm6',
    '9': '9',
    'maj9': 'maj9',
    'min9': 'm9',
    '1': '',
    '5': '5',
  }

  suffix = quality_map.get(quality, quality)
  return root + suffix


def _api_post(endpoint, mp3_path, extra_data=None):
  """POST an MP3 file to a ChordMini API endpoint."""
  url = CHORDMINI_URL + endpoint
  data = extra_data or {}

  if HAS_REQUESTS:
    with open(mp3_path, 'rb') as f:
      resp = requests.post(url, files={'file': f}, data=data, timeout=180)
    if resp.status_code != 200:
      print("ChordMini API error: HTTP %d for %s" % (resp.status_code, endpoint),
            file=sys.stderr)
      return None
    return resp.json()
  else:
    # urllib fallback for multipart
    boundary = '----ChordMiniBoundary'
    body = []
    for key, val in data.items():
      body.append(('--%s' % boundary).encode())
      body.append(('Content-Disposition: form-data; name="%s"' % key).encode())
      body.append(b'')
      body.append(str(val).encode())
    body.append(('--%s' % boundary).encode())
    body.append(('Content-Disposition: form-data; name="file"; filename="%s"' %
                 os.path.basename(mp3_path)).encode())
    body.append(b'Content-Type: audio/mpeg')
    body.append(b'')
    with open(mp3_path, 'rb') as f:
      body.append(f.read())
    body.append(('--%s--' % boundary).encode())
    body_bytes = b'\r\n'.join(body)

    import urllib.request
    req = urllib.request.Request(url, data=body_bytes,
      headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
    resp = urllib.request.urlopen(req, timeout=180)
    return json.loads(resp.read().decode('utf-8'))


def recognize_chords_api(mp3_path, detector='chord-cnn-lstm'):
  """Call ChordMini API to recognize chords from an MP3 file.

  Returns list of {'start': float, 'end': float, 'chord': str} or None.
  """
  result = _api_post('/api/recognize-chords', mp3_path,
                     {'detector': detector})
  if not result or not result.get('success'):
    print("ChordMini chord recognition failed", file=sys.stderr)
    return None

  chords = []
  for c in result.get('chords', []):
    simple = chordmini_notation_to_simple(c['chord'])
    if simple:
      chords.append({
        'start': c['start'],
        'end': c['end'],
        'chord': simple,
      })

  return chords


def detect_beats_api(mp3_path, model='madmom'):
  """Call ChordMini API for beat detection.

  Returns dict with 'beats', 'downbeats', 'bpm', 'time_signature' or None.
  """
  result = _api_post('/api/detect-beats', mp3_path, {'model': model})
  if not result or not result.get('success'):
    print("ChordMini beat detection failed", file=sys.stderr)
    return None

  return {
    'beats': result.get('beats', []),
    'downbeats': result.get('downbeats', []),
    'bpm': result.get('bpm'),
    'time_signature': result.get('time_signature', '4/4'),
    'duration': result.get('duration'),
  }


def map_chords_to_bars_downbeats(chords, downbeats):
  """Map timestamped chords to bars using actual downbeat positions.

  Each pair of consecutive downbeats defines a bar boundary.
  Returns list of bar chord strings.
  """
  if not chords or len(downbeats) < 2:
    return []

  bar_chords = []
  for i in range(len(downbeats) - 1):
    bar_start = downbeats[i]
    bar_end = downbeats[i + 1]
    bar_dur = bar_end - bar_start

    # Find chords overlapping this bar, weighted by duration
    chord_durations = {}
    for c in chords:
      overlap_start = max(c['start'], bar_start)
      overlap_end = min(c['end'], bar_end)
      if overlap_end > overlap_start:
        overlap = overlap_end - overlap_start
        name = c['chord']
        chord_durations[name] = chord_durations.get(name, 0.0) + overlap

    if not chord_durations:
      bar_chords.append('?')
      continue

    sorted_chords = sorted(chord_durations.items(), key=lambda x: -x[1])
    total = sum(d for _, d in sorted_chords)

    if sorted_chords[0][1] / total > 0.7:
      bar_chords.append(sorted_chords[0][0])
    elif len(sorted_chords) >= 2:
      bar_chords.append(sorted_chords[0][0] + sorted_chords[1][0])
    else:
      bar_chords.append(sorted_chords[0][0])

  return bar_chords


def map_chords_to_bars_bpm(chords, bpm, first_onset, time_sig='4/4'):
  """Map timestamped chords to bars using estimated BPM (fallback)."""
  if not chords:
    return []

  quarter_dur = 60.0 / bpm
  bar_dur_map = {
    '6/8': quarter_dur * 3,
    '9/8': quarter_dur * 4.5,
    '3/4': quarter_dur * 3,
    '2/4': quarter_dur * 2,
  }
  bar_dur = bar_dur_map.get(time_sig, quarter_dur * 4)

  total_dur = max(c['end'] for c in chords) - first_onset
  num_bars = int(total_dur / bar_dur) + 1
  downbeats = [first_onset + i * bar_dur for i in range(num_bars + 1)]
  return map_chords_to_bars_downbeats(chords, downbeats)


def detect_parts_from_chords(bar_chords, bars_per_part=8):
  """Detect repeated sections (parts) from chord progression.

  Traditional tunes play AABB (or similar). Looks for repeating
  8-bar patterns to identify distinct A, B, etc. parts.
  """
  if len(bar_chords) < bars_per_part:
    return [{'name': 'A', 'chords': bar_chords}]

  parts = []
  part_names = ['A', 'B', 'C', 'D']
  seen_patterns = []

  i = 0
  part_idx = 0
  while i + bars_per_part <= len(bar_chords) and part_idx < len(part_names):
    section = bar_chords[i:i + bars_per_part]

    matched = False
    for prev in seen_patterns:
      match_count = sum(1 for a, b in zip(section, prev) if a == b)
      if match_count >= bars_per_part * 0.75:
        matched = True
        break

    if not matched:
      seen_patterns.append(section)
      parts.append({
        'name': part_names[part_idx],
        'chords': section,
      })
      part_idx += 1

    i += bars_per_part

  return parts


def format_chord_chart(bar_chords, bars_per_row=4, repeat=True):
  """Format bar chords as a chord chart string."""
  lines = []
  prefix = '|:' if repeat else '| '
  suffix = ':|' if repeat else ' |'

  for i in range(0, len(bar_chords), bars_per_row):
    row = bar_chords[i:i + bars_per_row]
    if i == 0:
      line = prefix + ' ' + ' | '.join('%-4s' % c for c in row)
    else:
      line = '   ' + ' | '.join('%-4s' % c for c in row)
    if i + bars_per_row >= len(bar_chords):
      line = line.rstrip() + ' ' + suffix
    lines.append(line)

  return '\n'.join(lines)


def analyze_recording(mp3_path):
  """Run full chord + beat analysis on a recording.

  Calls ChordMini API for both chord recognition and beat detection.
  Returns dict with 'chords', 'beats', 'bar_chords', 'parts', 'bpm', etc.

  Rate limit: ChordMini allows 2 requests/min, so we pause between calls.
  """
  print("=== ChordMini Analysis ===")
  print("File: %s" % os.path.basename(mp3_path))

  # Chord recognition
  print("Requesting chord recognition...")
  t0 = time_mod.time()
  raw_chords = recognize_chords_api(mp3_path)
  print("  Chord recognition: %.1f sec" % (time_mod.time() - t0))

  if not raw_chords:
    print("  No chords detected")
    return None

  print("  Raw chords: %d segments" % len(raw_chords))

  # Rate limit pause (2 req/min = 30 sec between requests)
  elapsed = time_mod.time() - t0
  if elapsed < 31:
    wait = 31 - elapsed
    print("  Rate limit pause: %.0f sec..." % wait)
    time_mod.sleep(wait)

  # Beat detection
  print("Requesting beat detection...")
  t1 = time_mod.time()
  beats_info = detect_beats_api(mp3_path)
  print("  Beat detection: %.1f sec" % (time_mod.time() - t1))

  if not beats_info:
    print("  Beat detection failed, using BPM estimate")
    return {
      'raw_chords': raw_chords,
      'bar_chords': None,
      'parts': None,
      'bpm': None,
    }

  bpm = beats_info['bpm']
  time_sig = beats_info['time_signature']
  downbeats = beats_info['downbeats']

  print("  BPM: %.1f, Time sig: %s" % (bpm, time_sig))
  print("  Downbeats: %d (= %d bars)" % (len(downbeats), len(downbeats) - 1))

  # Map chords to bars using downbeats
  bar_chords = map_chords_to_bars_downbeats(raw_chords, downbeats)
  print("  Bar chords: %s" % ' | '.join(bar_chords))

  # Detect parts
  parts = detect_parts_from_chords(bar_chords)
  for part in parts:
    print("\n  Part %s: %s" % (part['name'], ' | '.join(part['chords'])))

  return {
    'raw_chords': raw_chords,
    'beats': beats_info['beats'],
    'downbeats': downbeats,
    'bpm': bpm,
    'time_signature': time_sig,
    'bar_chords': bar_chords,
    'parts': parts,
  }


def main():
  """Run chord + beat analysis on an MP3 file."""
  if len(sys.argv) < 2:
    print("Usage: ai_chords.py <mp3_path>")
    sys.exit(1)

  mp3_path = sys.argv[1]
  result = analyze_recording(mp3_path)

  if result:
    print("\n=== JSON Output ===")
    # Don't dump raw_chords in JSON output to keep it compact
    output = {k: v for k, v in result.items() if k != 'raw_chords'}
    output['chord_count'] = len(result.get('raw_chords', []))
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
  main()
