#!/usr/bin/env python3
"""Sweep skip cost x duration scale, scored HONESTLY (unplaced turns count as failures).

The earlier 0.13 median excluded the 30% of turns that received no audio, so it
was measured on an easy subset. Any metric here must count a turn with no audio
as a failure, otherwise a degenerate aligner looks good by simply declining.
"""
import os, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
sys.path.insert(0, ROOT)
from align_dli import audio_for, parse_items          # noqa: E402
from segment_vad import detect, load_audio            # noqa: E402
from dp_align import align, turns_for_file            # noqa: E402

LESSONS = [1, 2, 4, 5, 6, 8, 9, 10, 12, 31]
files = []
for n in LESSONS:
    for r in audio_for(n):
        if r["name"] not in [f["name"] for f in files]:
            files.append(r)

cache = {}
for r in files:
    turns, _ = turns_for_file(r["name"])
    x = load_audio(f"{ROOT}/corpus/dli/extracted/{r['path']}")
    cache[r["name"]] = (turns, detect(x))

N_ALL = sum(len(t) for t, _ in cache.values())
print(f"{'skip':>6} {'alpha':>7} | {'placed%':>8} {'medErr':>7} {'<=35%':>7}  (unplaced = fail)")
print("-" * 62)
for skip in (0.10, 0.25, 0.50, 1.00, 2.00):
    best = None
    for alpha in np.linspace(0.05, 1.20, 24):
        errs, n_total = [], 0
        for name, (turns, segs) in cache.items():
            p, sk, c = align(turns, segs, alpha, skip_pen=skip)
            if not p:
                n_total += len(turns); errs += [9.9] * len(turns); continue
            n_total += len(turns)
            for i, k, j in p:
                if j > k:
                    actual = segs[j - 1][1] - segs[k][0]
                else:
                    actual = 0.0
                pred = max(alpha * turns[i]["nch"], 0.02)
                errs.append(abs(actual - pred) / pred)
            # turns the DP never placed (can happen if i ran out) count as failures
            errs += [9.9] * max(0, len(turns) - len(p))
        if best is None or np.median(errs) < best[0]:
            best = (float(np.median(errs)), alpha, float(np.mean(np.array(errs) <= 0.35)),
                    len([e for e in errs if e < 9]))
    med, alpha, frac, placed = best
    print(f"{skip:>6.2f} {alpha:>7.2f} | {100*placed/N_ALL:>7.0f}% {med:>7.2f} {100*frac:>6.0f}%")
