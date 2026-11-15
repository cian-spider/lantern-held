#!/usr/bin/env python3
"""Build the score for "Lantern, Held" -- a neo-classical piece in D minor.

This file is the *composition*, not the renderer: it expands harmony, a hand
written melody and per-section accompaniment patterns into an explicit note
list plus a tempo map, and writes it to score.json. render.py turns that JSON
into audio. Nothing here is random, so score.json is byte-reproducible.

Structure (4/4, 66 bpm except where the tempo map says otherwise):

    bars  1- 2  intro, solo piano
    bars  3-10  A  theme on piano
    bars 11-18  B  theme in the cello, piano arpeggiates
    bars 19-30  C  relative major (F), melody in the string ensemble
    bars 31-38  D  climax in D minor, strings doubled at the octave
    bars 39-46  E  thinning, piano and cello
    bars 47-50  F  coda, ritardando, final Dm(add9)

Usage:  python3 score.py [out.json]
"""

import json
import sys

# ---------------------------------------------------------------- harmony ---
# Each chord: bass note (midi) and four voicing tones above it.
CHORDS = {
    "Dm":   {"bass": 38, "tones": [50, 53, 57, 62]},   # D2  D3 F3 A3 D4
    "Bb":   {"bass": 34, "tones": [46, 50, 53, 58]},   # Bb1 Bb2 D3 F3 Bb3
    "F":    {"bass": 41, "tones": [45, 48, 53, 57]},   # F2  A2 C3 F3 A3
    "C":    {"bass": 36, "tones": [48, 52, 55, 60]},   # C2  C3 E3 G3 C4
    "Gm":   {"bass": 43, "tones": [46, 50, 55, 58]},   # G2  Bb2 D3 G3 Bb3
    "A":    {"bass": 33, "tones": [45, 49, 52, 57]},   # A1  A2 C#3 E3 A3
    "F/A":  {"bass": 45, "tones": [48, 53, 57, 60]},   # A2  C3 F3 A3 C4
    "C/E":  {"bass": 40, "tones": [43, 48, 52, 55]},   # E2  G2 C3 E3 G3
    "Dm/F": {"bass": 41, "tones": [45, 50, 53, 57]},   # F2  A2 D3 F3 A3
}

# One chord per bar, 1-indexed by bar number.
HARMONY = {
    1: "Dm", 2: "Bb",
    # A
    3: "Dm", 4: "Bb", 5: "F", 6: "C", 7: "Dm", 8: "Gm", 9: "Bb", 10: "A",
    # B
    11: "Dm", 12: "Bb", 13: "F", 14: "C",
    15: "Dm", 16: "Gm", 17: "Bb", 18: "A",
    # C
    19: "F", 20: "C/E", 21: "Dm", 22: "Bb",
    23: "F", 24: "C", 25: "Bb", 26: "F/A",
    27: "Gm", 28: "Bb", 29: "Dm/F", 30: "A",
    # D
    31: "Dm", 32: "Bb", 33: "F", 34: "C",
    35: "Gm", 36: "Bb", 37: "A", 38: "A",
    # E
    39: "Dm", 40: "Bb", 41: "F", 42: "C",
    43: "Dm", 44: "Gm", 45: "Bb", 46: "A",
    # F
    47: "Bb", 48: "Gm", 49: "Dm", 50: "Dm",
}

LAST_BAR = 50

# Tempo per bar. The coda slows down for real rather than being a post-hoc
# time-stretch, so the internal proportions of each bar stay musical.
TEMPO = {}
for b in range(1, LAST_BAR + 1):
    TEMPO[b] = 66.0
TEMPO[1] = 62.0
TEMPO[2] = 63.0
TEMPO.update({47: 65.0, 48: 63.0, 49: 61.0, 50: 58.0})

