# Experiments — including three negative results

These are correct implementations of approaches that **did not work**, kept so nobody
repeats them. Each claim below is backed by a measurement from this corpus, not an
assumption. If you are about to try one of these, read the number first.

---

## 1. Whisper cannot transcribe Taishanese ❌

`faster-whisper` `large-v3-turbo`, `language="yue"` (Cantonese), on real DLI audio:

```
[58.1-96.8] NICINI EDI, chega NIR GINI,期 NIR QI,I LII,FI,JAR MI,FI,JAR MI...
```

Gibberish — while still reporting **`language=yue (p=1.00)`**. The confidence is
therefore worthless as a sanity check, which makes this trap especially easy to fall
into: a pipeline that logs the detected language will look healthy while producing
nothing usable. Taishanese is not mutually intelligible with Cantonese, and that gap
is exactly why the lexicon in `data/` had to be built by hand.

`transcribe_probe.py` is the harness.

Two library traps to know before running it:

- **`faster-whisper` 1.2.1 is incompatible with PyAV 19** (`metadata_errors` kwarg).
  Decode with ffmpeg and pass a numpy array — that path skips `decode_audio()`.
- **ffmpeg writes a corrupt header when piping WAV output** (it cannot seek back to
  patch the RIFF size, so readers see a truncated file). Read raw `s16le` instead.

## 2. Structural text↔audio alignment ❌

With no acoustic model, the tempting fallback is structural: parse the OCR'd textbook
into speaker turns, VAD the audio, pair monotonically. Measured over all 60 lessons:

| metric | value |
|---|---|
| lessons with a plausible VAD/turn ratio (0.5–2.0) | **2 / 60** |
| ratio quartiles | 1.3, 6.5, 9.2, 13.9 |
| worst case | 647 VAD segments for 10 turns |
| pairs produced | 807, only 64% utterance-sized |
| pair duration | mean 37 s, **max 762 s** |

Two compounding causes: the VAD splits a single speaker's line at internal pauses, and
the OCR turn parser under-counts. Output is not a training corpus.

## 3. Duration-informed DP alignment ❌

`dp_align.py` does monotonic alignment of text turns onto VAD segments. Three design
choices were each necessary, and each was found by measurement:

- **Full audio coverage is required.** Without it the DP degenerates: it gives each
  turn the shortest possible span and leaves the rest of the audio unassigned, which
  drives the fitted duration scale to zero.
- **A skip state is required.** The tapes carry material the textbook does not (English
  instructions, vocabulary read aloud). Forcing every segment onto a turn makes the DP
  dump that audio into a few turns — visible as only 70% of turns receiving any audio.
- **Score candidate duration scales by median relative error, not raw DP cost.** DP
  cost is monotone in the scale, so it always collapses to the minimum.

Scored honestly, with turns that receive no audio counted as failures:

| lesson set | placed | median duration error | within 25% |
|---|---|---|---|
| all sampled | 97% | **0.58** | 31% |
| lessons 30–31 (large count mismatch) | 100% | 0.43 | 35% |
| **lesson 9 — control** | 100% | **0.26** | **48%** |

**Lesson 9 is what settles it.** Its merged VAD count (75 raw segments → 21 at a 2.0 s
merge threshold) *exactly equals* its 21 text turns — the best case this method can
possibly have — and it still lands at 26% median duration error. The ceiling is set by
the signal, not the search: **duration alone cannot distinguish the correct monotonic
assignment from near-misses.**

### A measurement trap worth internalising

An intermediate version of this scored **median 0.13** and looked excellent. It was
measured only over the 70% of turns that received audio, quietly excluding the hard
cases. The honest figure for the same configuration is 0.58. Any metric on this problem
must count unplaced turns as failures.

---

## Lesson ↔ audio mapping (easy to get wrong)

The `lNN` in `toisan-vNN-lMM.mp3` is the **global** lesson number, not per-volume:
`toisan-v02-l21` is lesson 21, not volume-2 lesson 1. Volumes 1–3 cover lessons
1–20 / 21–40 / 41–60. **Volumes 4–6 restart at `l01`** — a separate edition; include
them and every lesson matches twice. Some files cover two lessons (`l02-03`,
`l06-and-07`), so parse all numbers in the name and drop the first (the volume).

## VAD granularity (a diagnostic that motivated the DP)

A fixed merge threshold cannot work — the tapes vary by ~10 dB between files, so a
single `silencedetect=noise=` value finds nothing on quiet ones and over-cuts loud ones.
`segment_vad.py` therefore derives a per-file noise floor from the frame-energy
distribution. Even so, the resulting segments are finer than speaker turns:

| lesson | turns | raw | g=0.5 | g=1.0 | g=1.5 | g=2.0 | g=3.0 |
|---|---|---|---|---|---|---|---|
| 9 | 21 | 75 | 54 | 34 | 28 | **21** | 3 |
| 4 | 20 | 26 | 21 | **19** | 14 | 9 | 1 |
| 31 | 22 | 120 | 84 | 65 | 56 | 53 | 46 |

No single column matches every row. `diag_vad_granularity.py` regenerates this.

## Files

| file | what it is |
|---|---|
| `segment_vad.py` | energy-based VAD with adaptive noise floor — **works**, reuse it |
| `diag_vad_granularity.py` | merge-threshold sweep diagnostic |
| `dp_align.py` | the DP aligner (correct, insufficient signal) |
| `sweep_alignment.py` | skip×scale sweep with the honest metric |
| `build_dli_text.py` | merges the two OCR passes into per-lesson text |
| `build_pairs.py` | the superseded count-matching aligner |
| `transcribe_probe.py` | the Whisper harness |
