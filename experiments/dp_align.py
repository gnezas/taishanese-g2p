#!/usr/bin/env python3
"""Duration-informed DP alignment for the DLI Toishan course (CPU, no model).

Why DP: a fixed VAD gap threshold cannot work — measured, lesson 9 needs g=2.0s
(75 segments -> 21, exactly its turn count) while lesson 4 needs g=1.0s and
lesson 31 never gets below 46 units for 22 turns. So instead of choosing a
granularity, let the aligner choose it.

Formulation: monotonic alignment of N text turns onto M raw VAD segments, where
turn i may consume any contiguous run of segments (k+1..j). Cost is the absolute
mismatch between the turn's duration predicted from its character count and the
elapsed audio time of that run, plus a penalty for over-long spans and a small
constant for letting a turn consume no audio at all (the OCR side has spurious
turns). Solved with the standard O(N*M^2) DP, vectorised over j in numpy.

Usage: dp_align.py [--lessons 1-60] [--out FILE]
"""
import argparse, json, math, os, re, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
sys.path.insert(0, ROOT)
from align_dli import audio_for, load_manifest, parse_items   # noqa: E402
from segment_vad import detect, load_audio, SR                # noqa: E402

INF = 1e18
MAX_SPAN = 25.0        # a single speaker turn is not longer than this
EMPTY_PEN = 6.0        # cost of letting a text turn consume no audio
MIN_CHAR_SEC = 0.02


def turns_for_file(fname):
    """All text turns for an audio file, in lesson order (some files cover two lessons)."""
    lessons = []
    for n in range(1, 61):
        if any(r["name"] == fname for r in audio_for(n)):
            lessons.append(n)
    out = []
    for n in sorted(lessons):
        lf = f"{ROOT}/corpus/dli-github/doc/lessons/lesson-{n:02d}.txt"
        if not os.path.exists(lf):
            continue
        text = open(lf, encoding="utf-8").read()
        for _, tl in parse_items(text):
            for _, seg in tl:
                out.append(dict(lesson=n, text=seg, nch=len(seg)))
    return out, sorted(lessons)


