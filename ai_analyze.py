"""Smarter MIDI analysis: melody extraction, quantization, chord inference.

Runs as a subprocess under the ai_venv Python 3 environment.
Reads a MIDI file and produces structured analysis suitable for Claude.
"""
import sys
import json
import pretty_midi
import numpy as np
from collections import Counter, defaultdict
from music21 import converter

def midi_to_abc_pitch(midi_num):
  """Convert MIDI note number to ABC notation pitch name."""
  # ABC: C,D,E,F,G,A,B = below middle C (MIDI 48-59 area)
  #      c,d,e,f,g,a,b = above middle C (MIDI 60-71)
  #      c',d' = octave above that, C, D, = octave below
  note_names = ['C', 'D', 'E', 'F', 'G', 'A', 'B']
  sharps = [False, True, False, True, False, False, True, False, True, False, True, False]
  # reverse: C=0, C#=1, D=2... maps to note_names index
  chromatic = [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6]  # C C# D D# E F F# G G# A A# B
  is_sharp =  [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]

  pc = midi_num % 12
  octave = midi_num // 12 - 1  # MIDI octave (C4 = middle C = MIDI 60, octave 4)
  name_idx = chromatic[pc]
  sharp = is_sharp[pc]

  # ABC convention: C-B (uppercase) = octave 4 (MIDI 60-71)
  #                 c-b (lowercase) = octave 5 (MIDI 72-83)
  if octave <= 4:
    letter = note_names[name_idx]
  else:
    letter = note_names[name_idx].lower()

  prefix = '^' if sharp else ''

  # Octave markers
  if octave <= 2:
    letter = letter + ',' * (3 - octave)
  elif octave == 3:
    letter = letter + ','
  elif octave == 4:
    pass  # plain uppercase
  elif octave == 5:
    pass  # plain lowercase
  elif octave >= 6:
    letter = letter + "'" * (octave - 5)

  return prefix + letter


def extract_melody(notes, min_pitch=55, max_pitch=96):
  """Extract melody line from note list by taking highest pitch at each onset.

  Filters to instrument range and groups simultaneous notes, keeping
  the highest pitch (melody is typically the highest voice).
  """
  # Filter to melody instrument range
  melody_notes = [n for n in notes if min_pitch <= n['pitch'] <= max_pitch]
  if not melody_notes:
    # Fallback: use all notes in upper half of range
    all_pitches = [n['pitch'] for n in notes]
    if all_pitches:
      mid = (min(all_pitches) + max(all_pitches)) // 2
      melody_notes = [n for n in notes if n['pitch'] >= mid]

  if not melody_notes:
    return notes

  # Group notes that start within 50ms of each other
  ONSET_TOLERANCE = 0.05
  groups = []
  current_group = [melody_notes[0]]

  for n in melody_notes[1:]:
    if n['start'] - current_group[0]['start'] < ONSET_TOLERANCE:
      current_group.append(n)
    else:
      groups.append(current_group)
      current_group = [n]
  groups.append(current_group)

  # Take highest pitch from each group
  melody = []
  for group in groups:
    best = max(group, key=lambda n: n['pitch'])
    melody.append(best)

  # Merge consecutive notes of the same pitch that are very close
  # (Basic Pitch sometimes splits one note into two)
  merged = [melody[0]]
  for n in melody[1:]:
    prev = merged[-1]
    if (n['pitch'] == prev['pitch'] and
        n['start'] - prev['end'] < 0.08):
      # Extend previous note
      prev['end'] = n['end']
      prev['dur'] = prev['end'] - prev['start']
    else:
      merged.append(n)

  return merged


