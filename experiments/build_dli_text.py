#!/usr/bin/env python3
"""Turn the two OCR passes into one usable per-lesson corpus text.

The DLI scan alternates page types and NEITHER pass handles both:
  * romanization pages -> the latin pass is right, the CJK pass echoes romanization
  * character pages    -> the CJK pass is right, the latin pass is pure gibberish
    (page 21 latin: "tf ofil eff?"  vs  cjk: "好喇嗎？ 好好。你呢？")
So classify each page and keep the winning pass. Statistics over the scan:
1189 pages carry >=40 latin chars but only ~504 carry >=5 Han chars, and the latin
count is inflated by gibberish from character pages.

Usage: build_dli_text.py <latin.txt> <cjk.txt> <outdir>
"""
import os, re, sys, collections

CJK = re.compile(r"[\u3400-\u9fff]")
LAT = re.compile(r"[A-Za-z]")
# a "real word" looks like an English/DLI-romanization token, not OCR noise
WORDY = re.compile(r"\b[A-Za-z][a-z']{1,}\b")
GIBBERISH = re.compile(r"[^\w\s\u4e00-\u9fff，。？！、：；（）「」『』《》·…—　]{2,}")


def parse(path):
    d, cur, buf = {}, None, []
    for line in open(path, encoding="utf-8"):
        m = re.match(r"^=== PAGE (\d+) ===$", line.strip())
        if m:
            if cur:
                d[cur] = "\n".join(buf).strip()
            cur, buf = int(m.group(1)), []
        elif cur is not None:
            buf.append(line.rstrip("\n"))
    if cur:
        d[cur] = "\n".join(buf).strip()
    return d


def latin_quality(t):
    """Fraction of latin tokens that look like real words (vs OCR noise)."""
    toks = LAT.findall(t)
    if not toks:
        return 0.0
    words = WORDY.findall(t)
    return len(words) / max(len(toks) / 3.0, 1.0)


def classify(lat, cjk):
    han = len(CJK.findall(cjk))
    han_in_lat = len(CJK.findall(lat))
    lq = latin_quality(lat)
    # character page: CJK pass found real Han, latin pass did not do better
    if han >= 5 and han > han_in_lat:
        return "cjk", han, lq
    return "latin", han, lq


def main():
    lat_p, cjk_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    L, C = parse(lat_p), parse(cjk_p)
    os.makedirs(outdir, exist_ok=True)

    kinds = collections.Counter()
    best, lesson_of = {}, {}
    for p in sorted(set(L) | set(C)):
        lat, cjk = L.get(p, ""), C.get(p, "")
        kind, han, lq = classify(lat, cjk)
        kinds[kind] += 1
        text = cjk if kind == "cjk" else lat
        best[p] = (kind, text)
        m = re.search(r"LESSON\s+(\d+)", text, re.I) or re.search(r"LESSON\s+(\d+)", lat + "\n" + cjk, re.I)
        if m:
            lesson_of[p] = int(m.group(1))

    print("page classification:", dict(kinds))
    cjk_pages = [p for p, (k, _) in best.items() if k == "cjk"]
    print(f"character pages kept: {len(cjk_pages)}")

    # write merged text
    merged = os.path.join(outdir, "FSI-ED022176.merged.txt")
    with open(merged, "w", encoding="utf-8") as f:
        for p in sorted(best):
            kind, text = best[p]
            f.write(f"\n=== PAGE {p} [{kind}] ===\n{text}\n")
    print(f"wrote {merged}")

    # group by lesson
    byl = collections.defaultdict(list)
    for p, n in sorted(lesson_of.items()):
        byl[n].append(p)
    print(f"\nlessons detected: {len(byl)}  (numbers {min(byl) if byl else '-'}..{max(byl) if byl else '-'})")
    ldir = os.path.join(outdir, "lessons")
    os.makedirs(ldir, exist_ok=True)
    total_cjk = 0
    for n in sorted(byl):
        pages = byl[n]
        chunks = []
        for p in pages:
            kind, text = best[p]
            if kind == "cjk":
                chunks.append(text)
                total_cjk += len(text)
        body = "\n".join(chunks)
        with open(os.path.join(ldir, f"lesson-{n:02d}.txt"), "w", encoding="utf-8") as f:
            f.write(body)
    print(f"wrote {len(byl)} lesson files to {ldir}")
    print(f"total character-page text: {total_cjk} chars")

    # quick sanity: does the character text phonemize with our lexicon?
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
    import phonemize as P
    sample = ""
    for f in sorted(os.listdir(ldir))[:6]:
        sample += open(os.path.join(ldir, f), encoding="utf-8").read()
    chars = [c for c in sample if CJK.match(c)]
    known = [c for c in chars if c in P.CHARS]
    print(f"\nlexicon check on {len(chars)} OCR'd Han chars: {len(known)} known "
          f"({100*len(known)/max(len(chars),1):.1f}%)")
    unk = collections.Counter(c for c in chars if c not in P.CHARS)
    print("top unknown:", "".join(c for c, _ in unk.most_common(30)))


if __name__ == "__main__":
    main()