def align(turns, segs, alpha, skip_pen=0.25):
    """Monotonic DP with full coverage AND a skip state.

    Two things matter here and both were found by measurement:

    * COVERAGE. Without it the DP degenerates — it gives each turn the shortest
      possible span and leaves the rest of the audio unassigned, which drives the
      fitted duration scale to zero.
    * A SKIP STATE. The tapes carry material the textbook does not (English
      instructions, vocabulary read aloud, drill sections). Forcing every segment
      onto some turn makes the DP dump all that audio into a few turns, which
      showed up as only 70% of turns getting any audio at all. So audio may also
      be *skipped* at a small cost per second, letting non-textual stretches be
      honestly unassigned.

    Returns (path as list of (turn_i, k, j), skipped segment indices, total_cost).
    """
    M = len(segs)
    N = len(turns)
    if M == 0 or N == 0:
        return [], [], INF
    cum_end = np.array([segs[0][0]] + [e for _, e in segs], dtype=float)
    dur = np.array([e - s for s, e in segs], dtype=float)
    pred = np.array([max(alpha * t["nch"], MIN_CHAR_SEC) for t in turns], dtype=float)

    span = cum_end[None, :] - cum_end[:, None]           # [k, j]
    span = np.where(span < 0, 0.0, span)
    valid = np.tril(np.ones((M + 1, M + 1), dtype=bool), k=-1).T   # j > k

    dp = np.full((N + 1, M + 1), INF)
    back = np.zeros((N + 1, M + 1), dtype=np.int32)      # k for a turn
    skipped = np.zeros((N + 1, M + 1), dtype=bool)       # True if step was a skip
    dp[0, 0] = 0.0

    for i in range(1, N + 1):
        cost = np.abs(span - pred[i - 1]) + np.where(span > MAX_SPAN,
                                                     4.0 * (span - MAX_SPAN), 0.0)
        cost = np.where(valid, cost, INF)
        cand = dp[i - 1][:, None] + cost
        kbest = np.argmin(cand, axis=0)
        row = cand[kbest, np.arange(M + 1)]

        # skip state: advance j consuming audio without consuming a turn
        for j in range(1, M + 1):
            sk = dp[i, j - 1] + skip_pen * dur[j - 1]
            if sk < row[j]:
                row[j] = sk
                skipped[i, j] = True
        dp[i] = row
        back[i] = kbest

    j = M
    if not np.isfinite(dp[N, M]):
        return [], [], INF
    total = dp[N, j]
    path, skips = [], []
    i = N
    while i > 0 and j > 0:
        if skipped[i, j]:
            skips.append(j - 1)
            j -= 1
            continue
        k = int(back[i, j])
        path.append((i - 1, k, j))
        j = k
        i -= 1
    path.reverse()
    skips.reverse()
    return path, skips, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lessons", default="1-60")
    ap.add_argument("--out", default=f"{ROOT}/corpus/dp_pairs.tsv")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    lo, hi = (int(x) for x in a.lessons.split("-"))
    files = []
    for n in range(lo, hi + 1):
        for r in audio_for(n):
            if r["name"] not in [f["name"] for f in files]:
                files.append(r)

    rows, per_lesson = [], []
    for r in files:
        turns, lessons = turns_for_file(r["name"])
        if not turns:
            continue
        x = load_audio(f"{ROOT}/corpus/dli/extracted/{r['path']}")
        segs = detect(x)
        speech = sum(e - s for s, e in segs)
        tot_ch = sum(t["nch"] for t in turns)

        # The duration scale is FITTED, not assumed. In a language-lab drill each
        # item is spoken twice (instructor models it, student repeats), so
        # speech_seconds/chars badly underestimates the audio one turn occupies.
        # Score candidate scales by the resulting MEDIAN relative error — scoring
        # by raw DP cost is monotone in alpha and always collapses to the minimum.
        best = None
        for alpha in np.linspace(0.05, 1.60, 32):
            p, sk, c = align(turns, segs, alpha)
            if not p:
                continue
            e = []
            for i, k, j in p:
                if j > k:
                    actual = segs[j - 1][1] - segs[k][0]
                    pred = max(alpha * turns[i]["nch"], MIN_CHAR_SEC)
                    e.append(abs(actual - pred) / pred)
            if len(e) < 0.5 * len(turns):
                continue
            med = float(np.median(e))
            if best is None or med < best[0]:
                best = (med, alpha, p)
        if best is None:
            fb = speech / max(tot_ch, 1)
            p = align(turns, segs, fb)[0]
            best = (float("nan"), fb, p)
        score, alpha, path = best
        _, skips, _ = align(turns, segs, alpha)
        skipped_sec = sum(segs[k][1] - segs[k][0] for k in skips)

        errs = []
        for i, k, j in path:
            actual = (segs[j - 1][1] - segs[k][0]) if j > k else 0.0
            pred = max(alpha * turns[i]["nch"], MIN_CHAR_SEC)
            if j > k:
                errs.append(abs(actual - pred) / pred)
            rows.append(dict(audio=r["name"], lesson=turns[i]["lesson"], i=i,
                             start=segs[k][0] if j > k else None,
                             end=segs[j - 1][1] if j > k else None,
                             dur=actual, pred=pred, rel_err=(errs[-1] if j > k else None),
                             chars=turns[i]["nch"], text=turns[i]["text"]))
        ok = sum(1 for e in errs if e <= 0.5)
        med = float(np.median(errs)) if errs else float("nan")
        per_lesson.append((r["name"], len(turns), len(segs), len(errs), ok, med, score))
        if a.verbose:
            print(f"  {r['name']:24s} turns={len(turns):3d} segs={len(segs):4d} "
                  f"placed={len(errs):3d} within50%={ok:3d} medErr={med:5.2f} "
                  f"alpha={alpha:.2f}")

    with open(a.out, "w", encoding="utf-8") as f:
        f.write("audio\tlesson\tturn\tstart\tend\tdur\tpred\trelerr\tchars\ttext\n")
        for p in rows:
            start = "" if p["start"] is None else f"{p['start']:.2f}"
            end = "" if p["end"] is None else f"{p['end']:.2f}"
            rel = "" if p["rel_err"] is None else f"{p['rel_err']:.3f}"
            text = p["text"].replace("\t", " ")
            f.write(f"{p['audio']}\t{p['lesson']}\t{p['i']}\t{start}\t{end}\t"
                    f"{p['dur']:.2f}\t{p['pred']:.2f}\t{rel}\t{p['chars']}\t{text}\n")

    placed = [p for p in rows if p["start"] is not None]
    errs = [p["rel_err"] for p in placed if p["rel_err"] is not None]
    print(f"\nfiles processed : {len(files)}")
    print(f"turns total     : {len(rows):,}")
    print(f"turns placed    : {len(placed):,} ({100*len(placed)/max(len(rows),1):.0f}%)")
    if errs:
        errs = np.array(errs)
        print(f"relative duration error: median {np.median(errs):.2f}, "
              f"<=25%: {100*np.mean(errs<=0.25):.0f}%, "
              f"<=50%: {100*np.mean(errs<=0.50):.0f}%")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
