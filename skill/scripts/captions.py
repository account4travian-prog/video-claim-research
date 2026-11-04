#!/usr/bin/env python3
"""Convert a YouTube json3 caption file (from yt-dlp) into a clean timestamped
transcript. Usage: captions.py CAPS.en.json3 [--out transcript.txt]
Rolling auto-captions repeat the previous line; consecutive duplicates and
partial-prefix lines are collapsed. Prints a warning when the track is mostly
[Music]/empty (music + overlay-text videos: the frames carry the content)."""
import argparse, json, re, sys

p = argparse.ArgumentParser()
p.add_argument("json3")
p.add_argument("--out", default=None)
a = p.parse_args()

d = json.load(open(a.json3))
f = lambda ms: f"{int(ms//60000):02d}:{int(ms//1000)%60:02d}"
lines, prev = [], ""
music = 0
for e in d.get("events", []):
    segs = e.get("segs")
    if not segs or "tStartMs" not in e:
        continue
    text = "".join(s.get("utf8", "") for s in segs).replace("\n", " ").strip()
    if not text:
        continue
    if re.fullmatch(r"\[.*\]", text):
        music += 1
        continue
    if text == prev or (prev and text.startswith(prev)):
        prev = text
        continue
    lines.append(f"[{f(e['tStartMs'])}] {text}")
    prev = text

total = len(lines) + music
if total and music / total > 0.5:
    print(f"WARNING: {music}/{total} caption events were [Music]/markers — this video likely has "
          "no real narration; use the frame route (overlay text) instead.", file=sys.stderr)
out = a.out or (a.json3.rsplit(".", 2)[0] + ".transcript.txt")
open(out, "w").write("\n".join(lines) + "\n")
print(f"{len(lines)} lines -> {out}")
