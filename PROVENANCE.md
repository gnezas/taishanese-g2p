# Provenance and licensing

**The merged lexicon in `data/` is a derived work with mixed upstream licences. It is
NOT covered by this repository's MIT grant.** Read this before any use beyond research
and personal projects.

## Where each row came from

Every row of `data/hoisan_char_ipa_merged.tsv` carries its source in the third column.
Exact counts, verified against the shipped file (they sum to 12,708):

| Source | Chars | Upstream terms |
|---|---|---|
| **Gene Chin** Hoisan-English Dictionary (via `pearapple123/rime-hoisanva`) | 7,619 | GPL-3.0 repo; underlying dictionary © Gene M. Chin, "informational purposes only" |
| **Script inheritance** — OpenCC simplified↔traditional | 2,254 | Apache-2.0 |
| **en.wiktionary** `{{zh-pron}}` `\|c-t=` | 2,074 | CC BY-SA 3.0 |
| **Stephen Li** Taishanese dictionary (via `suspiciouscactus/stephen-dictionary-data`) | 743 | AGPL-3.0 repo; underlying dictionary by Stephen Li |
| **泛粵大典 / jyutdict.org** (台城/大江/斗山墟) | 12 | see below |
| **Variant inheritance** — OpenCC variant maps + manual | 6 | Apache-2.0 / manual |

Plus `data/hoisan_word_ipa_merged.tsv` (8,575 words, overwhelmingly Stephen Li) and
`data/hoisan_taishan_jyutdict.tsv` (26 verbatim readings kept separate for auditing).

`corpus/` is a different situation and is **clean**: the DLI "Chinese-Cantonese
(Toishan) Basic Course" is US-government public domain. A DLI contact confirmed this,
with the single condition that nobody sells it or claims authorship. The OCR text in
`corpus/ocr/` is therefore public domain.

## What this means in practice

- **Research, study, personal projects, contributing here: fine.**
- **Shipped commercial product: not fine as-is.** Two upstream datasets are
  **copyleft** (GPL-3.0 and AGPL-3.0), and those licences propagate to derivatives.
  The underlying dictionaries are also third-party works whose own pages state they
  are for informational use. Publishing this data does not grant you rights the
  upstream authors never gave.
- **To go commercial, do one of:**
  1. obtain permission from Gene M. Chin and Stephen Li, or
  2. **rebuild from the clean sources only** — Wiktionary `|c-t=` (CC BY-SA) plus
     OpenCC (Apache-2.0). That path still gives full high-frequency coverage; you
     lose only the long tail. `src/build_lexicon_multi.py` takes the sources as a
     list, so simply omit the Gene Chin and Stephen Li loaders.

## 泛粵大典 / jyutdict.org

Used only for 12 characters the other sources lacked, plus a handful of control
characters used to settle a transcription question. Their documentation states that
some contributed data is not released with full permission from its authors, so treat
it as **all rights reserved by its contributors** and do not redistribute it widely
without asking them. They are reachable via the contact details on jyutdict.org and
explicitly invite corrections and contributions.

**Their docs also ask, in plain terms, that nobody crawl the site** (「服務器細水管
低配置・請勿 ddos・不要爬蟲」 — thin server, don't flood it, no crawlers). Their public
API is at `/api/v1.0/`, and it **403s if you append `.php`** — use the extensionless
path. Please respect the request and query per-character only.

## Transcription conventions differ between sources

This is a real hazard when merging, and it is why each row is tagged.

泛粵大典 writes the historical voiced series as **plain nasals** — 你 = `nei33`,
人 = `ŋin22`. Wiktionary's guidelines and Gene Chin write the same contrast as
**pre-nasalised stops** — `ⁿd` / `ᵑɡ` / `ᵐb`. Same phonemes, different notation. The
main lexicon keeps the `ⁿd`/`ᵑɡ`/`ᵐb` convention for internal consistency; the verbatim
泛粵大典 readings live separately in `data/hoisan_taishan_jyutdict.tsv`. **If you train
a model, pick one convention deliberately** rather than inheriting the mix.

## Sub-dialect mixing

Wiktionary is Taicheng. Gene Chin and Stephen Li cover their own localities. 泛粵大典
gives 台城, 大江 and 斗山墟. For a single-voice model, filter the lexicon to one source
using the provenance column.
