#!/usr/bin/env python3
"""AI analysis pipeline orchestrator for web use.

Called as a subprocess by tunejam.py under ai_venv Python 3.
Reuses existing modules (ai_analyze.py, ai_chords.py) to analyze a
tune's recording and produce structured JSON output.

Usage: ai_runner.py <tune_name> <mp3_path> [--no-chordmini]
Output: JSON to stdout
"""

import os
import sys
import json
import time
import tempfile
import subprocess
import re

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SRC_DIR), 'data')
AI_VENV = os.path.join(os.path.dirname(SRC_DIR), 'ai_venv')
PYTHON = os.path.join(AI_VENV, 'bin', 'python3')
CACHE_DIR = os.path.join(DATA_DIR, 'ai_cache')


def error_exit(msg):
  """Output error JSON and exit."""
  json.dump({'ok': False, 'error': msg}, sys.stdout)
  sys.exit(1)


def get_api_key():
  """Read API key from data/ai_config.json."""
  config_path = os.path.join(DATA_DIR, 'ai_config.json')
  if not os.path.isfile(config_path):
    error_exit('AI not configured: missing ai_config.json')
  with open(config_path) as f:
    config = json.load(f)
  key = config.get('api_key', '').strip()
  if not key:
    error_exit('AI not configured: empty api_key')
  return key


def check_cache(tune_name, mp3_path):
  """Check cache for existing result. Returns cached JSON or None."""
  cache_path = os.path.join(CACHE_DIR, tune_name + '.json')
  if not os.path.isfile(cache_path):
    return None
  try:
    with open(cache_path) as f:
      cached = json.load(f)
    current_mtime = os.path.getmtime(mp3_path)
    if cached.get('recording_mtime') == current_mtime:
      return cached.get('result')
  except (json.JSONDecodeError, OSError, KeyError):
    pass
  return None


def save_cache(tune_name, mp3_path, result):
  """Save result to cache."""
  if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)
  cache_path = os.path.join(CACHE_DIR, tune_name + '.json')
  data = {
    'recording_mtime': os.path.getmtime(mp3_path),
    'timestamp': time.time(),
    'result': result,
  }
  with open(cache_path, 'w') as f:
    json.dump(data, f, indent=2)


