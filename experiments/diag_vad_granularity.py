#!/usr/bin/env python3
"""Diagnostic: what VAD granularity actually matches textbook speaker turns?

The DP aligner only has a chance if one audio unit ~ one text turn. The raw VAD
gives ~9 segments per turn, so the question is whether merging nearby segments
(raising the effective min-gap) collapses them to the turn count.

Reports, per lesson, the text turn count vs the audio unit count at several
gap-merge thresholds.
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
sys.path.insert(0, ROOT)
from align_dli import audio_for, parse_items          # noqa: E402
from segment_vad import detect, load_audio, SR        # noqa: E402


def merge(segs, gap):
    """Merge segments separated by less than `gap` seconds."""
    if not segs:
        return []
    out = [list(segs[0])]
    for s, e in segs[1:]:
        if s - out[-1][1] < gap:
            out[-1][1] = e
        else:
            out.append([s, e])
    return [tuple(x) for x in out]


def main():
    lessons = [int(x) for x in sys.argv[1:]] or [4, 5, 8, 9, 12, 10, 31, 2]
    gaps = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]
    print(f"{'lesson':>6} {'turns':>6} | " + " ".join(f"g={g:<4}" for g in gaps))
    print("-" * 62)
    for n in lessons:
        lf = f"{ROOT}/corpus/dli-github/doc/lessons/lesson-{n:02d}.txt"
        if not os.path.exists(lf):
            continue
        turns = [s for _, tl in parse_items(open(lf, encoding="utf-8").read())
                 for _, s in tl]
        auds = audio_for(n)
        if not auds:
            continue
        x = load_audio(f"{ROOT}/corpus/dli/extracted/{auds[0]['path']}")
        base = detect(x)
        counts = [len(merge(base, g)) for g in gaps]
        flag = "  <== best" if counts and min(
            abs(c - len(turns)) for c in counts) <= max(2, 0.2 * len(turns)) else ""
        print(f"{n:>6} {len(turns):>6} | " + " ".join(f"{c:<6}" for c in counts) + flag)


if __name__ == "__main__":
    main()