def detect_swing_ratio(notes):
  """Detect whether the performance is swung and estimate the swing ratio.

  In swing playing, consecutive eighth notes alternate long-short.
  A straight performance has ratio 1.0; typical swing is 1.5-2.0.

  Returns (is_swung, swing_ratio, long_dur, short_dur).
  """
  if len(notes) < 8:
    return False, 1.0, None, None

  onsets = np.array([n['start'] for n in notes])
  iois = np.diff(onsets)

  # Filter out very short (ornaments) and very long (rests) intervals
  valid = (iois > 0.05) & (iois < 1.5)
  iois = iois[valid]

  if len(iois) < 8:
    return False, 1.0, None, None

  median_ioi = np.median(iois)

  # Look at IOIs near the eighth note level (0.5x to 1.5x median)
  eighth_range = (iois > median_ioi * 0.4) & (iois < median_ioi * 1.8)
  eighth_iois = iois[eighth_range]

  if len(eighth_iois) < 8:
    return False, 1.0, None, None

  # Check for bimodal distribution (swing indicator)
  # Split IOIs into two clusters using the mean as split point
  # (mean is between the two modes when alternating long-short)
  mean_ioi = np.mean(eighth_iois)
  short_iois = eighth_iois[eighth_iois < mean_ioi]
  long_iois = eighth_iois[eighth_iois >= mean_ioi]

  # If all IOIs are very similar (straight), try stricter split
  if len(short_iois) < 3 or len(long_iois) < 3:
    # Try percentile-based split
    p40 = np.percentile(eighth_iois, 40)
    p60 = np.percentile(eighth_iois, 60)
    if p60 > p40 * 1.1:
      mid = (p40 + p60) / 2
      short_iois = eighth_iois[eighth_iois < mid]
      long_iois = eighth_iois[eighth_iois >= mid]

  if len(short_iois) < 3 or len(long_iois) < 3:
    return False, 1.0, None, None

  short_mean = np.mean(short_iois)
  long_mean = np.mean(long_iois)
  ratio = long_mean / short_mean

  # Swing if ratio > 1.2 (noticeable swing) and < 2.5 (not just quarter/eighth)
  if 1.2 < ratio < 2.5:
    return True, ratio, long_mean, short_mean
  else:
    return False, 1.0, None, None


def detect_tempo_and_beats(notes, estimated_bpm):
  """Detect tempo and beat positions from note onsets.

  Returns (bpm, beat_duration_sec, first_beat_time).
  """
  if not notes or len(notes) < 4:
    return estimated_bpm, 60.0 / estimated_bpm, 0.0

  onsets = np.array([n['start'] for n in notes])
  iois = np.diff(onsets)  # inter-onset intervals
  iois = iois[iois > 0.05]  # filter tiny gaps (ornaments)
  iois = iois[iois < 2.0]   # filter long gaps (rests/breaks)

  if len(iois) < 4:
    return estimated_bpm, 60.0 / estimated_bpm, 0.0

  # For traditional music, the basic pulse is usually the eighth note
  # Reels: ~180-240 eighth notes/min = 90-120 quarter BPM
  # Jigs: ~180-240 eighth notes/min
  # Look for the most common IOI cluster
  median_ioi = np.median(iois)

  # Check for swing and use combined long+short as the beat pair
  is_swung, swing_ratio, long_dur, short_dur = detect_swing_ratio(notes)
  if is_swung and long_dur and short_dur:
    # A swung pair (long + short) = two straight eighth notes
    # So one eighth note = (long + short) / 2
    eighth_dur = (long_dur + short_dur) / 2.0
    print("Swing detected: ratio=%.2f (long=%.3f short=%.3f) -> eighth=%.3f" %
          (swing_ratio, long_dur, short_dur, eighth_dur))
  else:
    eighth_dur = median_ioi

  quarter_dur = eighth_dur * 2
  bpm = 60.0 / quarter_dur

  # Sanity check: traditional music is usually 80-140 BPM (quarter note)
  if bpm < 60:
    bpm *= 2
    quarter_dur /= 2
    eighth_dur /= 2
  elif bpm > 160:
    bpm /= 2
    quarter_dur *= 2
    eighth_dur *= 2

  return bpm, quarter_dur, onsets[0]


