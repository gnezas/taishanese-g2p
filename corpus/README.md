# Corpus: DLI Chinese-Cantonese (Toishan) Basic Course

US Army Language School / Defense Language Institute, Presidio of Monterey, **1962**.

**Licence: US-government public domain.** A DLI contact confirmed the Toishan material
is public domain, with one condition — nobody sells it or claims authorship. This is the
cleanest-licensed asset in the repository; unlike `data/`, there is no copyleft issue.

## What's here

| | |
|---|---|
| Audio | **128 mp3 files, 16.93 hours** |
| Volumes | 6 lesson volumes + volume-1 drills |
| Text | 1,218-page scanned textbook, OCR'd here (both passes) |

`dli_corpus.tsv` — one row per audio file: `path`, `duration_s`, `volume`, `kind`, `lesson`.

```
corpus/ocr/FSI-ED022176.latin.txt     OCR pass 1: Latin romanization
corpus/ocr/FSI-ED022176.cjk.txt       OCR pass 2: Chinese characters
corpus/ocr/lessons/lesson-NN.txt      per-lesson text, best pass auto-selected
```

## Getting the audio

The audio is not committed here (it is ~1.2 GB and re-downloadable). Two sources:

```bash
# per-lesson files, easiest to work with (68 files, ~600 MB)
#   github.com/aaronjlee/toishan-basic-course  (GPL-3 repo, public-domain content)
# volume zips (6 volumes + drills, ~1.2 GB)
BASE=https://pneumatised.com/wp-content/uploads/2025/09
for v in volume_1_drills volume_1_lessons_pt1 volume_1_lessons_pt2 \
         volume_2_lessons_pt1 volume_2_lessons_pt2 \
         volume_3_lessons_pt1 volume_3_lessons_pt2 \
         volume_4_lessons_pt1 volume_4_lessons_pt2 \
         volume_5_lessons_pt1 volume_5_lessons_pt2 \
         volume_6_lessons_pt1 volume_6_lessons_pt2; do
  curl -L -C - -o "$v.zip" "$BASE/$v.zip"
done
```

The scanned PDF (`FSI-ED022176.pdf`, 26 MB) comes from the same GitHub repo — not
committed, to keep the repository light.

## Lesson ↔ audio mapping

**The `lNN` in the filename is the GLOBAL lesson number, not per-volume.**
`toisan-v02-l21` is lesson 21. Volumes 1–3 cover lessons 1–20 / 21–40 / 41–60.
**Volumes 4–6 restart at `l01`** — a separate edition; include them and every lesson
matches twice. Two files cover two lessons each (`l02-03`, `l06-and-07`).

## How the OCR was produced

The PDF is a **pure scan — 1,218 pages, zero text layer**. It was OCR'd with a
native on-device OCR framework — no GPU required, and it beat tesseract
substantially on this material.

**Each page needs two passes.** The course alternates romanization and character pages,
and one recognizer cannot read both: `en-US` turns CJK into gibberish (`tf ofil eff?`)
while `zh-Hans` misreads romanization. `build_dli_text.py` classifies each page and
keeps the winning pass (714 latin pages, 504 character pages).

**The OCR agrees with the pronunciation lexicon on 99.8% of Han characters**
(6,890 / 6,901) — two fully independent sources. Corrections are welcome; the
romanization's diacritics degrade (`ọ`→`ö`, `kw'`→`kr'`) and numbered items are
sometimes merged across page breaks.

## Coverage by volume

| Volume | Files | Duration |
|---|---|---|
| Vol 1 Drills | 10 | 36.1 min |
| Vol 1 Lessons | 18 | 116.3 min |
| Vol 2 Lessons | 20 | 165.2 min |
| Vol 3 Lessons | 20 | 188.4 min |
| Vol 4 Lessons | 20 | 160.6 min |
| Vol 5 Lessons | 20 | 183.4 min |
| Vol 6 Lessons | 20 | 165.9 min |

17 hours is enough for both targets: Whisper LoRA fine-tunes well on 10–20 h, and a
VITS/FastSpeech2 TTS wants 5–20 h. **What is missing is alignment, not compute or
audio** — see [../experiments/README.md](../experiments/README.md) and
[../CONTRIBUTING.md](../CONTRIBUTING.md).

## Note on the romanization

The course teaches the **DLI romanization** (`p p' m f t t' n lh l ch ch' s y k k'
ng h kw kw' w`) and only introduces Chinese characters from lesson 4, so this is a
phoneme-level corpus rather than a character-level one. The DLI scheme is one of the
four compared on
`Wiktionary:Chinese entry guidelines/Cantonese/Taishanese`, which is the mapping to use
if you need DLI text in IPA.
