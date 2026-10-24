#!/usr/bin/env python3
"""Energy-based VAD segmentation for DLI lesson tapes (CPU only, no models).

Why not a fixed silencedetect threshold: the DLI tapes vary by ~10 dB between
files (drill-03 peaks at -12 dB, lesson 4 at -1 dB), so any single noise= value
either finds nothing on the quiet tapes or over-cuts the loud ones. This computes
a per-file noise floor from the frame-energy distribution instead.

The DLI drills are language-lab tapes — the instructor reads an item and leaves a
long pause — so silence boundaries line up with utterance boundaries.

Usage:
  segment_vad.py <in.mp3> <outdir> [--tsv out.tsv] [--no-wav]
Writes <base>_NNNN.wav (16 kHz mono) plus a timestamps TSV.
"""
import argparse, os, subprocess

import numpy as np

SR = 16000
FRAME = 0.025          # 25 ms
HOP = 0.010            # 10 ms


def load_audio(path, sr=SR):
    """Decode to mono float32 via ffmpeg using raw PCM (no PyAV, no RIFF header)."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(sr), "-"],
        capture_output=True, check=True)
    if not p.stdout:
        raise RuntimeError(f"ffmpeg produced no audio for {path}")
    return np.frombuffer(p.stdout, dtype=np.int16).astype(np.float32) / 32768.0


def frame_energy(x, frame=FRAME, hop=HOP, sr=SR):
    n = int(frame * sr)
    h = int(hop * sr)
    if len(x) < n:
        return np.zeros(0), h
    count = 1 + (len(x) - n) // h
    idx = np.arange(n)[None, :] + h * np.arange(count)[:, None]
    frames = x[idx]
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12), h


def detect(x, sr=SR, min_speech=0.35, min_gap=0.35, max_utt=15.0, pad=0.12):
    db, h = frame_energy(x, sr=sr)
    if db.size == 0:
        return []
    floor = np.percentile(db, 10)
    peak = np.percentile(db, 99)
    thr = max(floor + 8.0, peak - 30.0)      # clear the floor, stay near the peak
    voiced = db > thr

    # close short unvoiced gaps
    min_gap_f = int(min_gap * sr / h)
    i = 0
    while i < len(voiced):
        if not voiced[i]:
            j = i
            while j < len(voiced) and not voiced[j]:
                j += 1
            if i > 0 and j < len(voiced) and (j - i) < min_gap_f:
                voiced[i:j] = True
            i = j
        else:
            i += 1

    runs, i = [], 0
    while i < len(voiced):
        if voiced[i]:
            j = i
            while j < len(voiced) and voiced[j]:
                j += 1
            runs.append((i * h / sr, j * h / sr))
            i = j
        else:
            i += 1

    out = []
    for a, b in runs:
        if b - a < min_speech:
            continue
        a = max(0.0, a - pad)
        b = min(len(x) / sr, b + pad)
        if b - a > max_utt:                  # split over-long runs evenly
            n = int(np.ceil((b - a) / max_utt))
            step = (b - a) / n
            for k in range(n):
                s0, s1 = a + k * step, a + (k + 1) * step
                if s1 - s0 >= min_speech:
                    out.append((s0, s1))
        else:
            out.append((a, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp")
    ap.add_argument("outdir")
    ap.add_argument("--tsv")
    ap.add_argument("--no-wav", action="store_true")
    ap.add_argument("--max-utt", type=float, default=15.0)
    a = ap.parse_args()

    x = load_audio(a.inp)
    dur = len(x) / SR
    segs = detect(x, max_utt=a.max_utt)
    base = os.path.splitext(os.path.basename(a.inp))[0]
    speech = sum(b - t for t, b in segs)
    print(f"{base}: {dur:.1f}s | {len(segs)} utterances | {speech:.1f}s speech "
          f"({100*speech/dur:.0f}%)")

    if not a.no_wav:
        os.makedirs(a.outdir, exist_ok=True)
        for i, (s, e) in enumerate(segs, 1):
            subprocess.run(
                ["ffmpeg", "-v", "error", "-y", "-i", a.inp, "-ss", f"{s:.3f}",
                 "-to", f"{e:.3f}", "-ac", "1", "-ar", "16000",
                 "-acodec", "pcm_s16le",
                 os.path.join(a.outdir, f"{base}_{i:04d}.wav")], check=True)

    if a.tsv:
        with open(a.tsv, "w", encoding="utf-8") as f:
            f.write("file\tstart\tend\tduration\n")
            for i, (s, e) in enumerate(segs, 1):
                f.write(f"{base}_{i:04d}.wav\t{s:.3f}\t{e:.3f}\t{e-s:.3f}\n")


if __name__ == "__main__":
    main()
