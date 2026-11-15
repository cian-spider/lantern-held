#!/usr/bin/env python3
"""Render score.json to a stereo WAV and an MP3.

Everything is synthesised here from the score: no samples, no presets, no
third-party recordings. Three voices:

  piano   additive, inharmonic partials, per-partial decay, hammer noise
  cello   additive sawtooth with a body formant, vibrato, bow noise
  strings additive detuned ensemble with slow attack, vibrato, wide stereo

Then a synthetic stereo impulse response (exponentially decaying noise) for
reverb, block-wise FFT convolution, peak normalisation, soft limiting, TPDF
dither, 16-bit output.

The render is deterministic: all randomness comes from seeds derived from the
note's own fields, so rendering the same score twice gives a byte-identical
WAV. `--verify` uses exactly that to run the regression check.

Usage:
  python3 render.py score.json out.wav [--mp3 out.mp3]
  python3 render.py score.json /tmp/again.wav --verify out.wav
"""

import hashlib
import json
import sys
import wave
import zlib

import numpy as np

SR = 44100
TAIL = 5.0  # seconds of reverb tail after the last bar


# ------------------------------------------------------------------ utils ---
def seed_of(*parts):
    return zlib.crc32("|".join(str(p) for p in parts).encode()) & 0xFFFFFFFF


def pan_gains(p):
    """Equal-power pan, p in [-1, 1]."""
    a = (p + 1.0) * np.pi / 4.0
    return float(np.cos(a)), float(np.sin(a))


def adsr_attack(n, seconds):
    k = max(1, min(n, int(seconds * SR)))
    env = np.ones(n, dtype=np.float32)
    env[:k] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, k, dtype=np.float32))
    return env


def release_fade(n, dur, seconds):
    """Fade the tail after `dur` with an exponential damper."""
    env = np.ones(n, dtype=np.float32)
    i0 = min(n, int(dur * SR))
    if i0 < n:
        t = np.arange(n - i0, dtype=np.float32) / SR
        env[i0:] = np.exp(-t / max(1e-3, seconds / 4.0))
    return env


def shaped_noise(n, rng, centre, width, lo=None, hi=None):
    """Band-limited noise with a log-Gaussian band, built in the frequency
    domain so no sample-by-sample filter loop is needed."""
    if n < 32:
        return np.zeros(max(1, n), dtype=np.float32)
    x = rng.standard_normal(n)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    logf = np.log(np.maximum(f, 1.0))
    resp = np.exp(-0.5 * ((logf - np.log(centre)) / width) ** 2)
    if lo:
        resp *= 1.0 / (1.0 + (lo / np.maximum(f, 1.0)) ** 4)
    if hi:
        resp *= 1.0 / (1.0 + (f / hi) ** 4)
    y = np.fft.irfft(np.fft.rfft(x) * resp, n)
    y /= np.max(np.abs(y)) + 1e-9
    return y.astype(np.float32)


# -------------------------------------------------------------- instruments --
def piano(midi, dur, vel, seed):
    f0 = 440.0 * 2.0 ** ((midi - 69) / 12.0)
    n = int((dur + 0.55) * SR)
    if n <= 0:
        return np.zeros(1, dtype=np.float32)
    t = np.arange(n, dtype=np.float64) / SR
    rng = np.random.default_rng(seed)

    K = int(max(1, min(20, 9000.0 / f0)))
    B = 0.00035  # string inharmonicity
    damp = 0.20 - 0.13 * vel
    tau1 = float(np.clip(2.4 * (261.63 / f0) ** 0.45, 0.55, 4.5))

    out = np.zeros(n, dtype=np.float64)
    for k in range(1, K + 1):
        fk = k * f0 * np.sqrt(1.0 + B * k * k)
        if fk > SR * 0.46:
            break
        ak = (1.0 / k ** 1.32) * np.exp(-(k - 1) * damp)
        tau = tau1 / (1.0 + 0.55 * (k - 1))
        # slight per-partial detune stands in for the three unison strings
        fk *= 1.0 + rng.uniform(-0.0004, 0.0004)
        out += ak * np.exp(-t / tau) * np.sin(2.0 * np.pi * fk * t)

    # hammer: short noise burst, brighter with velocity
    hn = min(n, int(0.012 * SR))
    if hn > 8:
        noise = shaped_noise(hn, rng, 1400.0 + 2600.0 * vel, 0.55).astype(np.float64)
        noise *= np.exp(-np.arange(hn) / (0.0025 * SR))
        out[:hn] += noise * (0.35 * vel)

    out = out.astype(np.float32)
    out *= vel ** 1.15
    out *= adsr_attack(n, 0.004)
    out *= release_fade(n, dur, 0.35)
    return out


