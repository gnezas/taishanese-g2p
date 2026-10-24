#!/usr/bin/env python3
"""Build a Taishanese char/word -> IPA lexicon from the fetched |c-t= dump,
then phonemize real text and measure coverage against high-frequency chars.

Format facts (verified against the dump):
  你 -> "nei1,nei4"          comma  = SEPARATE READINGS (variants)
  台山話 -> "hoi3 saan1 va5"  space  = SYLLABLES within one word
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from taishanese_g2p import syllable_to_ipa

SCR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = f"{SCR}/taishanese_ct.tsv"
OUTCHAR = f"{SCR}/hoisan_char_ipa.tsv"
OUTWORD = f"{SCR}/hoisan_word_ipa.tsv"

REF_RE = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>|<!--.*?-->", re.S)
CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\U00020000-\U0002ffff]")

# top ~200 high-frequency Chinese characters (standard frequency list order)
FREQ = ("的一是不了在人有我他这个们中来上大为和国地到以说时要就出会可也你对生能而子那得于着下自之年过发后作里用道行所然家种事成方多经么去法学如都同现当没动面起看定天分还进好小部其些主样理心她本前开但因只从想实日军者意无力它与长把机十民第公此已工使情明性知全三又关点正业外将两高间由问很最重并物手应战向头文体政美相见被利什二等产或新己制身果加西斯月话合回特代内信表化老给世位次度门任常先海通教儿原东声提立及比员解水名真论处走义各入几口认条平系气题活尔更别打女变四神总何电数安少报才结反受目太量再感建务做接必场件计管期市直德资命山金指克许统区保至队形社便空决治展马科司五基眼书非则听白却界达光放强即像难且权思王象完设式色路记南品住告类求据程北边死张该交规万取拉格望觉术领共确传师观清今切院让识候带导争运笑飞风步改收根干造言联持组每济车亲极林服快办议往元英士证近失转夫令准布始怎呢存未远叫台单影具罗字爱击流备兵连调深商算质团集百需价花党华城石级整府离况亚请技际约示复病息究线似官火断精满支视消越器容照须九增研写称企八功吗包片史委乎查轻易早曾除农找装广显吧阿李标谈吃图念六引历首医局突专费号尽另周较注语仅考落青随选列武红响虽推势参希古众构房半节土投某案黑维革划敌致陈律足态护七兴派孩验责营星够章音跟志底站严巴例防族供效续施留讲型料终答紧黄绝奇察母京段依批群项故按河米围江织害斗双境客纪采举杀攻父苏密低朝友诉止细镇导落")
FREQ = "".join(dict.fromkeys(FREQ))   # dedupe, keep order


def clean(v):
    return REF_RE.sub("", v).strip().strip(".").strip()


def phonemize_value(v):
    """value -> (list of readings, errors). A reading is a list of IPA syllables."""
    readings, errs = [], []
    for variant in re.split(r"[,，、;；]", clean(v)):
        syls = []
        for tok in variant.split():
            ipa, e = syllable_to_ipa(tok)
            if e:
                errs.append(e)
            else:
                syls.append(ipa)
        if syls:
            readings.append(syls)
    return readings, errs


def main():
    chars, words = {}, {}
    all_errs, n_vals = {}, 0
    for line in open(TSV, encoding="utf-8"):
        if "\t" not in line:
            continue
        title, vals = line.rstrip("\n").split("\t", 1)
        readings = []
        for v in vals.split("|"):
            n_vals += 1
            r, errs = phonemize_value(v)
            readings += r
            for e in errs:
                all_errs[e] = all_errs.get(e, 0) + 1
        if not readings:
            continue
        is_char = len(title) == 1 and CJK.match(title)
        (chars if is_char else words)[title] = readings

    with open(OUTCHAR, "w", encoding="utf-8") as f:
        for c in sorted(chars):
            f.write(c + "\t" + " / ".join(" ".join(r) for r in chars[c]) + "\n")
    with open(OUTWORD, "w", encoding="utf-8") as f:
        for w in sorted(words):
            f.write(w + "\t" + " / ".join(" ".join(r) for r in words[w]) + "\n")

    print(f"c-t values parsed : {n_vals}")
    print(f"single characters : {len(chars)}   (with IPA, some multi-reading)")
    print(f"multi-char words  : {len(words)}")
    print(f"parse errors      : {sum(all_errs.values())}")
    for e, n in sorted(all_errs.items(), key=lambda kv: -kv[1])[:8]:
        print(f"   x{n:4d}  {e}")

    print("\n=== phonemization demo (first reading of each char) ===")
    for s in ["你好", "我係台山人", "食飯", "多謝", "唔該",
              "一二三四五六七八九十", "三", "你係邊個", "飲茶", "台山話"]:
        parts, miss = [], 0
        for ch in s:
            if ch in chars:
                parts.append(" ".join(chars[ch][0]))
            else:
                parts.append(f"[?{ch}]")
                miss += 1
        print(f"  {s:12s} {len(s)-miss}/{len(s)}  {' | '.join(parts)}")

    hit = sum(1 for c in FREQ if c in chars)
    print(f"\n=== coverage vs top-{len(FREQ)} high-frequency characters ===")
    print(f"  {hit}/{len(FREQ)} = {100*hit/len(FREQ):.1f}% of everyday running text covered")
    missing = "".join(c for c in FREQ if c not in chars)
    print(f"  missing ({len(missing)}): {missing}")


if __name__ == "__main__":
    main()