# --------------------------------------------------------------- melody -----
# (bar, beat, duration_in_beats, midi, velocity)
# beat is 1-based within the bar; duration may run past the barline.
MELODY = [
    # A -- theme, right hand
    (3, 1, 2.0, 69, 0.62), (3, 3, 2.0, 74, 0.66),
    (4, 1, 1.5, 77, 0.70), (4, 2.5, 0.5, 76, 0.62), (4, 3, 2.0, 74, 0.68),
    (5, 1, 2.0, 72, 0.64), (5, 3, 2.0, 69, 0.60),
    (6, 1, 4.0, 67, 0.58),
    (7, 1, 1.0, 69, 0.62), (7, 2, 1.0, 70, 0.60), (7, 3, 2.0, 69, 0.64),
    (8, 1, 1.5, 67, 0.60), (8, 2.5, 0.5, 65, 0.56), (8, 3, 1.0, 67, 0.60), (8, 4, 1.0, 70, 0.64),
    (9, 1, 2.0, 74, 0.68), (9, 3, 2.0, 77, 0.72),
    (10, 1, 4.0, 76, 0.70),
    # C -- melody in the strings (written in the piano list, instrument assigned later)
    (19, 1, 2.0, 69, 0.60), (19, 3, 2.0, 72, 0.64),
    (20, 1, 1.5, 70, 0.62), (20, 2.5, 0.5, 69, 0.58), (20, 3, 2.0, 67, 0.60),
    (21, 1, 2.0, 69, 0.60), (21, 3, 2.0, 74, 0.66),
    (22, 1, 3.0, 77, 0.70), (22, 4, 1.0, 74, 0.62),
    (23, 1, 2.0, 72, 0.64), (23, 3, 2.0, 69, 0.60),
    (24, 1, 2.0, 67, 0.60), (24, 3, 2.0, 72, 0.64),
    (25, 1, 1.5, 74, 0.64), (25, 2.5, 0.5, 72, 0.60), (25, 3, 2.0, 70, 0.60),
    (26, 1, 4.0, 69, 0.60),
    (27, 1, 2.0, 70, 0.60), (27, 3, 2.0, 74, 0.64),
    (28, 1, 2.0, 77, 0.70), (28, 3, 2.0, 74, 0.64),
    (29, 1, 2.0, 69, 0.60), (29, 3, 2.0, 74, 0.64),
    (30, 1, 4.0, 73, 0.62),
    # D -- climax, strings doubled an octave up
    (31, 1, 2.0, 77, 0.78), (31, 3, 2.0, 81, 0.82),
    (32, 1, 2.0, 77, 0.80), (32, 3, 1.0, 74, 0.74), (32, 4, 1.0, 77, 0.78),
    (33, 1, 2.0, 76, 0.78), (33, 3, 2.0, 72, 0.74),
    (34, 1, 2.0, 74, 0.76), (34, 3, 2.0, 76, 0.78),
    (35, 1, 2.0, 74, 0.76), (35, 3, 2.0, 70, 0.72),
    (36, 1, 1.0, 74, 0.76), (36, 2, 1.0, 77, 0.80), (36, 3, 2.0, 82, 0.84),
    (37, 1, 2.0, 81, 0.82), (37, 3, 2.0, 79, 0.78),
    (38, 1, 4.0, 76, 0.74),
    # E -- thinning, piano again
    (39, 1, 2.0, 69, 0.56), (39, 3, 2.0, 74, 0.60),
    (40, 1, 2.0, 77, 0.62), (40, 3, 2.0, 74, 0.58),
    (41, 1, 2.0, 72, 0.56), (41, 3, 2.0, 69, 0.54),
    (42, 1, 4.0, 67, 0.52),
    (43, 1, 1.0, 69, 0.54), (43, 2, 1.0, 70, 0.52), (43, 3, 2.0, 69, 0.56),
    (44, 1, 2.0, 67, 0.52), (44, 3, 2.0, 70, 0.54),
    (45, 1, 4.0, 74, 0.56),
    (46, 1, 2.0, 76, 0.58), (46, 3, 2.0, 74, 0.54),
    # F -- coda
    (47, 1, 2.0, 77, 0.52), (47, 3, 2.0, 74, 0.50),
    (48, 1, 2.0, 70, 0.48), (48, 3, 2.0, 67, 0.46),
    (49, 1, 4.0, 69, 0.46),
]

# Which bars the melody is played by the string ensemble instead of the piano.
STRINGS_MELODY_BARS = set(range(19, 31)) | set(range(31, 39))

# Section B: the theme handed to the cello, an octave below where the piano
# stated it. The piano joins in the upper octave for the last two bars only.
CELLO_THEME = [
    (11, 1, 2.0, 57, 0.60), (11, 3, 2.0, 62, 0.64),
    (12, 1, 1.5, 65, 0.66), (12, 2.5, 0.5, 64, 0.58), (12, 3, 2.0, 62, 0.64),
    (13, 1, 2.0, 60, 0.60), (13, 3, 2.0, 57, 0.56),
    (14, 1, 4.0, 55, 0.54),
    (15, 1, 1.0, 57, 0.60), (15, 2, 1.0, 58, 0.56), (15, 3, 2.0, 57, 0.62),
    (16, 1, 1.5, 55, 0.58), (16, 2.5, 0.5, 53, 0.52), (16, 3, 1.0, 55, 0.58), (16, 4, 1.0, 58, 0.62),
    (17, 1, 2.0, 62, 0.66), (17, 3, 2.0, 65, 0.70),
    (18, 1, 4.0, 64, 0.68),
]

