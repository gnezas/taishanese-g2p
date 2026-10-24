#!/usr/bin/env python3
"""Merge three Taishanese pronunciation sources into one char/word -> IPA lexicon.

Priority (highest first):
  1. en.wiktionary  |c-t=  (Taicheng, unambiguous, already IPA)   ~900+ chars
  2. Stephen Li dictionary data (already IPA + tone contours)      ~9000 entries
  3. Gene Chin HED via rime-hoisanva (romanization -> IPA)        ~12000 chars

Sources are GPL-3 / AGPL-3; the underlying dictionaries are third-party works.
Fine for research/personal use; a licensing problem for a shipped product.
"""
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "sources")
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]")

# ---------------------------------------------------------------- tone helper
_CHAO = {"1": "˩", "2": "˨", "3": "˧", "4": "˦", "5": "˥"}


def tone_letters(digits):
    """'335' -> '˧˥'. Collapses consecutive equal levels (55->˥, 33->˧)."""
    s = "".join(_CHAO[c] for c in digits if c in _CHAO)
    out = []
    for c in s:
        if not out or out[-1] != c:
            out.append(c)
    return "".join(out)


# ------------------------------------------------------------- source 1: wiktionary
def load_wiktionary():
    chars, words = {}, {}
    p = os.path.join(HERE, "hoisan_char_ipa.tsv")
    w = os.path.join(HERE, "hoisan_word_ipa.tsv")
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            if "\t" in line:
                k, v = line.rstrip("\n").split("\t", 1)
                chars[k] = [rd.split() for rd in v.split(" / ")]
    if os.path.exists(w):
        for line in open(w, encoding="utf-8"):
            if "\t" in line:
                k, v = line.rstrip("\n").split("\t", 1)
                words[k] = [rd.split() for rd in v.split(" / ")]
    return chars, words


# ------------------------------------------------------------ source 2: Stephen Li
SL_INIT = {"dz": "t͡s", "ts": "t͡sʰ", "ɬ": "ɬ", "b": "p", "p": "pʰ", "m": "ᵐb",
           "f": "f", "v": "v", "d": "t", "t": "tʰ", "n": "ⁿd", "l": "l",
           "g": "k", "k": "kʰ", "ŋ": "ᵑɡ", "y": "j", "s": "s", "h": "h"}
SL_RHYME = {
    "ai": "ai", "ɔu": "au", "au": "au", "am": "am", "an": "an", "aŋ": "aŋ",
    "ap": "ap̚", "at": "at̚", "ak": "ak̚",
    "iu": "iu", "im": "im", "in": "in", "ip": "ip̚", "it": "it̚",
    "ia": "iɛ", "iau": "iau", "iam": "iam", "iaŋ": "iaŋ", "iap": "iap̚", "iak": "iak̚",
    "ian": "iɛn", "iat": "iɛt̚",
    "ui": "ui", "un": "un", "ut": "ut̚",
    "ǝu": "eu", "əu": "eu", "ǝm": "em", "əm": "em", "ein": "en",
    "ǝp": "ep̚", "əp": "ep̚", "ɛt": "et̚", "et": "et̚",
    "ǝŋ": "ɵŋ", "əŋ": "ɵŋ", "ǝk": "ɵk̚", "ək": "ɵk̚",
    "eiŋ": "eŋ",
    "ɔ": "ᵘɔ", "uɔ": "ᵘɔ", "ɔi": "ᵘɔi", "oi": "ᵘɔi", "ɔn": "ᵘɔn", "uɔn": "ᵘɔn",
    "on": "ᵘɔn", "ɔŋ": "ɔŋ", "ong": "ɔŋ", "ɔt": "ᵘɔt̚", "ot": "ᵘɔt̚",
    "ɔk": "ɔk̚", "ok": "ɔk̚",
    "ə": "ə", "e": "ə", "ei": "ei", "m": "m̩",
    "a": "a", "i": "i", "u": "u",
}
SL_INIT_KEYS = sorted(SL_INIT, key=len, reverse=True)
SL_RHYME_KEYS = sorted(SL_RHYME, key=len, reverse=True)
TONE_RE = re.compile(r"(\d+)\s*$")


