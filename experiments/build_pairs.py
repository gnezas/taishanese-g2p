#!/usr/bin/env python3
"""Run the text<->audio alignment across all 60 DLI lessons and emit one manifest.

Each lesson: parse OCR'd text into A/B turns, VAD the lesson audio, pair
monotonically, and record how the pairing was derived so low-confidence lessons
stay visible rather than silently looking as good as the clean ones.

Usage: build_pairs.py [--outdir DIR]
"""
import argparse, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
sys.path.insert(0, ROOT)
from align_dli import audio_for, parse_items, load_manifest   # noqa: E402
from segment_vad import detect, load_audio, SR                # noqa: E402

CJK_OK = None


def pairs_for(lesson):
    lf = f"{ROOT}/corpus/dli-github/doc/lessons/lesson-{lesson:02d}.txt"
    if not os.path.exists(lf):
        return None
    text = open(lf, encoding="utf-8").read()
    turns = [seg for _, tl in parse_items(text) for _, seg in tl]
    auds = audio_for(lesson)
    if not auds or not turns:
        return dict(lesson=lesson, turns=len(turns), vad=0, pairs=[],
                    method="no-audio" if not auds else "no-text", secs=0.0)
    r = auds[0]
    x = load_audio(f"{ROOT}/corpus/dli/extracted/{r['path']}")
    segs = detect(x)
    n_txt, n_aud = len(turns), len(segs)
    if abs(n_txt - n_aud) <= max(2, 0.15 * n_txt):
        pr = [(turns[i], segs[i]) for i in range(min(n_txt, n_aud))]
        method = "direct"
    else:
        bounds = [0.0]
        for (_, e0), (s1, _) in zip(segs, segs[1:]):
            bounds.append((e0 + s1) / 2)
        bounds.append(len(x) / SR)
        pr = []
        if n_txt < len(bounds) - 1:
            gaps = sorted(((bounds[i + 1] - bounds[i]), i) for i in range(len(bounds) - 1))
            keep = sorted(i for _, i in gaps[: n_txt - 1])
            cuts = [0.0] + [bounds[i] for i in keep] + [bounds[-1]]
        else:
            cuts = bounds[: n_txt + 1]
        for i in range(min(len(cuts) - 1, n_txt)):
            pr.append((turns[i], (cuts[i], cuts[i + 1])))
        method = f"norm({n_aud}->{n_txt})"
    return dict(lesson=lesson, turns=n_txt, vad=n_aud, method=method,
                secs=len(x) / SR, audio=r["path"],
                pairs=[{"start": s, "end": e, "text": t} for t, (s, e) in pr])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=f"{ROOT}/corpus/pairs")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    allp, stats = [], []
    for lesson in range(1, 61):
        res = pairs_for(lesson)
        if res is None:
            print(f"  lesson {lesson:2d}: NO TEXT"); continue
        stats.append(res)
        for i, p in enumerate(res["pairs"]):
            allp.append(dict(lesson=lesson, idx=i, audio=res.get("audio"),
                             method=res["method"], **p))
        with open(os.path.join(a.outdir, f"lesson-{lesson:02d}.json"), "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)

    with open(f"{ROOT}/corpus/dli_pairs.tsv", "w", encoding="utf-8") as f:
        f.write("lesson\tturn\taudio\tstart\tend\tduration\tmethod\ttext\n")
        for p in allp:
            t = p["text"].replace("\t", " ")
            f.write(f"{p['lesson']}\t{p['idx']}\t{p['audio']}\t{p['start']:.2f}\t"
                    f"{p['end']:.2f}\t{p['end']-p['start']:.2f}\t{p['method']}\t{t}\n")

    good = [s for s in stats if s["method"] == "direct"]
    norm = [s for s in stats if s["method"].startswith("norm")]
    bad = [s for s in stats if s["method"] in ("no-audio", "no-text")]
    tot = sum(s["secs"] for s in stats)
    print(f"\nlessons processed : {len(stats)}/60")
    print(f"  direct pairings : {len(good)}")
    print(f"  count-normalised: {len(norm)}")
    print(f"  unusable        : {len(bad)}")
    print(f"total pairs       : {len(allp):,}")
    print(f"audio covered     : {tot/3600:.2f} h")
    if allp:
        ds = [p["end"] - p["start"] for p in allp]
        ds.sort()
        print(f"pair duration     : median {ds[len(ds)//2]:.2f}s, "
              f"p10 {ds[len(ds)//10]:.2f}s, p90 {ds[9*len(ds)//10]:.2f}s")
    print(f"\nwrote {a.outdir}/lesson-NN.json and corpus/dli_pairs.tsv")


if __name__ == "__main__":
    main()