def bowed(midi, dur, vel, seed, kind):
    f0 = 440.0 * 2.0 ** ((midi - 69) / 12.0)
    n = int((dur + 0.7) * SR)
    if n <= 0:
        return np.zeros(1, dtype=np.float32)
    t = np.arange(n, dtype=np.float64) / SR
    rng = np.random.default_rng(seed)

    if kind == "cello":
        K, roll, attack, body = int(min(26, 5000.0 / f0)), 1.10, 0.13, 380.0
        detunes = [0.0]
        vib_rate, vib_depth = 5.1, 0.0045
        noise_centre, noise_level = 700.0, 0.035
    else:
        K, roll, attack, body = int(min(26, 8000.0 / f0)), 1.02, 0.34, 900.0
        detunes = [-0.0055, -0.0018, 0.0021, 0.0062]  # cents as fractions
        vib_rate, vib_depth = 4.7, 0.0032
        noise_centre, noise_level = 1800.0, 0.030

    # vibrato as phase modulation, applied identically to every partial
    phase = 2.0 * np.pi * f0 * t + (vib_depth * f0 / vib_rate) * np.sin(
        2.0 * np.pi * vib_rate * t + rng.uniform(0, 6.28))
    # a slow swell keeps a long note from sounding static
    swell = 1.0 + 0.05 * np.sin(2.0 * np.pi * 0.23 * t + rng.uniform(0, 6.28))

    out = np.zeros(n, dtype=np.float64)
    for d in detunes:
        for k in range(1, K + 1):
            fk = k * f0 * (1.0 + d)
            if fk > SR * 0.45:
                break
            ak = (1.0 / k ** roll) * (1.0 + 1.6 * np.exp(-((fk - body) / body) ** 2))
            out += ak * np.sin(k * phase + rng.uniform(0, 6.28))
    out /= max(1.0, len(detunes))
    out *= swell

    # bow noise: band-limited hiss, louder with velocity
    out += shaped_noise(n, rng, noise_centre, 0.9).astype(np.float64) * (
        noise_level * (0.6 + 0.7 * vel))

    out = out.astype(np.float32)
    out *= 0.30 * vel
    out *= adsr_attack(n, attack)
    out *= release_fade(n, dur, 0.45)
    return out


# ------------------------------------------------------------------ reverb --
def make_ir(seconds=2.2, seed=20261115):
    n = int(seconds * SR)
    t = np.arange(n, dtype=np.float32) / SR
    env = np.exp(-t * 3.0)
    pre = int(0.018 * SR)
    env[:pre] = 0.0
    irs = []
    for ch in (0, 1):
        rng = np.random.default_rng(seed + ch)
        x = rng.standard_normal(n).astype(np.float32) * env
        # tilt the tail dark: one-pole lowpass
        a = 0.42
        for i in range(1, n):
            x[i] = a * x[i] + (1.0 - a) * x[i - 1]
        x /= np.sqrt(np.sum(x * x)) + 1e-9
        irs.append(x)
    return irs


def fft_convolve(x, ir, block=1 << 18):
    """Overlap-add convolution, block-wise so memory stays flat."""
    n_ir = len(ir)
    nfft = 1 << int(np.ceil(np.log2(block + n_ir)))
    H = np.fft.rfft(ir, nfft)
    out = np.zeros(len(x) + n_ir, dtype=np.float32)
    for s in range(0, len(x), block):
        chunk = x[s:s + block]
        X = np.fft.rfft(chunk, nfft)
        y = np.fft.irfft(X * H, nfft)[:len(chunk) + n_ir - 1]
        out[s:s + len(y)] += y.astype(np.float32)
    return out


