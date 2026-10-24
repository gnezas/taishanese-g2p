# Taishanese (Hoisan-wa / 台山話) G2P lexicon

A free **text → IPA pronunciation lexicon and phonemizer** for Taishanese, the Siyi
Yue language of Taishan, Guangdong and of the first generations of Chinese America.
Also known as Toisanese, Hoisanese, Hoisan-wa.

**12,708 characters · 8,575 words · 100% coverage of high-frequency text.**

## Why this exists

Feed Taishanese text to any TTS or ASR model on the market and you get **Cantonese**,
or gibberish. The cause is not the acoustic model — it is the **text frontend**. Every
Chinese TTS maps characters to phonemes through a Mandarin or Cantonese dictionary.
Feed it 三 and it looks up `saam1` (Cantonese), because nothing told it Taishanese
reads it `ɬam`. The model then renders Cantonese phonemes perfectly, which is exactly
the "sounds like Cantonese" complaint.

Taishanese also has sounds Cantonese cannot produce, so it is unreachable by accident:

| | | |
|---|---|---|
| pre-nasalised voiced stops | `ᵐb ⁿd ᵑɡ` | 乜 你 人 |
| voiceless lateral fricative | `ɬ` | 三 心 死 — where Cantonese has `s` |
| initial velar nasal | `ŋ` | 我 五 |
| final unreleased stops | `-p̚ -t̚ -k̚` | 十 一 六 |
| 5 lexical tones, no sandhi | `˥ ˧ ˨ ˨˩ ˧˩` | plus 4 changed tones |

**Replace the lexicon and any decent acoustic model becomes a Taishanese model.** That
is what this repository provides.

## Quickstart

```bash
git clone <this repo> && cd taishanese-g2p
python3 -m pip install numpy            # only dependency for phonemize.py

python3 src/phonemize.py "你好" "食飯"
```

```
你好            ⁿdei˧ hau˥
食飯            set̚˧˩ fan˧˩
唔該            m̩˨ kʰᵘɔi˨˩
飲茶            ᵑɡim˥ t͡sʰa˨
去街市買嘢       hui˧ kai˨˩˥ si˨˩ ᵐbai˧ jiɛ˧
一二三四五六七八九十  jit̚˥ ᵑɡei˧˩ ɬam˧ ɬei˧ m̩˥ lɵk̚˧˩ tʰit̚˥ pat̚˧ kiu˥ sip̚˧˩
```

Unknown characters are emitted as `<unk:CHAR>` rather than guessed, so gaps stay
visible instead of silently leaking a Cantonese reading.

## What's here

```
data/
  hoisan_char_ipa_merged.tsv     THE LEXICON — char / IPA readings / provenance
  hoisan_word_ipa_merged.tsv     word-level readings (captures changed tones)
  hoisan_taishan_jyutdict.tsv    verbatim 泛粵大典 readings, 台城/大江/斗山墟
src/
  taishanese_g2p.py              romanization -> IPA converter + conversion tables
  phonemize.py                   CLI: text -> IPA
  build_lexicon.py               crawl dump -> per-source lexicon
  build_lexicon_multi.py         the four-source merge + script inheritance
  add_jyutdict_layer.py          jyutdict layer + variant inheritance
  fetch_taishanese.py            resumable, rate-limit-aware Wiktionary crawler
corpus/
  dli_corpus.tsv                 128 audio files, 16.93 h, correct lesson mapping
  ocr/                           1,218-page OCR of the 1962 DLI textbook, both passes
experiments/
  README.md                      what was tried and failed — read this before repeating it
```

## Coverage

| | |
|---|---|
| Single characters | **12,708** |
| Multi-character words | **8,575** |
| Top ~600 high-frequency characters | **598/598 = 100%** |
| Characters used in 55,845 real Taishanese words | **8,298/8,311 = 99.8%** |
| Unknown rate across the whole lexicon | 5 / 32,467 = 0.015% |

**13 characters could not be resolved from any reachable source** — 㥟 偓 唂 啲 抰 揼
摵 砵 縧 菎 邌 鈒 鋙. These are Cantonese-colloquial characters and rare variants with
no Taishanese reading recorded anywhere. If you know any of them, see CONTRIBUTING.md.

## Sources

Merged in priority order; each lexicon row carries its source in the third column.

| # | Source | Contribution | Licence |
|---|---|---|---|
| 1 | **en.wiktionary** `{{zh-pron}}` `\|c-t=` (Taicheng dialect) | 2,074 chars | CC BY-SA 3.0 |
| 2 | **Stephen Li** Taishanese dictionary | 743 chars, 7,058 words | (see PROVENANCE) |
| 3 | **Gene Chin** Hoisan-English Dictionary | 7,619 chars | (see PROVENANCE) |
| 4 | **泛粵大典** (jyutdict.org) 台城/大江/斗山墟 | 12 chars | (see PROVENANCE) |
| + | **OpenCC** simp↔trad + variant maps | 2,254 chars | Apache-2.0 |

**⚠️ Read [PROVENANCE.md](PROVENANCE.md) before any commercial use.** Two of the
upstream dictionary datasets are GPL-3 / AGPL-3, and their underlying dictionaries are
third-party works marked for informational use. Research and personal use is fine; a
shipped product would need permission from the dictionary authors, or a rebuild from
Wiktionary + OpenCC only.

## The open problems

This repository solves the pronunciation problem. It does **not** solve alignment:
there is no aligned audio+text training set for Taishanese, and
[experiments/README.md](experiments/README.md) documents, with measurements, why the
obvious bootstraps fail — Whisper cannot transcribe Taishanese, and duration-based DP
alignment cannot recover the correct pairing either.

If you want to help, that is where the value is. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Reproducing the lexicon

```bash
python3 src/fetch_taishanese.py 900      # crawl Wiktionary (resumable, rate-limited)
python3 src/build_lexicon.py             # per-source lexicon
python3 src/build_lexicon_multi.py       # merge + simplified/traditional inheritance
python3 src/add_jyutdict_layer.py        # jyutdict layer + variant inheritance
```

## Licence

Code: MIT (see [LICENSE](LICENSE)). Data: see [PROVENANCE.md](PROVENANCE.md) — it is a
derived work with mixed upstream licences and is **not** covered by the MIT grant.
