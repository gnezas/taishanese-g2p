#!/usr/bin/env python3
"""Segment + pseudo-label a DLI lesson with faster-whisper (CPU, no GPU).

Notes on this environment:
  * faster-whisper 1.2.1 is incompatible with PyAV 19 (`metadata_errors` kwarg),
    so audio is decoded with ffmpeg and passed in as a numpy array — that path
    skips decode_audio() entirely.
  * faster-whisper bundles Silero VAD, so vad_filter=True does utterance
    segmentation and transcription in one pass, with timestamps.

Usage: transcribe_probe.py <audio> [minutes] [model]
"""
import io, json, os, subprocess, sys, time, wave

import numpy as np
from faster_whisper import WhisperModel

SR = 16000


def load_audio(path, sr=SR):
    """Decode any audio to mono float32 @16k via ffmpeg (no PyAV).

    Raw s16le rather than WAV: ffmpeg cannot seek back to patch the RIFF size
    when writing to a pipe, so a piped WAV header reports a bogus frame count and
    the `wave` module reads almost nothing (observed: 2s from a 127s file).
    """
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1",
         "-ar", str(sr), "-"],
        capture_output=True, check=True)
    if not p.stdout:
        raise RuntimeError(f"ffmpeg produced no audio for {path}: {p.stderr[:400]!r}")
    data = np.frombuffer(p.stdout, dtype=np.int16)
    return data.astype(np.float32) / 32768.0


def main():
    audio = sys.argv[1]
    minutes = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    model_name = sys.argv[3] if len(sys.argv) > 3 else "large-v3-turbo"

    print(f"model={model_name}  audio={os.path.basename(audio)}  "
          f"first {minutes or 'all'} min", flush=True)

    t0 = time.time()
    samples = load_audio(audio)
    if minutes > 0:
        samples = samples[: int(minutes * SR)]
    print(f"decoded {len(samples)/SR:.0f}s of audio in {time.time()-t0:.1f}s", flush=True)

    t0 = time.time()
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    print(f"model loaded in {time.time()-t0:.0f}s", flush=True)

    t0 = time.time()
    segments, info = model.transcribe(
        samples,                     # ndarray -> skips PyAV
        language="yue",              # Cantonese: closest thing Whisper has
        task="transcribe",
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=450, speech_pad_ms=120),
        beam_size=5,
        condition_on_previous_text=False,
    )
    segs = list(segments)
    el = time.time() - t0
    dur = sum(s.end - s.start for s in segs)
    print(f"\ntranscribed in {el:.0f}s | {len(segs)} segments | {dur:.0f}s speech")
    print(f"speed: {dur/max(el,0.01):.2f}x realtime")
    print(f"detected language: {info.language} (p={info.language_probability:.2f})\n")
    for s in segs[:30]:
        print(f"  [{s.start:6.1f}-{s.end:6.1f}] {s.text.strip()}")

    out = os.path.splitext(audio)[0] + ".probe.json"
    json.dump([{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs],
              open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