def run_basic_pitch(mp3_path, work_dir):
  """Run Basic Pitch on MP3 to produce MIDI. Returns MIDI path or error string."""
  bp_script = """
import sys
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH
predict_and_save([sys.argv[1]], sys.argv[2], save_midi=True, sonify_midi=False,
    save_model_outputs=False, save_notes=False, model_or_model_path=ICASSP_2022_MODEL_PATH,
    onset_threshold=0.5, frame_threshold=0.3, minimum_note_length=58, midi_tempo=120)
"""
  bp_path = os.path.join(work_dir, 'bp_melody.py')
  with open(bp_path, 'w') as f:
    f.write(bp_script)
  melody_out = os.path.join(work_dir, 'melody_out')
  os.makedirs(melody_out, exist_ok=True)
  proc = subprocess.Popen([PYTHON, bp_path, mp3_path, melody_out],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = proc.communicate()

  if proc.returncode != 0:
    err = stderr.decode('utf-8', errors='replace').strip()
    # Return last 200 chars of stderr for diagnostics
    return 'error:' + (err[-200:] if len(err) > 200 else err)

  for fn in os.listdir(melody_out):
    if fn.endswith('.mid'):
      return os.path.join(melody_out, fn)
  return 'error:Basic Pitch produced no MIDI output'


def run_ai_analyze(midi_path):
  """Run ai_analyze.py on MIDI file. Returns analysis text or error string."""
  analyze_script = os.path.join(SRC_DIR, 'ai_analyze.py')
  cmd = [PYTHON, analyze_script, midi_path, 'none']
  proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  stdout, stderr = proc.communicate()
  if proc.returncode != 0:
    err = stderr.decode('utf-8', errors='replace').strip()
    return 'error:' + (err[-200:] if len(err) > 200 else err)
  return stdout.decode('utf-8', errors='replace')


def get_chordmini_chords(mp3_path):
  """Get chord detection from ChordMini API.

  Calls recognize_chords_api() directly since we run under ai_venv.
  Returns formatted text or None.
  """
  try:
    sys.path.insert(0, SRC_DIR)
    from ai_chords import recognize_chords_api
    chords = recognize_chords_api(mp3_path)
  except Exception:
    return None

  if not chords:
    return None

  # Consolidate consecutive identical chords and filter very short segments
  consolidated = []
  for c in chords:
    if consolidated and consolidated[-1]['chord'] == c['chord']:
      consolidated[-1]['end'] = c['end']
    elif c['end'] - c['start'] < 0.3 and consolidated:
      pass
    else:
      consolidated.append(dict(c))

  # Compute chord distribution
  chord_durations = {}
  total_dur = 0
  for c in consolidated:
    dur = c['end'] - c['start']
    chord_durations[c['chord']] = chord_durations.get(c['chord'], 0.0) + dur
    total_dur += dur

  lines = ["AI chord detection from audio - chords present in recording:"]
  for chord, dur in sorted(chord_durations.items(), key=lambda x: -x[1]):
    pct = dur * 100 / total_dur if total_dur > 0 else 0
    lines.append("  %-6s: %.0f%% of recording" % (chord, pct))

  # Harmonic progression summary
  if consolidated:
    total_time = consolidated[-1]['end'] - consolidated[0]['start']
    window = max(2.0, total_time / 20)
    lines.append("\nHarmonic progression summary (%.0f-sec windows):" % window)
    t = consolidated[0]['start']
    window_chords = []
    while t < consolidated[-1]['end']:
      window_end = t + window
      wc = {}
      for c in consolidated:
        overlap_start = max(c['start'], t)
        overlap_end = min(c['end'], window_end)
        if overlap_end > overlap_start:
          wc[c['chord']] = wc.get(c['chord'], 0.0) + (overlap_end - overlap_start)
      if wc:
        dominant = max(wc.items(), key=lambda x: x[1])[0]
        window_chords.append(dominant)
      t = window_end
    lines.append("  " + " -> ".join(window_chords))

  return '\n'.join(lines)


def ask_claude(analysis_output, tune_name, api_key, chordmini_text=None):
  """Ask Claude to produce structured tune data from analysis.

  Calls the Anthropic API directly since we run under ai_venv.
  """
  import anthropic

  combined = analysis_output
  if chordmini_text:
    combined += "\n\n=== Chords Detected in Audio ===\n"
    combined += ("The following chords were detected by AI analysis of the full "
                 "audio recording. Use this as a guide for which chords are present "
                 "in this tune, but determine bar-by-bar placement using the "
                 "melody analysis and bass notes above.\n\n")
    combined += chordmini_text

  prompt = """You are an expert in traditional music transcription (Irish, Scottish, Quebecois, New England folk).

Analyze this automated transcription of the tune "%s":

%s

INSTRUCTIONS:
1. Determine the key, time signature, tune type, and unit note length.
2. Identify the parts (A, B, possibly C, D). Traditional tunes have 2-4 parts of 8 bars each.
   The recording usually plays AABB (or AABBAABB etc). Find where repeated sections start.
3. For each part, write the first 3 measures of melody in ABC notation.
   - IMPORTANT: Write in "straight" notation even though the performance may be "swung".
     Traditional musicians read straight eighth notes and automatically apply swing.
     If swing was detected in the analysis, account for that in your notation.
   - Use standard ABC: CDEFGAB below middle C, cdefgab above. ^=sharp, _=flat.
   - Use standard durations: no suffix=1 unit, 2=double, /2=half, 3=triple, etc.
   - Include pickup notes before the first bar line if present.
   - Use | for bar lines.
4. For each part, write the chord progression for ALL 8 measures.
   - Use BOTH the bass notes from the MIDI analysis AND the external chord detection data
     (if available) to determine chords. The external chord detection provides root chord
     names with timestamps. Cross-reference these with the melody and bass analysis.
   - IMPORTANT: Traditional tunes commonly use secondary chords like Em, Am, Bm, F#m.
     The chord detection may show only major chords (D, G, A) but consider whether
     the harmonic context suggests minor chords instead:
     * In D major: Em (ii), F#m (iii), Bm (vi) are common
     * In G major: Am (ii), Bm (iii), Em (vi) are common
     * In A major: Bm (ii), C#m (iii), F#m (vi) are common
     * In Em: Am (iv), Bm (v), C (VI), D (VII), G (III) are common
   - The melody notes during each bar are the strongest indicator of the chord.
     If the melody emphasizes E-G-B over a bar, the chord is likely Em even if
     the chord detection says G or D.
   - Format: |: G | Am | D | G | C | Am | D | G :|
   - If two chords share a measure, write them together: "AmD"
   - Some parts may have slight variations between first and second playing.
     If so, note the variation but write the primary version.

Return ONLY valid JSON:
{
  "key": "G",
  "time_signature": "4/4",
  "tune_type": "reel",
  "unit_note_length": "1/8",
  "parts": [
    {
      "name": "A",
      "first_3_measures": "GA|B2 AB AGEG|DGGF GAAB|",
      "chords": "|: G | G | C | CD | G | G | CAm | D :|"
    }
  ],
  "confidence": "high/medium/low",
  "notes": "observations"
}""" % (tune_name, combined)

  client = anthropic.Anthropic(api_key=api_key)
  msg = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=3000,
    messages=[{"role": "user", "content": prompt}],
  )
  text = msg.content[0].text
  if '```json' in text:
    text = text.split('```json')[1].split('```')[0]
  elif '```' in text:
    text = text.split('```')[1].split('```')[0]
  text = text.strip()

  try:
    return json.loads(text)
  except json.JSONDecodeError:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
      try:
        return json.loads(match.group())
      except json.JSONDecodeError:
        pass
    return {'error': 'JSON parse failed', 'raw': text[:500]}


