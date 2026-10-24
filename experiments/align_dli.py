#!/usr/bin/env python3
"""Order-based text<->audio alignment for the DLI Toishan course.

Whisper cannot transcribe Taishanese (verified: it returns confident gibberish),
so there is no acoustic model to force-align against. But this corpus does not
need one: the drills are rigidly structured — the instructor reads numbered item
1, pauses, item 2, pauses — and the OCR'd textbook has those same numbers. So
alignment is monotonic and structural:

  1. parse the OCR'd lesson text into numbered items
  2. segment the lesson audio by silence (adaptive VAD)
  3. if the counts line up, pair in order; if not, re-cut the audio at its
     longest silences so the count matches the text exactly

Usage: align_dli.py <lesson_no> [--report]
"""
import argparse, json, os, re, subprocess, sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
sys.path.insert(0, ROOT)
from segment_vad import detect, load_audio, SR      # noqa: E402

CJK = re.compile(r"[\u3400-\u9fff]")
ITEM = re.compile(r"(?<![\d.])(\d{1,2})\s*[.。．、,，:：]\s*")


def load_manifest():
    rows = []
    for line in open(f"{ROOT}/corpus/dli_corpus.tsv", encoding="utf-8").read().splitlines()[1:]:
        path, dur, vol, kind, name = line.split("\t")
        rows.append(dict(path=path, dur=float(dur), vol=int(vol), kind=kind, name=name))
    return rows


def audio_for(lesson):
    """Map a course lesson number (1..60) to its audio file(s).

    The `lNN` in the filename is the GLOBAL lesson number, not per-volume:
    toisan-v02-l21 is lesson 21, not volume-2 lesson 1. Volumes 1-3 cover
    lessons 1-20 / 21-40 / 41-60 respectively. Volumes 4-6 RESTART at l01 —
    they are a separate edition, so they are excluded here or every lesson
    would match twice.
    """
    out = []
    for r in load_manifest():
        if r["kind"] == "Drills":
            continue
        nums = [int(x) for x in re.findall(r"\d+", r["name"])]
        if not nums:
            continue
        vol = nums[0]                     # first number is the volume
        covered = nums[1:]                # the rest are lesson numbers
        if vol > 3:
            continue
        if lesson in covered:
            out.append(r)
    return out


TURN = re.compile(r"(?<![\u4e00-\u9fff])([AB司茧嚀嗞芽])[：:]\s*")


def parse_items(text):
    """Split OCR'd lesson text into numbered items, then into A/B turns.

    A turn is the natural alignment unit: the tape plays one speaker's line, then
    pauses. Numbers appear both at line starts and mid-line in the OCR, so match
    them anywhere rather than anchoring to ^.
    """
    hits = list(ITEM.finditer(text))
    items = []
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        body = re.sub(r"\s+", " ", text[m.end():end]).strip()
        if not body:
            continue
        turns = []
        tm = list(TURN.finditer(body))
        for j, t in enumerate(tm):
            te = tm[j + 1].start() if j + 1 < len(tm) else len(body)
            seg = body[t.end():te].strip(" •·．.,，")
            if len(seg) >= 2:
                turns.append((t.group(1), seg))
        if not turns:
            turns = [("", body)]
        items.append((int(m.group(1)), turns))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lesson", type=int)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--outdir")
    a = ap.parse_args()

    lf = f"{ROOT}/corpus/dli-github/doc/lessons/lesson-{a.lesson:02d}.txt"
    text = open(lf, encoding="utf-8").read()
    items = parse_items(text)
    turns = [seg for _, tl in items for _, seg in tl]
    auds = audio_for(a.lesson)
    print(f"lesson {a.lesson}: {len(items)} items -> {len(turns)} turns | "
          f"{len(auds)} audio file(s)")
    if auds:
        print(f"   audio: {[r['name'] for r in auds]}")

    if a.report:
        for i, t in enumerate(turns[:10]):
            print(f"   {i+1:>2}. {t[:70]}")
        return

    if not auds:
        print("no audio for this lesson"); return

    r = auds[0]
    x = load_audio(f"{ROOT}/corpus/dli/extracted/{r['path']}")
    segs = detect(x)
    print(f"  audio {r['name']}: {len(x)/SR:.0f}s, {len(segs)} VAD utterances")
    print(f"  text turns: {len(turns)}")

    n_txt, n_aud = len(turns), len(segs)
    if n_txt and abs(n_txt - n_aud) <= max(2, 0.15 * n_txt):
        pairs = [(turns[i], segs[i]) for i in range(min(n_txt, n_aud))]
        method = "direct order match"
    else:
        # re-cut the audio at its longest silences so counts match the text
        pairs, method = [], f"count-normalised ({n_aud} -> {n_txt})"
        # boundaries between utterances = midpoints of the gaps
        bounds = [0.0]
        for (_, e0), (s1, _) in zip(segs, segs[1:]):
            bounds.append((e0 + s1) / 2)
        bounds.append(len(x) / SR)
        if n_txt < len(bounds) - 1:
            gaps = sorted(((bounds[i + 1] - bounds[i]), i) for i in range(len(bounds) - 1))
            keep = set()
            for _, i in gaps[:n_txt - 1]:
                keep.add(i)
            cuts = [bounds[i] for i in sorted(keep)] + [bounds[-1]]
            cuts = [0.0] + cuts
        else:
            cuts = bounds[:n_txt + 1]
        for i in range(min(len(cuts) - 1, n_txt)):
            pairs.append((turns[i], (cuts[i], cuts[i + 1])))

    print(f"  method: {method}")
    print(f"  pairs produced: {len(pairs)}\n")
    for txt, (s, e) in pairs[:10]:
        print(f"   [{s:6.1f}-{e:6.1f}]  {txt[:60]}")

    if a.outdir:
        os.makedirs(a.outdir, exist_ok=True)
        with open(os.path.join(a.outdir, f"lesson-{a.lesson:02d}.pairs.json"), "w", encoding="utf-8") as f:
            json.dump([{"start": s, "end": e, "text": t, "audio": r["path"]}
                       for t, (s, e) in pairs], f, ensure_ascii=False, indent=1)
        print(f"\nwrote pairs to {a.outdir}")


if __name__ == "__main__":
    main()
