#!/usr/bin/env python3
"""Taishanese text -> IPA phoneme string, using the merged lexicon.

Usage:
    python3.13 phonemize.py 你好世界
    python3.13 phonemize.py --file sentences.txt
    echo "食飯" | python3.13 phonemize.py -

Reads hoisan_char_ipa_merged.tsv (char / IPA readings / provenance).
Unknown characters emit <unk:CHAR> so gaps stay visible instead of being
silently approximated by a Cantonese reading.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve(name):
    """Locate a lexicon file.

    Supports both the repo layout (script in src/, data in ../data/) and a flat
    layout with everything in one directory, so the documented quickstart
    (`python3 src/phonemize.py ...`) works from a fresh clone.
    """
    for cand in (os.path.join(HERE, name),
                 os.path.join(HERE, os.pardir, "data", name),
                 os.path.join(HERE, os.pardir, name)):
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return os.path.join(HERE, name)


CHAR_TSV = _resolve("hoisan_char_ipa_merged.tsv")
WORD_TSV = _resolve("hoisan_word_ipa_merged.tsv")
MAX_WORD_LEN = 8


def load(path):
    """-> {key: ([reading, ...], provenance)}"""
    d = {}
    if not os.path.exists(path):
        return d
    with open(path, encoding="utf-8") as f:
        for line in f:
            if "\t" not in line:
                continue
            parts = line.rstrip("\n").split("\t")
            k, v = parts[0], parts[1]
            prov = parts[2] if len(parts) > 2 else ""
            d[k] = ([r.split() for r in v.split(" / ")], prov)
    return d


CHARS = load(CHAR_TSV)
WORDS = load(WORD_TSV)
for k in WORDS:
    MAX_WORD_LEN = max(MAX_WORD_LEN, len(k))


PUNCT = set("，。！？、；：（）《》〈〉「」『』【】〔〕…—～・·")


def phonemize(text, provenance=False):
    out, i, unk, provs = [], 0, 0, []
    while i < len(text):
        hit = None
        for L in range(min(MAX_WORD_LEN, len(text) - i), 1, -1):
            if text[i:i + L] in WORDS:
                hit = (text[i:i + L], WORDS[text[i:i + L]][0])
                break
        if hit:
            out.append(" ".join(hit[1][0]))
            provs.append("word")
            i += len(hit[0])
            continue
        ch = text[i]
        if ch in CHARS:
            out.append(" ".join(CHARS[ch][0][0]))
            provs.append(CHARS[ch][1])
        elif ch.isspace() or ch in PUNCT:
            out.append("|")
        elif ch.isascii() and (ch.isalnum() or ch in ".,!?;:"):
            out.append(ch)
        else:
            out.append(f"<unk:{ch}>")
            unk += 1
        i += 1
    ipa = " ".join(x for x in out if x)
    return (ipa, provs) if provenance else (ipa, unk)


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--no-words":
        # character-by-character only: avoids multi-char word entries from
        # lower-priority sources (notably Stephen Li's /ei/->/i/ merge) winning
        # over the cleaner per-character Taicheng readings.
        WORDS.clear()
        args = args[1:]
    if args and args[0] == "--file":
        lines = [l.rstrip("\n") for l in open(args[1], encoding="utf-8")]
    elif args and args[0] == "-":
        lines = [l.rstrip("\n") for l in sys.stdin]
    elif args:
        lines = [" ".join(args)]
    else:
        print(__doc__)
        sys.exit(0)

    print(f"lexicon: {len(CHARS)} chars, {len(WORDS)} words "
          f"({os.path.basename(CHAR_TSV)})\n")
    total_unk = total_ch = 0
    for ln in lines:
        if not ln.strip():
            continue
        ipa, unk = phonemize(ln)
        total_unk += unk
        total_ch += len(ln)
        print(f"{ln}\n  {ipa}\n")
    if total_ch:
        print(f"unknown-character rate: {total_unk}/{total_ch} = "
              f"{100*total_unk/total_ch:.1f}%")