def sl_syllable(syl):
    """'mein32' -> 'meiⁿ? ...'  returns IPA or None."""
    m = TONE_RE.search(syl)
    if not m:
        return None
    body, tone = TONE_RE.sub("", syl), m.group(1)
    # A bare "m"/"ng" is a SYLLABIC NASAL (五, 唔), not the ᵐb/ᵑɡ initial.
    if body in ("m", "ng"):
        return ("m̩" if body == "m" else "ŋ̩") + tone_letters(tone)
    ini = ""
    for k in SL_INIT_KEYS:
        if body.startswith(k):
            ini, body = SL_INIT[k], body[len(k):]
            break
    if body == "":
        rhy = ""
    elif body in SL_RHYME:
        rhy = SL_RHYME[body]
    elif body == "i":                       # /i/ vs /ei/ merge (documented)
        rhy = "i"
    elif body == "ut":
        rhy = "ut̚"
    elif body == "einn":
        rhy = "en"
    elif body == "ii":
        rhy = "i"
    else:
        return None
    return ini + rhy + tone_letters(tone)


def load_stephen():
    chars, words = {}, {}
    p = os.path.join(SRC, "stephen_data.json")
    if not os.path.exists(p):
        return chars, words
    data = json.load(open(p, encoding="utf-8"))
    INNER = re.compile(r"\[([^\]]*)\]")
    for e in data:
        surf = (e.get("taishanese") or "").strip()
        m = INNER.search(e.get("taishaneseRomanization") or "")
        if not surf or not m:
            continue
        body = INNER.search(e["taishaneseRomanization"]).group(1)
        body = re.sub(r"\([^)]*\)", "", body)          # drop variant tones
        if any(c in body for c in "?.}{"):
            continue
        readings = []
        for variant in body.split("/"):
            ipa = [sl_syllable(s) for s in variant.split()]
            if ipa and all(ipa):
                readings.append(ipa)
        if not readings:
            continue
        if len(surf) == 1 and CJK.match(surf):
            chars.setdefault(surf, []).extend(readings)
        else:
            words.setdefault(surf, []).extend(readings)
    return chars, words


# ------------------------------------------------------------ source 3: Gene Chin
GC_INIT = {"ch": "t͡sʰ", "ng": "ᵑɡ", "b": "p", "p": "pʰ", "m": "ᵐb", "f": "f",
           "v": "v", "d": "t", "t": "tʰ", "n": "ⁿd", "l": "l", "x": "ɬ",
           "g": "k", "k": "kʰ", "j": "t͡s", "y": "j", "s": "s", "h": "h"}
GC_RHYME = {
    "ai": "ai", "ao": "au", "am": "am", "an": "an", "ang": "aŋ",
    "ap": "ap̚", "at": "at̚", "ak": "ak̚",
    "iu": "iu", "im": "im", "in": "in", "ip": "ip̚", "it": "it̚",
    "eh": "iɛ", "el": "iau", "em": "iam", "eng": "iaŋ", "ep": "iap̚", "ek": "iak̚",
    "ui": "ui", "un": "un", "ut": "ut̚", "ung": "ɵŋ", "uk": "ɵk̚",
    "o": "ᵘɔ", "oi": "ᵘɔi", "on": "ᵘɔn", "ong": "ɔŋ", "ot": "ᵘɔt̚", "ok": "ɔk̚",
    "eo": "eu", "eim": "em", "en": "en", "ein": "en", "eip": "ep̚",
    "eik": "et̚", "et": "et̚",
    "a": "a", "i": "i", "u": "u", "e": "ə", "m": "m̩",
}
GC_INIT_KEYS = sorted(GC_INIT, key=len, reverse=True)


def gc_syllable(syl):
    m = TONE_RE.search(syl)
    if not m:
        return None
    body, tone = TONE_RE.sub("", syl), m.group(1)
    # A bare "m"/"ng" is a SYLLABIC NASAL (五, 唔), not the ᵐb/ᵑɡ initial.
    if body in ("m", "ng"):
        return ("m̩" if body == "m" else "ŋ̩") + tone_letters(tone)
    ini = ""
    for k in GC_INIT_KEYS:
        if body.startswith(k):
            ini, body = GC_INIT[k], body[len(k):]
            break
    if body == "":
        rhy = ""
    elif body in GC_RHYME:
        rhy = GC_RHYME[body]
    else:
        return None
    return ini + rhy + tone_letters(tone)


def load_genechin():
    chars, words = {}, {}
    p = os.path.join(SRC, "hoisanva.dict.yaml")
    if not os.path.exists(p):
        return chars, words
    for line in open(p, encoding="utf-8"):
        if not line.strip() or line[0] in "#- \t":
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2 or not parts[1].strip():
            continue
        surf, reading = parts[0], parts[1].strip()
        ipa = [gc_syllable(s) for s in reading.split()]
        if not ipa or not all(ipa):
            continue
        if len(surf) == 1 and CJK.match(surf):
            chars.setdefault(surf, []).append(ipa)
        else:
            words.setdefault(surf, []).append(ipa)
    return chars, words