def quantize_to_grid(notes, bpm, first_onset, time_sig='4/4', unit='1/8'):
  """Quantize note onsets to a rhythmic grid, normalizing swing.

  Traditional music is written 'straight' but played with swing.
  We detect the swing ratio and use it to build a corrected grid
  that maps swung note positions to straight grid positions.
  """
  quarter_dur = 60.0 / bpm

  if unit == '1/8':
    subdiv_dur = quarter_dur / 2  # eighth note duration
  else:
    subdiv_dur = quarter_dur  # quarter note duration

  if time_sig == '6/8':
    beats_per_bar = 6 if unit == '1/8' else 2
  elif time_sig == '9/8':
    beats_per_bar = 9 if unit == '1/8' else 3
  elif time_sig == '3/4':
    beats_per_bar = 6 if unit == '1/8' else 3
  elif time_sig == '2/4':
    beats_per_bar = 4 if unit == '1/8' else 2
  else:  # 4/4
    beats_per_bar = 8 if unit == '1/8' else 4

  bar_dur = subdiv_dur * beats_per_bar

  # Detect swing to build a warped grid
  is_swung, swing_ratio, long_dur, short_dur = detect_swing_ratio(notes)

  quantized = []
  for n in notes:
    t = n['start'] - first_onset

    if is_swung and long_dur and short_dur and unit == '1/8':
      # Swing-aware quantization: within each beat (2 eighth notes),
      # the downbeat eighth arrives on time but the upbeat eighth is
      # delayed by the swing ratio.
      #
      # One beat = long_dur + short_dur (swung pair)
      # We need to figure out which beat pair this note falls in,
      # and whether it's the on-beat or off-beat eighth.
      beat_pair_dur = long_dur + short_dur  # = one quarter note in time
      beat_pair_idx = int(t / beat_pair_dur)
      pos_in_pair = t - beat_pair_idx * beat_pair_dur

      # If position is closer to 0, it's the downbeat eighth (grid pos even)
      # If position is closer to long_dur, it's the upbeat eighth (grid pos odd)
      if pos_in_pair < long_dur * 0.65:
        # Downbeat eighth
        grid_pos = beat_pair_idx * 2
      elif pos_in_pair < long_dur * 1.15:
        # Upbeat eighth (swung late)
        grid_pos = beat_pair_idx * 2 + 1
      else:
        # Beyond - next downbeat
        grid_pos = (beat_pair_idx + 1) * 2
    else:
      # Straight quantization
      grid_pos = round(t / subdiv_dur)

    bar_num = int(grid_pos // beats_per_bar)
    beat_in_bar = int(grid_pos % beats_per_bar)

    # Duration: for swung notes, use the straight subdivision
    dur_subdivs = max(1, round(n['dur'] / subdiv_dur))

    quantized.append({
      'pitch': n['pitch'],
      'name': n['name'],
      'abc': midi_to_abc_pitch(n['pitch']),
      'bar': bar_num,
      'beat': beat_in_bar,
      'dur': dur_subdivs,
      'start_sec': n['start'],
    })

  return quantized, bar_dur


def format_quantized_as_bars(quantized, beats_per_bar):
  """Format quantized notes as bar-by-bar text for readability."""
  bars = defaultdict(list)
  for n in quantized:
    bars[n['bar']].append(n)

  lines = []
  for bar_num in sorted(bars.keys()):
    bar_notes = sorted(bars[bar_num], key=lambda n: n['beat'])
    note_strs = []
    for n in bar_notes:
      dur_str = str(n['dur']) if n['dur'] != 1 else ''
      note_strs.append('%s%s' % (n['abc'], dur_str))
    lines.append('|%s' % ' '.join(note_strs))

  return '\n'.join(lines)


def extract_bass_line(notes, max_pitch=55):
  """Extract bass notes for chord inference."""
  bass = [n for n in notes if n['pitch'] <= max_pitch]
  return bass


def infer_chords_from_bass(bass_notes, bpm, first_onset, time_sig='4/4', unit='1/8'):
  """Infer chords from bass note patterns within each bar."""
  if not bass_notes:
    return []

  quarter_dur = 60.0 / bpm
  subdiv_dur = quarter_dur / 2 if unit == '1/8' else quarter_dur

  if time_sig == '6/8':
    beats_per_bar = 6 if unit == '1/8' else 2
  elif time_sig == '3/4':
    beats_per_bar = 6 if unit == '1/8' else 3
  elif time_sig == '2/4':
    beats_per_bar = 4 if unit == '1/8' else 2
  else:
    beats_per_bar = 8 if unit == '1/8' else 4

  bar_dur = subdiv_dur * beats_per_bar

  # Group bass notes by bar
  bars = defaultdict(list)
  for n in bass_notes:
    t = n['start'] - first_onset
    bar_num = int(t / bar_dur)
    bars[bar_num].append(n)

  # For each bar, find the most prominent bass pitch class
  note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  chord_map = {
    'C': 'C', 'C#': 'C#', 'D': 'D', 'D#': 'D#', 'E': 'E',
    'F': 'F', 'F#': 'F#', 'G': 'G', 'G#': 'G#', 'A': 'A',
    'A#': 'A#', 'B': 'B'
  }

  chords = []
  for bar_num in sorted(bars.keys()):
    pc_dur = Counter()
    for n in bars[bar_num]:
      pc = note_names[n['pitch'] % 12]
      pc_dur[pc] += n['dur']
    if pc_dur:
      root = pc_dur.most_common(1)[0][0]
      chords.append({'bar': bar_num, 'root': root})
    else:
      chords.append({'bar': bar_num, 'root': '?'})

  return chords


def main():
  midi_path = sys.argv[1]
  has_bass_midi = sys.argv[2] if len(sys.argv) > 2 else None

  # Load MIDI
  pm = pretty_midi.PrettyMIDI(midi_path)
  estimated_bpm = pm.estimate_tempo()
  duration = pm.get_end_time()

  # Get all notes
  all_notes = []
  for inst in pm.instruments:
    for note in inst.notes:
      all_notes.append({
        'start': note.start,
        'end': note.end,
        'pitch': note.pitch,
        'name': pretty_midi.note_number_to_name(note.pitch),
        'dur': note.end - note.start,
      })
  all_notes.sort(key=lambda x: (x['start'], x['pitch']))

  print("=== MIDI Summary ===")
  print("Duration: %.1f seconds" % duration)
  print("Total notes: %d" % len(all_notes))
  print("Estimated tempo: %.1f BPM (eighth note level)" % estimated_bpm)

  # Key detection via music21
  score = converter.parse(midi_path)
  detected_key = score.analyze('key')
  print("Detected key: %s (confidence: %.3f)" % (detected_key, detected_key.correlationCoefficient))

  # Pitch class histogram
  note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
  pc_counts = Counter()
  for n in all_notes:
    pc_counts[note_names[n['pitch'] % 12]] += n['dur']
  print("\nPitch class profile:")
  for name in sorted(pc_counts, key=pc_counts.get, reverse=True)[:8]:
    bar = '#' * int(pc_counts[name] * 20 / max(pc_counts.values()))
    print("  %-3s %s" % (name, bar))

  # Extract melody
  melody = extract_melody(all_notes)
  print("\n=== Melody Extraction ===")
  print("Melody notes: %d (from %d total)" % (len(melody), len(all_notes)))
  if melody:
    mel_pitches = [n['pitch'] for n in melody]
    print("Melody range: %s (%d) to %s (%d)" % (
      pretty_midi.note_number_to_name(min(mel_pitches)), min(mel_pitches),
      pretty_midi.note_number_to_name(max(mel_pitches)), max(mel_pitches)))

  # Detect tempo from melody note onsets
  bpm, quarter_dur, first_onset = detect_tempo_and_beats(melody, estimated_bpm)
  print("\n=== Tempo Detection ===")
  print("Detected BPM: %.1f (quarter note)" % bpm)
  print("Quarter note duration: %.3f sec" % quarter_dur)
  print("First onset: %.3f sec" % first_onset)

  # Quantize melody
  # Default to 4/4 and 1/8 for now; Claude will refine
  quantized, bar_dur = quantize_to_grid(melody, bpm, first_onset)
  print("\n=== Quantized Melody (first 16 bars) ===")
  bars_text = format_quantized_as_bars(quantized, 8)
  # Print first 16 bars
  bar_lines = bars_text.split('\n')
  for line in bar_lines[:16]:
    print(line)
  if len(bar_lines) > 16:
    print("... (%d more bars)" % (len(bar_lines) - 16))

  # Also output raw melody timeline for Claude
  print("\n=== Melody Note Timeline ===")
  for n in melody[:150]:
    print("  %.3f  %-5s  dur=%.3f" % (n['start'], n['name'], n['dur']))
  if len(melody) > 150:
    print("  ... (%d more)" % (len(melody) - 150))

  # Bass/chord analysis from separated bass track if available
  if has_bass_midi and has_bass_midi != 'none':
    print("\n=== Bass Track Chord Analysis ===")
    bass_pm = pretty_midi.PrettyMIDI(has_bass_midi)
    bass_notes = []
    for inst in bass_pm.instruments:
      for note in inst.notes:
        bass_notes.append({
          'start': note.start,
          'end': note.end,
          'pitch': note.pitch,
          'name': pretty_midi.note_number_to_name(note.pitch),
          'dur': note.end - note.start,
        })
    bass_notes.sort(key=lambda x: x['start'])
    print("Bass notes: %d" % len(bass_notes))

    bass_chords = infer_chords_from_bass(bass_notes, bpm, first_onset)
    if bass_chords:
      chord_strs = []
      for c in bass_chords[:64]:
        chord_strs.append(c['root'])
      # Group by 8 (one line per 8 bars, typical for traditional tunes)
      for i in range(0, len(chord_strs), 8):
        print("  bars %d-%d: %s" % (i, min(i+7, len(chord_strs)-1), ' | '.join(chord_strs[i:i+8])))
  else:
    # Try to extract bass from the same MIDI (lower range notes)
    print("\n=== Bass Note Chord Inference ===")
    bass_notes = extract_bass_line(all_notes)
    print("Bass notes found: %d" % len(bass_notes))
    if bass_notes:
      bass_chords = infer_chords_from_bass(bass_notes, bpm, first_onset)
      if bass_chords:
        chord_strs = [c['root'] for c in bass_chords[:64]]
        for i in range(0, len(chord_strs), 8):
          print("  bars %d-%d: %s" % (i, min(i+7, len(chord_strs)-1), ' | '.join(chord_strs[i:i+8])))


if __name__ == '__main__':
  main()
