#!/usr/bin/env python3
"""Transcribe audio/video to a timestamped transcript with faster-whisper (CPU).
Audio is decoded with ffmpeg (not PyAV, whose API drifts) and fed to the model
as samples. Usage: transcribe.py MEDIA [--model base] [--out transcript.txt]
Output: one line per segment, [MM:SS-MM:SS] text, with a stats header/footer."""
import argparse, subprocess, sys, time
import numpy as np
from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument("media")
p.add_argument("--model", default="base")
p.add_argument("--out", default=None)
a = p.parse_args()

def load_audio(path):
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

t0 = time.time()
model = WhisperModel(a.model, device="cpu", compute_type="int8", cpu_threads=4)
audio = load_audio(a.media)
segments, info = model.transcribe(audio, beam_size=1, vad_filter=True)
f = lambda x: f"{int(x//60):02d}:{int(x%60):02d}"
lines = [f"# source: {a.media} | lang: {info.language} ({info.language_probability:.2f}) | audio: {info.duration:.0f}s | model: {a.model} int8 cpu"]
count = 0
for s in segments:
    lines.append(f"[{f(s.start)}-{f(s.end)}] {s.text.strip()}")
    count += 1
elapsed = time.time() - t0
lines.append(f"# segments: {count} | wall time: {elapsed:.0f}s | realtime factor: {info.duration/elapsed:.1f}x")
out = a.out or (a.media.rsplit(".", 1)[0] + ".transcript.txt")
open(out, "w").write("\n".join(lines) + "\n")
print("\n".join(lines[:8]))
print(f"... wrote {out}")