def main():
  if len(sys.argv) < 3:
    error_exit('Usage: ai_runner.py <tune_name> <mp3_path> [--no-chordmini]')

  tune_name = sys.argv[1]
  mp3_path = sys.argv[2]
  use_chordmini = '--no-chordmini' not in sys.argv

  if not os.path.isfile(mp3_path):
    error_exit('Recording not found: %s' % mp3_path)

  # Check cache
  cached = check_cache(tune_name, mp3_path)
  if cached:
    json.dump(cached, sys.stdout)
    sys.exit(0)

  # Get API key
  api_key = get_api_key()

  # Create work directory
  work_dir = tempfile.mkdtemp(prefix='ai_runner_')

  # Step 1: Basic Pitch
  midi_result = run_basic_pitch(mp3_path, work_dir)
  if midi_result.startswith('error:'):
    error_exit('Basic Pitch failed: %s' % midi_result[6:])
  midi_path = midi_result

  # Step 2: AI Analyze
  analysis = run_ai_analyze(midi_path)
  if analysis.startswith('error:'):
    error_exit('MIDI analysis failed: %s' % analysis[6:])

  # Step 3: ChordMini (optional, graceful degradation)
  chordmini_text = None
  if use_chordmini:
    chordmini_text = get_chordmini_chords(mp3_path)
    # If it fails, continue without it

  # Step 4: Claude API
  result = ask_claude(analysis, tune_name, api_key, chordmini_text)
  if 'error' in result:
    error_exit('Claude analysis failed: %s' % result.get('error', 'unknown'))

  # Cache result
  save_cache(tune_name, mp3_path, result)

  # Output
  json.dump(result, sys.stdout)


if __name__ == '__main__':
  main()
