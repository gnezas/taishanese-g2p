# Contributing

The pronunciation problem is largely solved. **The alignment problem is not**, and that
is where contributions are most valuable. This file lists concrete, bounded tasks —
roughly in order of value per hour spent.

## 1. Verify an alignment seed set (highest value)

**The blocker.** There is no aligned audio+text training set for Taishanese, and
[experiments/README.md](experiments/README.md) shows with measurements why automatic
bootstrapping fails: Whisper cannot transcribe Taishanese, and duration-based DP
alignment cannot recover the correct pairing on its own.

**What's needed:** about an hour of a *literate* Taishanese speaker listening to short
clips and confirming whether the text matches. That seed set is enough to train a small
aligner, which aligns the rest, which you iterate — the standard low-resource bootstrap.

**Why it needs a literate speaker:** the verification task is "does this clip say this
text", which requires reading. You need to be able to *listen* — being able to read the
1962 textbook helps a lot too, since its romanization has OCR errors.

**Where to start:** lesson 9. Its merged VAD count (75 raw segments → 21 at a 2.0 s
merge threshold) **exactly equals** its 21 text turns, so the structure already lines
up and the pairs are the most trustworthy available.

```bash
# segment one lesson into utterance wavs + a timestamps TSV
python3 -m pip install numpy
python3 experiments/segment_vad.py corpus/.../toisan-v01-l09.mp3 out/ --tsv out/l09.tsv
```

Then mark each row of `out/l09.tsv` as match / no-match and open a PR with the
corrected file. Even 60 verified pairs is a real contribution.

## 2. Resolve the 13 missing characters

These have no Taishanese reading in any reachable source:

> 㥟 偓 唂 啲 抰 揼 摵 砵 縧 菎 邌 鈒 鋙

If you speak Taishanese and know any of these — or know someone who does — add the
reading to `data/hoisan_char_ipa_merged.tsv` in the same format and mark the provenance
column `manual`. Include your locality, since sub-dialects differ.

## 3. Correct the OCR

`corpus/ocr/` is machine-OCR'd from a 1962 scan and is imperfect: diacritics degrade
(`ọ`→`ö`, `kw'`→`kr'`), and numbered items are sometimes merged. If you can read the
DLI romanization, corrections to `corpus/ocr/lessons/*.txt` are useful and easy to
review.

## 4. Improve the aligner

`experiments/dp_align.py` is a correct implementation of duration-informed monotonic DP
(coverage constraint, skip state, fitted duration scale) that nonetheless is not
accurate enough. If you have a better idea — a phonetic-feature signal, a
semi-supervised approach, a better text-side parse — the harness is there.

Scoring rules, please follow them: **turns that receive no audio must count as
failures.** An earlier measurement looked far better (0.13 vs 0.58 median error) purely
because it scored only over the 70% of turns that got audio.

## 5. Add corpus

`corpus/dli_corpus.tsv` documents 16.93 h of public-domain DLI audio. Other public-domain
or permissively-licensed Taishanese recordings are welcome. **Check the licence first** —
and note that stephen-li.com carries a large aligned corpus (9,019 entries with audio)
that is currently unreachable: its Cloudflare firewall rule (error 1020) rejects every
client tried, including an independent third-party fetcher, so it is not a local
network problem. If you can reach the site owner, that corpus would be transformative.

## Practical notes

**File formats**

- `data/*.tsv` — tab-separated. Char lexicon is `char \t readings \t provenance`, where
  readings are ` / `-separated alternatives and each reading is space-separated IPA
  syllables.
- Please keep the provenance column accurate. It is the only way downstream users can
  separate cleanly-licensed rows from copyleft ones.

**Environment**

- Use Python 3.10 or newer.
- `numpy` is the only runtime dependency of `src/phonemize.py` and
  `experiments/segment_vad.py`. `ffmpeg` is required for anything touching audio.
- Two library traps are documented in
  [experiments/README.md](experiments/README.md): `faster-whisper` 1.2.1 is
  incompatible with PyAV 19, and ffmpeg emits a corrupt WAV header when piping.

**Before opening a PR**

Verify the lexicon still phonemizes cleanly and that your change did not regress
coverage:

```bash
python3 src/phonemize.py "你好" "食飯" "去街市買嘢" "一二三四五六七八九十"
# expect 0% unknown
```

**Licensing of contributions:** by contributing you agree your work may be distributed
under this repository's licence (MIT for code) and that data contributions are subject
to the upstream constraints described in [PROVENANCE.md](PROVENANCE.md). Do not
contribute data you do not have the right to redistribute.