# --------------------------------------------------- script inheritance (simp<->trad)
def load_st_map():
    """OpenCC STCharacters.txt (Apache-2.0): simplified -> traditional forms."""
    st, ts = {}, {}
    p = os.path.join(SRC, "STCharacters.txt")
    if not os.path.exists(p):
        return st, ts
    for line in open(p, encoding="utf-8"):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        simp, trads = parts[0], parts[1].split()
        if len(simp) == 1:
            st[simp] = trads
            for t in trads:
                if len(t) == 1:
                    ts.setdefault(t, []).append(simp)
    return st, ts


def inherit_script(merged, st, ts, is_char):
    """Fill missing simplified (or traditional) forms from the other script.

    Dialect dictionaries are traditional-script; users type simplified. One step
    of script conversion recovers a large block of otherwise-missing characters.
    Marked separately so the borrowing is auditable.
    """
    added = {}
    universe = (set(st) | set(ts)) if is_char else set()
    for c in universe:
        if c in merged:
            continue
        for a in list(st.get(c, [])) + list(ts.get(c, [])):
            if a in merged:
                merged[c] = merged[a]
                added[c] = a
                break
    return added


# ------------------------------------------------------------------------ merge
def dedupe(readings):
    seen, out = set(), []
    for r in readings:
        k = " ".join(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def main():
    wc, ww = load_wiktionary()
    sc, sw = load_stephen()
    gc, gw = load_genechin()
    print(f"wiktionary : {len(wc):6d} chars  {len(ww):6d} words")
    print(f"stephen li : {len(sc):6d} chars  {len(sw):6d} words")
    print(f"gene chin  : {len(gc):6d} chars  {len(gw):6d} words")

    merged_c, merged_w = {}, {}
    prov = {}
    for name, src_c, src_w in (("wiktionary", wc, ww), ("stephenli", sc, sw),
                               ("genechin", gc, gw)):
        for k, v in src_c.items():
            if k not in merged_c:
                merged_c[k] = dedupe(v)
                prov[k] = name
        for k, v in src_w.items():
            if k not in merged_w:
                merged_w[k] = dedupe(v)

    st, ts = load_st_map()
    inh_c = inherit_script(merged_c, st, ts, True)
    for k, v in inh_c.items():
        prov[k] = f"script<{v}"
    print(f"\nMERGED     : {len(merged_c):6d} chars  {len(merged_w):6d} words")
    print(f"  of which inherited via simplified<->traditional: {len(inh_c)}")

    # write
    with open(os.path.join(HERE, "hoisan_char_ipa_merged.tsv"), "w", encoding="utf-8") as f:
        for k in sorted(merged_c):
            f.write(k + "\t" + " / ".join(" ".join(r) for r in merged_c[k])
                    + "\t" + prov[k] + "\n")
    with open(os.path.join(HERE, "hoisan_word_ipa_merged.tsv"), "w", encoding="utf-8") as f:
        for k in sorted(merged_w):
            f.write(k + "\t" + " / ".join(" ".join(r) for r in merged_w[k]) + "\n")

    # coverage against high-frequency characters
    sys.path.insert(0, HERE)
    import importlib
    bl = importlib.import_module("build_lexicon")
    FREQ = bl.FREQ
    hit = sum(1 for c in FREQ if c in merged_c)
    print(f"\ncoverage vs top-{len(FREQ)} high-frequency chars: "
          f"{hit}/{len(FREQ)} = {100*hit/len(FREQ):.1f}%")
    miss = "".join(c for c in FREQ if c not in merged_c)
    print(f"still missing ({len(miss)}): {miss}")

    pc = collections.Counter(prov.values())
    agg = collections.Counter()
    for k, v in prov.items():
        agg["script-inherited" if v.startswith("script<") else v] += 1
    print("\nprovenance of merged chars:", dict(agg))
    print("\nspot checks:")
    for c in "三你人我食飯飲茶心死五一二三四五六七八九十":
        if c in merged_c:
            print(f"  {c}  {' / '.join(' '.join(r) for r in merged_c[c])}   [{prov[c]}]")
        else:
            print(f"  {c}  <MISSING>")


if __name__ == "__main__":
    main()
