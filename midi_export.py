#!/usr/bin/env python3
"""Export score.json to a Standard MIDI File (format 1).

The MIDI is the editable interchange copy of the piece: three tracks, a real
tempo map, and note-on/note-off pairs at the positions render.py uses. Open it
in any DAW, swap in your own instruments, and the arrangement is intact.

Pan and velocity carry over as CC10 and note velocity. Instrument sounds do
not: MIDI has no way to say "this additive model with a 380 Hz body formant",
so the program changes are only the closest General MIDI names.

Usage:  python3 midi_export.py score.json lantern-held.mid
"""

import json
import struct
import sys

TPQN = 960  # ticks per quarter note

GM = {"piano": 0, "cello": 42, "strings": 48}   # Acoustic Grand, Cello, String Ensemble 1
TRACK_NAME = {"piano": "Piano", "cello": "Cello", "strings": "Strings"}


def vlq(n):
    """MIDI variable-length quantity."""
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def tempo_events(score):
    """Bar -> seconds is already in the score; convert each tempo change to a
    tick position and a microseconds-per-quarter value."""
    ev = []
    tick = 0
    bars = int(score["bars"])
    tempo = score["tempo_map"]
    for b in range(1, bars + 1):
        bpm = tempo[str(b)]
        ev.append((tick, 0x51, int(round(60_000_000 / bpm))))
        tick += 4 * TPQN   # 4/4 throughout
    return ev


def seconds_to_ticks(score):
    """A function mapping seconds to MIDI ticks, integrating the tempo map."""
    tempo = score["tempo_map"]
    bars = int(score["bars"])
    # tick position of each barline
    bar_tick = {}
    tick = 0
    for b in range(1, bars + 1):
        bar_tick[b] = tick
        tick += 4 * TPQN
    bar_sec = {}
    t = 0.0
    for b in range(1, bars + 1):
        bar_sec[b] = t
        t += 4.0 * 60.0 / tempo[str(b)]
    bounds = [(bar_sec[b], bar_tick[b], tempo[str(b)]) for b in range(1, bars + 1)]
    bounds.append((t, tick, tempo[str(bars)]))

    def f(sec):
        for i in range(len(bounds) - 1):
            t0, k0, bpm = bounds[i]
            t1 = bounds[i + 1][0]
            if sec < t1 or i == len(bounds) - 2:
                return int(round(k0 + (sec - t0) * bpm / 60.0 * TPQN))
        return bounds[-1][1]

    return f


def track_chunk(name, events):
    """events: list of (abs_tick, bytes). Serialised with delta times."""
    data = bytearray()
    data += b"\x00\xff\x03" + vlq(len(name)) + name.encode()
    last = 0
    for tick, payload in sorted(events, key=lambda e: (e[0], e[1])):
        data += vlq(tick - last) + payload
        last = tick
    data += b"\x00\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def build(score):
    to_tick = seconds_to_ticks(score)
    tracks = {}

    # conductor track: tempo map, time signature, key signature (D minor = 1 flat)
    cond = []
    for tick, kind, value in tempo_events(score):
        cond.append((tick, bytes([0xFF, 0x51, 0x03]) + value.to_bytes(3, "big")))
    cond.append((0, bytes([0xFF, 0x58, 0x04, 4, 2, 24, 8])))       # 4/4
    cond.append((0, bytes([0xFF, 0x59, 0x02, 0xFD, 0x00])))        # 1 flat, minor
    tracks[0] = track_chunk("Conductor", cond)

    channels = {"piano": 0, "cello": 1, "strings": 2}
    ev = {0: [], 1: [], 2: []}
    for ch, inst in enumerate(("piano", "cello", "strings")):
        ev[ch].append((0, bytes([0xC0 | ch, GM[inst]])))
    # pan once per channel, from the mean pan of its notes
    for ch, inst in enumerate(("piano", "cello", "strings")):
        pans = [n["p"] for n in score["notes"] if n["i"] == inst]
        if pans:
            v = int(round((sum(pans) / len(pans) + 1.0) / 2.0 * 127))
            ev[ch].append((0, bytes([0xB0 | ch, 10, max(0, min(127, v))])))

    for note in score["notes"]:
        ch = channels[note["i"]]
        on = to_tick(note["t"])
        off = max(on + 10, to_tick(note["t"] + note["d"]))
        vel = max(1, min(127, int(round(note["v"] * 127))))
        midi = max(0, min(127, note["m"]))
        ev[ch].append((on, bytes([0x90 | ch, midi, vel])))
        ev[ch].append((off, bytes([0x80 | ch, midi, 64])))

    out = bytearray()
    out += b"MThd" + struct.pack(">IHHH", 6, 1, 4, TPQN)
    out += tracks[0]
    for ch, inst in enumerate(("piano", "cello", "strings")):
        out += track_chunk(TRACK_NAME[inst], ev[ch])
    return bytes(out)


if __name__ == "__main__":
    score_path = sys.argv[1] if len(sys.argv) > 1 else "score.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "lantern-held.mid"
    with open(score_path, encoding="utf-8") as f:
        score = json.load(f)
    data = build(score)
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"{out_path}: {len(data)} bytes, {len(score['notes'])} notes, 4 tracks")
