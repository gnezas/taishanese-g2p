#!/usr/bin/env python3
"""Add the 泛粵大典 (jyutdict.org) Taishan layer + variant inheritance to the lexicon.

Two additions:
  1. jyutdict Taishan readings (台城 / 大江 / 斗山墟), native-speaker IPA with tone
     contours, for characters the other three sources lacked.
  2. Variant -> canonical inheritance for a handful of variant characters
     (伱 -> 你, 隂 -> 陰, 斎 -> 齋, 譭 -> 毁, 艹 -> 艸, 忄 -> 心).

NOTE on transcription convention: jyutdict writes the historical voiced series as
plain nasals (n / ŋ / m: 你 = nei33, 人 = ŋin22). Wiktionary's guideline and Gene
Chin write them as prenasalised stops (ⁿd / ᵑɡ / ᵐb). Same phonemic contrast,
different notation. The main lexicon keeps the ⁿd/ᵑɡ/ᵐb convention for internal
consistency; the verbatim jyutdict readings are preserved separately.
"""
import json, os, re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "sources")
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")

# --- characters resolved from jyutdict detail api (verbatim IPA per locality) ---
# id 8 = 台山大江, 9 = 台山斗山墟, 70 = 台山台城
JYUT = {
    "彝": {"70": ["ji22"]},
    "踊": {"70": ["jəɯŋ55"]},
    "諡": {"70": ["si33"]},
    "堯": {"8": ["ŋiɐu22"], "9": ["ŋiu22"], "70": ["ŋieu22"]},
    "埞": {"8": ["ʔiɐŋ32"]},
    "躝": {"8": ["lɔn55"]},
    "瀰": {"8": ["mei22"], "9": ["mi22"]},
    "睩": {"8": ["lək55"]},
    "嗗": {"8": ["kuɔt11"]},
    "岙": {"70": ["ʔɑu33"]},
    "茌": {"70": ["ʦʰi22"]},
    "髧": {"8": ["ʔəm33"]},
    # control characters used to settle the /ei/ vs /i/ question (see README)
    "二": {"70": ["ŋei32", "ŋei215"]},
    "四": {"70": ["ɬei33"]},
    "五": {"70": ["m̩55"]},
    "十": {"70": ["sip32"]},
    "三": {"70": ["ɬam33", "ɬam215"]},
    "你": {"70": ["nei33", "nei21"]},
    "人": {"70": ["ŋin22"]},
    "死": {"70": ["ɬei55"]},
    "心": {"70": ["ɬim33", "ɬim21"]},
    "街": {"70": ["kai21"]},
    "食": {"70": ["set32", "tu32"]},
    "哪": {"70": ["na22", "na32", "nai21"]},
}

# --- variant -> canonical, for characters with no reading of their own ---
VARIANTS = {"伱": "你", "隂": "陰", "斎": "齋", "譭": "毁", "艹": "艸", "忄": "心"}


def load_lex(path):
    d = {}
    for line in open(path, encoding="utf-8"):
        if "\t" not in line:
            continue
        parts = line.rstrip("\n").split("\t")
        d[parts[0]] = (parts[1], parts[2] if len(parts) > 2 else "")
    return d


def main():
    lex_path = os.path.join(HERE, "hoisan_char_ipa_merged.tsv")
    lex = load_lex(lex_path)
    before = len(lex)

    # 1. variant inheritance (transitive, bounded)
    var_added = {}
    for v, canon in VARIANTS.items():
        if v in lex or canon not in lex:
            continue
        lex[v] = (lex[canon][0], f"variant<{canon}")
        var_added[v] = canon

    # 2. jyutdict layer
    jyut_added = {}
    for ch, places in JYUT.items():
        if ch in lex:
            continue
        # prefer 台城 (70), then 大江 (8), then 斗山 (9)
        for pid in ("70", "8", "9"):
            if pid in places:
                lex[ch] = (" / ".join(places[pid]), f"jyutdict:{pid}")
                jyut_added[ch] = pid
                break

    with open(lex_path, "w", encoding="utf-8") as f:
        for k in sorted(lex):
            f.write(f"{k}\t{lex[k][0]}\t{lex[k][1]}\n")

    # verbatim jyutdict record, kept separate for auditing
    with open(os.path.join(HERE, "hoisan_taishan_jyutdict.tsv"), "w", encoding="utf-8") as f:
        f.write("# 泛粵大典 (jyutdict.org) Taishan readings, VERBATIM IPA\n")
        f.write("# locality ids: 8=台山大江 9=台山斗山墟 70=台山台城\n")
        f.write("char\tlocality\tIPA(J++ reading)\n")
        for ch, places in sorted(JYUT.items()):
            for pid, ipas in places.items():
                f.write(f"{ch}\t{pid}\t{' / '.join(ipas)}\n")

    print(f"lexicon: {before} -> {len(lex)} chars")
    print(f"  variant-inherited: {len(var_added)}  {var_added}")
    print(f"  jyutdict-native:   {len(jyut_added)}  {jyut_added}")

    # report remaining gaps against the rime word list
    wordchars = set()
    for line in open(os.path.join(SRC, "hoisanva.words.dict.yaml"), encoding="utf-8"):
        if not line.strip() or line[0] in "#- \t" or ":" in line:
            continue
        for c in line.strip():
            if CJK.match(c):
                wordchars.add(c)
    missing = sorted(wordchars - set(lex))
    print(f"\nstill missing from real-Taishanese-word vocabulary: {len(missing)}")
    print(f"  {''.join(missing)}")


if __name__ == "__main__":
    main()