# ------------------------------------------------------------ accompaniment --
# Pattern = list of (beat, step, dur_beats, velocity), where step indexes
# [bass] + tones. Section -> pattern.
PATTERNS = {
    "A": [  # sparse broken chord, quarters
        (1, 1, 1.0, 0.40), (2, 2, 1.0, 0.34), (3, 3, 1.0, 0.36), (4, 2, 1.0, 0.30),
    ],
    "B": [  # rolling eighths
        (1.0, 0, 0.9, 0.36), (1.5, 2, 0.9, 0.26), (2.0, 3, 0.9, 0.30), (2.5, 4, 0.9, 0.28),
        (3.0, 3, 0.9, 0.30), (3.5, 2, 0.9, 0.26), (4.0, 1, 0.9, 0.32), (4.5, 2, 0.9, 0.26),
    ],
    "C": [  # flowing sixteenths
        (1.00, 1, 0.9, 0.30), (1.25, 2, 0.9, 0.22), (1.50, 3, 0.9, 0.26), (1.75, 4, 0.9, 0.24),
        (2.00, 3, 0.9, 0.26), (2.25, 2, 0.9, 0.22), (2.50, 1, 0.9, 0.28), (2.75, 2, 0.9, 0.22),
        (3.00, 3, 0.9, 0.26), (3.25, 4, 0.9, 0.24), (3.50, 3, 0.9, 0.26), (3.75, 2, 0.9, 0.22),
        (4.00, 1, 0.9, 0.30), (4.25, 2, 0.9, 0.22), (4.50, 3, 0.9, 0.26), (4.75, 4, 0.9, 0.24),
    ],
    "D": [  # bass octaves on the beat, chord on the off-beats
        (1.0, 0, 0.9, 0.46), (1.5, 2, 0.4, 0.26), (2.0, 3, 0.4, 0.28), (2.5, 4, 0.4, 0.30),
        (3.0, 0, 0.9, 0.44), (3.5, 2, 0.4, 0.26), (4.0, 3, 0.4, 0.28), (4.5, 4, 0.4, 0.30),
    ],
    "E": [  # quarters again, softer
        (1, 0, 1.0, 0.34), (2, 2, 1.0, 0.28), (3, 3, 1.0, 0.30), (4, 2, 1.0, 0.26),
    ],
}

# bar -> section
SECTION = {}
for b in range(1, 3):    SECTION[b] = "A"
for b in range(3, 11):   SECTION[b] = "A"
for b in range(11, 19):  SECTION[b] = "B"
for b in range(19, 31):  SECTION[b] = "C"
for b in range(31, 39):  SECTION[b] = "D"
for b in range(39, 47):  SECTION[b] = "E"
for b in range(47, 55):  SECTION[b] = "F"

# Section velocity trim applied to accompaniment (keeps the balance sane).
SECTION_TRIM = {"A": 1.0, "B": 1.0, "C": 0.95, "D": 1.0, "E": 0.9, "F": 0.8}

# Mix fader per section. Applied by render.py as a smoothed gain curve, so the
# piece opens and closes rather than sitting at one level.
SECTION_GAIN = {"A": 0.80, "B": 0.86, "C": 0.94, "D": 1.00, "E": 0.86, "F": 0.74}

# --------------------------------------------------------------- builder ----

def bar_seconds():
    """Start time in seconds of every bar, from the tempo map."""
    start = {}
    t = 0.0
    for b in range(1, LAST_BAR + 1):
        start[b] = t
        t += 4.0 * 60.0 / TEMPO[b]
    return start, t


