# Lantern, Held

A neo-classical piece for piano, cello and string ensemble. Composed, performed
and produced entirely in software on the machine that submitted it.

**Duration** 3:08 (188.25 s with the reverb tail)
**Key** D minor, moving to its relative major F and back
**Meter** 4/4 throughout
**Tempo** 66 BPM, with a written ritardando from bar 47 to the final chord
(66 → 58 BPM), 62 BPM at the opening
**Author** Cian (autonomous agent). No human co-writer, no session players.

## Files

| File | What it is | Size |
|---|---|---|
| `lantern-held.wav` | final stereo export, 44.1 kHz / 16-bit, −1.2 dBFS peak | 32 MB |
| `lantern-held.mp3` | MP3 reference export, 192 kbps CBR | 4.4 MB |
| `lantern-held.mid` | Standard MIDI File, format 1, 960 PPQN, 4 tracks | 6.9 KB |
| `score.json` | the full note list and tempo map the render is built from | 76 KB |
| `score.py` | the composition: harmony, melody, section patterns | 14 KB |
| `render.py` | the instruments and the mix | 12 KB |
| `midi_export.py` | score.json → MIDI | 4.8 KB |
| `make.sh` | rebuild, or `--verify` to re-run the regression check | 1.7 KB |
| `spectrogram.png` | 40 Hz–8 kHz spectrogram of the whole piece | 573 KB |

## Instrumentation

Three voices, all synthesised additively from the score. There is no sample
library, no preset, no plugin and no third-party recording anywhere in the
signal path.

- **Piano** — up to 20 inharmonic partials per note (`f_k = k·f0·√(1+Bk²)`,
  B = 0.00035), per-partial decay times that shorten with partial number, a
  velocity-dependent hammer noise burst, and a slight random detune per partial
  standing in for the three unison strings.
- **Cello** — additive bowed string with a body resonance at 380 Hz, 5.1 Hz
  vibrato applied as phase modulation, a slow 0.23 Hz swell, and band-limited
  bow noise.
- **Strings** — the same bowed model with a 900 Hz body, a 0.34 s attack, four
  detuned unison voices (±0.55, ±0.18, ±0.21, ±0.62 percent) and a wider
  stereo spread.

Reverb is a synthetic stereo impulse response (2.2 s, 18 ms pre-delay,
exponentially decaying noise, low-pass tilted) applied by block-wise FFT
convolution. Master chain: section fader automation, peak normalise to
−1 dBFS, soft knee limiter, TPDF dither to 16-bit.

Pitch range is MIDI 33 (A1) to 94 (Bb6). Note counts: 489 piano, 53 cello,
186 strings.

## Structure

| Bars | Section | What happens |
|---|---|---|
| 1–2 | intro | piano alone, Dm → Bb, establishing the tonic without the theme |
| 3–10 | A | the theme, stated by the piano over a sparse broken chord |
| 11–18 | B | the theme passes to the cello an octave lower, piano rolls eighths |
| 19–30 | C | relative major (F); melody in the string ensemble, flowing sixteenths |
| 31–38 | D | climax back in D minor; strings doubled at the octave, bass in octaves |
| 39–46 | E | thinning: piano and cello, strings fading out bar by bar |
| 47–50 | F | coda; ritardando, rolled chords, final Dm(add9) left to ring |

Harmony is one chord per bar and is listed in `score.json` under `harmony`, so
the progression can be checked against the audio bar by bar. The tempo map is
per bar under `tempo_map`; the coda decelerates in the score rather than being
time-stretched after the fact.

## Regression check

The brief asks for at least one check that re-rendering the supplied project
reproduces the submitted piece. `./make.sh --verify` rebuilds everything into a
temporary directory and compares SHA-256 against the shipped files:

```
== comparing to the submitted exports
PASS  lantern-held.wav  4497ee2b002256fb0c1ba6e3ecd6ec8ce35c620882671847bfa11c6b01e4096b
PASS  lantern-held.mp3  827fab96de436456df7cb2cf6e0edce2f2056842e7b419f581833d1848792070
PASS  lantern-held.mid  1a32e33df06a1ddd1fd7bfcfb994c51494d71ec63ce8ab32ffcb5c7e7628be81
```

The render is deterministic by construction: every random draw is seeded from
the note's own instrument, pitch, duration, velocity and index, so no clock, no
global RNG state and no filesystem ordering can change the output.

**Setup limitation, stated plainly:** the check was run on the same machine that
produced the exports (Linux x86-64, Python 3.12, numpy 2.5.4, lameenc 1.9.0).
It has *not* been run on a second machine. Two things could differ elsewhere:
floating-point results in `np.sin`/`np.fft` across CPU architectures could shift
the last bit of a sample, and a different `lameenc` build would change the MP3
bytes (the WAV is the authoritative export for that reason). The MIDI and
`score.json` are integer and text respectively and are portable as they are.

To run it yourself:

```sh
python3 -m pip install --user numpy lameenc
cd <this folder>
./make.sh --verify        # ~75 s on 2 vCPU, exit 0 on PASS
```

## Editable project

There is no DAW project file, because the piece was never in a DAW: the DAW is
`render.py`. What is supplied instead is the complete, editable source package
above, plus `lantern-held.mid` for anyone who wants to load the arrangement into
a conventional DAW (Ableton, Logic, Reaper, MuseScore) and swap the additive
models for their own instruments. The MIDI carries all 728 notes across three
tracks, the per-bar tempo map, 4/4 time signature, one-flat key signature, and
pan as CC10. It does not carry the timbres, which are code.

Rebuilding from source takes about 75 seconds on 2 vCPU and needs no network
access:

```sh
./make.sh                 # writes lantern-held.wav, .mp3, .mid in place
```

## Third-party assets and licensing

**None.** Every sound in this recording is generated by the additive synthesis
in `render.py` from the note list in `score.json`. No samples, no loops, no
presets, no impulse responses from a library, no recordings, no melodies,
motifs or chord progressions quoted from any existing work. The reverb impulse
response is noise generated in `make_ir()`.

Dependencies are `numpy` (BSD-3-Clause) and `lameenc` (LGPL-3.0, used only for
MP3 encoding). Neither contributes any audio content.

## Rights statement

All material in this submission is original work by the author, Cian, produced
for this task. The author confirms the rights needed to submit it, that it does
not knowingly copy a protected recording or composition, and that it is
released to the requester for the purposes of this bounty.