# ------------------------------------------------------------------ render --
def render(score, out_wav, mp3_path=None, verify_wav=None):
    total = float(score["duration_seconds"]) + TAIL
    n = int(total * SR)
    L = np.zeros(n, dtype=np.float32)
    R = np.zeros(n, dtype=np.float32)
    sendL = np.zeros(n, dtype=np.float32)
    sendR = np.zeros(n, dtype=np.float32)

    notes = score["notes"]
    gains = {"piano": 0.9, "cello": 0.62, "strings": 0.5}
    sends = {"piano": 0.34, "cello": 0.55, "strings": 0.5}

    for idx, note in enumerate(notes):
        inst, midi, dur = note["i"], note["m"], note["d"]
        vel, pan = note["v"], note["p"]
        sd = seed_of(inst, midi, round(dur, 3), round(vel, 3), idx)
        if inst == "piano":
            sig = piano(midi, dur, vel, sd)
        else:
            sig = bowed(midi, dur, vel, sd, inst)
        s = int(note["t"] * SR)
        if s >= n:
            continue
        m = min(len(sig), n - s)
        if m <= 0:
            continue
        gl, gr = pan_gains(pan)
        g = gains[inst]
        seg = sig[:m] * g
        L[s:s + m] += seg * gl
        R[s:s + m] += seg * gr
        sv = sig[:m] * g * sends[inst]
        sendL[s:s + m] += sv * gl
        sendR[s:s + m] += sv * gr
        if idx % 100 == 0:
            print(f"  note {idx}/{len(notes)}", flush=True)

    print("  reverb", flush=True)

    # section fader automation, evaluated on a coarse grid and smoothed, so the
    # gain changes over ~1 s instead of stepping at the barline
    auto = score.get("automation") or []
    if auto:
        xs = [0.0] + [a["t"] for a in auto] + [total]
        ys = [auto[0]["gain"]] + [a["gain"] for a in auto] + [auto[-1]["gain"]]
        step = 256
        ts = np.arange(0.0, total, step / SR)
        gs = np.interp(ts, xs, ys)
        k = max(3, int(0.9 * SR / step))
        ker = np.hanning(k)
        ker /= ker.sum()
        gs = np.convolve(gs, ker, mode="same")
        g = np.interp(np.arange(n, dtype=np.float32) / SR, ts, gs).astype(np.float32)
        L *= g
        R *= g
        sendL *= g
        sendR *= g

    irL, irR = make_ir()
    wetL = fft_convolve(sendL, irL)[:n]
    wetR = fft_convolve(sendR, irR)[:n]
    L = L + 0.9 * wetL
    R = R + 0.9 * wetR

    # master: fades, soft limit, normalise, dither
    fade_in = int(0.03 * SR)
    L[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)
    R[:fade_in] *= np.linspace(0, 1, fade_in, dtype=np.float32)
    fade_out = int(3.0 * SR)
    L[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32) ** 1.5
    R[-fade_out:] *= np.linspace(1, 0, fade_out, dtype=np.float32) ** 1.5

    peak = float(max(np.max(np.abs(L)), np.max(np.abs(R))))
    target = 0.891  # -1 dBFS
    L *= target / peak
    R *= target / peak
    knee = 0.72
    for ch in (L, R):
        over = np.abs(ch) > knee
        if over.any():
            s = ch[over]
            ch[over] = np.sign(s) * (knee + (1.0 - knee) * np.tanh((np.abs(s) - knee) / (1.0 - knee)))

    rng = np.random.default_rng(424242)
    dither = (rng.random(n, dtype=np.float32) - rng.random(n, dtype=np.float32)) / 32768.0
    Li = np.clip(np.round((L + dither) * 32767.0), -32768, 32767).astype(np.int16)
    Ri = np.clip(np.round((R + dither) * 32767.0), -32768, 32767).astype(np.int16)
    inter = np.empty(2 * n, dtype=np.int16)
    inter[0::2] = Li
    inter[1::2] = Ri

    print(f"  writing {out_wav}", flush=True)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        step = 1 << 20
        for s in range(0, 2 * n, step):
            w.writeframes(inter[s:s + step].tobytes())

    def digest(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    sha = digest(out_wav)
    stats = {
        "wav": out_wav,
        "sha256": sha,
        "seconds": round(n / SR, 3),
        "peak_dbfs": round(20 * np.log10(float(max(np.max(np.abs(Li / 32767.0)), np.max(np.abs(Ri / 32767.0))))), 2),
        "rms_dbfs": round(20 * np.log10(float(np.sqrt(np.mean((Li / 32767.0) ** 2 + (Ri / 32767.0) ** 2) / 2.0))), 2),
        "clipped_samples": int(np.sum((np.abs(Li.astype(np.int32)) >= 32767))),
    }

    if mp3_path:
        import lameenc
        enc = lameenc.Encoder()
        enc.set_bit_rate(192)
        enc.set_in_sample_rate(SR)
        enc.set_channels(2)
        enc.set_quality(2)
        mp3 = enc.encode(inter.tobytes())
        mp3 += enc.flush()
        with open(mp3_path, "wb") as f:
            f.write(mp3)
        stats["mp3"] = mp3_path
        stats["mp3_bytes"] = len(mp3)
        stats["mp3_sha256"] = digest(mp3_path)
        print(f"  wrote {mp3_path} ({len(mp3)} bytes)", flush=True)

    if verify_wav:
        other = digest(verify_wav)
        stats["verify_against"] = verify_wav
        stats["verify_sha256"] = other
        stats["verify_match"] = other == sha
        print(f"  regression check: {'PASS' if other == sha else 'FAIL'} ({other})", flush=True)

    return stats


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    mp3 = None
    verify = None
    if "--mp3" in args:
        i = args.index("--mp3")
        mp3 = args[i + 1]
        del args[i:i + 2]
    if "--verify" in args:
        i = args.index("--verify")
        verify = args[i + 1]
        del args[i:i + 2]
    score_path, wav_path = args[0], args[1]
    with open(score_path, encoding="utf-8") as f:
        score = json.load(f)
    st = render(score, wav_path, mp3_path=mp3, verify_wav=verify)
    print(json.dumps(st, indent=1))