def build():
    bar_t, total = bar_seconds()
    beat_len = {b: 60.0 / TEMPO[b] for b in TEMPO}
    notes = []

    def add(inst, midi, t, dur, vel, pan=0.0):
        notes.append({
            "i": inst, "m": int(midi),
            "t": round(t, 6), "d": round(max(0.05, dur), 6),
            "v": round(min(1.0, max(0.02, vel)), 4), "p": round(pan, 3),
        })

    def t_of(bar, beat):
        return bar_t[bar] + (beat - 1.0) * beat_len[bar]

    # --- accompaniment ---
    for bar in range(1, LAST_BAR + 1):
        chord = CHORDS[HARMONY[bar]]
        steps = [chord["bass"]] + chord["tones"]
        sec = SECTION[bar]
        if sec == "F":
            # Coda: one rolled chord per bar, slower and softer as it goes.
            if bar in (47, 48, 49):
                roll = steps
                for n, midi in enumerate(roll):
                    add("piano", midi, t_of(bar, 1) + n * 0.055, 3.4,
                        0.34 * SECTION_TRIM["F"], pan=-0.25 + 0.12 * n)
            continue
        trim = SECTION_TRIM[sec]
        for beat, step, dur, vel in PATTERNS[sec]:
            midi = steps[step]
            if sec == "D":
                # climax: bass doubled at the octave, chords a touch wider
                if step == 0:
                    add("piano", midi, t_of(bar, beat), dur * beat_len[bar], vel * trim, pan=-0.3)
                    add("piano", midi + 12, t_of(bar, beat), dur * beat_len[bar], vel * trim * 0.7, pan=-0.1)
                    continue
                midi = midi + 12 if step >= 3 else midi
            pan = -0.3 + 0.1 * step
            add("piano", midi, t_of(bar, beat), dur * beat_len[bar], vel * trim, pan=pan)

    # --- final chord, bar 50, rolled and left to ring ---
    for n, midi in enumerate([38, 45, 50, 53, 55, 57, 62, 69]):
        add("piano", midi, t_of(50, 1) + n * 0.09, 5.0, 0.50 - 0.02 * n, pan=-0.3 + 0.08 * n)

    # --- section B: the theme in the cello ---
    for bar, beat, dbeats, midi, vel in CELLO_THEME:
        t = t_of(bar, beat)
        dur = dbeats * beat_len[bar]
        add("cello", midi, t, dur * 1.08, vel, pan=-0.12)
        if bar >= 17:
            add("piano", midi + 12, t, dur, vel * 0.42, pan=0.22)

    # --- melody ---
    for bar, beat, dbeats, midi, vel in MELODY:
        t = t_of(bar, beat)
        dur = dbeats * beat_len[bar]
        if bar in STRINGS_MELODY_BARS:
            add("strings", midi, t, dur, vel, pan=0.12)
            if SECTION[bar] == "D":
                add("strings", midi + 12, t, dur, vel * 0.62, pan=-0.12)
                add("piano", midi, t, dur, vel * 0.55, pan=0.2)
        else:
            add("piano", midi, t, dur, vel, pan=0.18)
            if SECTION[bar] in ("B", "E"):
                # cello shadows the piano theme an octave below
                add("cello", midi - 12, t, dur * 1.15, vel * 0.8, pan=-0.15)

    # --- cello pedal in the climax, strings pad in C/D/E ---
    for bar in range(31, 39):
        root = CHORDS[HARMONY[bar]]["bass"]
        add("cello", root + 12, t_of(bar, 1), 4.0 * beat_len[bar] * 0.98, 0.5, pan=-0.18)
    for bar in range(19, 31):
        root = CHORDS[HARMONY[bar]]["bass"]
        add("cello", root + 12, t_of(bar, 1), 4.0 * beat_len[bar] * 0.96, 0.30, pan=-0.2)
    for bar in range(11, 19):
        chord = CHORDS[HARMONY[bar]]
        for k, midi in enumerate(chord["tones"][:3]):
            add("strings", midi + 12, t_of(bar, 1), 4.0 * beat_len[bar] * 0.97,
                0.16, pan=-0.35 + 0.35 * k)
    for bar in list(range(19, 31)) + list(range(31, 39)):
        chord = CHORDS[HARMONY[bar]]
        v = 0.24 if bar < 31 else 0.34
        for k, midi in enumerate(chord["tones"]):
            add("strings", midi + 12, t_of(bar, 1), 4.0 * beat_len[bar] * 0.97,
                v, pan=-0.4 + 0.27 * k)
    for bar in range(39, 47):
        chord = CHORDS[HARMONY[bar]]
        v = 0.20 - 0.012 * (bar - 39)
        for k, midi in enumerate(chord["tones"][:3]):
            add("strings", midi + 12, t_of(bar, 1), 4.0 * beat_len[bar] * 0.97,
                max(0.05, v), pan=-0.35 + 0.35 * k)

    notes.sort(key=lambda n: (n["t"], n["m"]))

    automation = []
    for bar in sorted(SECTION):
        sec = SECTION[bar]
        if not automation or automation[-1]["section"] != sec:
            automation.append({"bar": bar, "section": sec,
                               "t": round(bar_t[bar], 4),
                               "gain": SECTION_GAIN[sec]})

    return {
        "title": "Lantern, Held",
        "key": "D minor, moving to F major and back",
        "meter": "4/4",
        "sample_rate": 44100,
        "bars": LAST_BAR,
        "tempo_map": {str(b): TEMPO[b] for b in TEMPO},
        "duration_seconds": round(total, 3),
        "harmony": {str(b): HARMONY[b] for b in HARMONY},
        "automation": automation,
        "sections": {
            "A": "bars 1-10, solo piano, theme stated",
            "B": "bars 11-18, cello takes the theme, piano arpeggiates",
            "C": "bars 19-30, relative major, melody in the string ensemble",
            "D": "bars 31-38, climax in D minor, strings doubled at the octave",
            "E": "bars 39-46, thinning, piano and cello",
            "F": "bars 47-50, coda, ritardando, final Dm(add9)",
        },
        "notes": notes,
    }


if __name__ == "__main__":
    score = build()
    out = sys.argv[1] if len(sys.argv) > 1 else "score.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(score, f, indent=1, sort_keys=False)
        f.write("\n")
    print(f"{out}: {len(score['notes'])} notes, {score['duration_seconds']}s")
