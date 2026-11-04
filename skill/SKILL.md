# Video Understanding — transcript + key frames

Understand a video (YouTube link or a media file) by combining a timestamped transcript with frames pulled at the moments that matter. Built for the author's two main uses: **car-mechanic how-to videos** (steps, specs, warnings) and **long research/lecture videos** (outline, claims, where things are said). The transcript says *when*; the frames show *what*.

## Environment (measured 2026-11-02, this VM)

- 4 CPU cores (AMD EPYC), ~8 GB RAM, no GPU. **That is enough** — see measured performance below.
- Tools live in a venv: `~/workspace/tools/video-env/bin/` (`yt-dlp` 2026.10.26, `faster-whisper` 1.2.1). System `ffmpeg` 8.1.2 is on PATH.
- Whisper models cache under `~/.cache/huggingface/`; `base` is already downloaded.
- Scripts: `scripts/captions.py` (json3 → clean transcript), `scripts/transcribe.py` (Whisper, ffmpeg-decoded).

## Route order (always in this order)

1. **Existing captions first** (YouTube CC or auto-captions): free, instant, already timestamped.
2. **Check for the [Music] trap**: some videos (AUTODOC-style tips) have caption tracks that are only `[Music]` markers — the content is in on-screen text overlays. `captions.py` warns when this happens. Then the **frame route is the primary source**, densely sampled.
3. **No usable captions → local Whisper** on this VM (`transcribe.py`). Never send audio to a paid transcription service for this; local is free and measured fast enough.
4. **Frames for anything visual**: a step's hand position, a part's location, a slide, an overlay spec. Transcript alone never establishes a visual claim.

## Step 1 — captions (YouTube)

```sh
V=~/workspace/tools/video-env/bin/yt-dlp
$V --skip-download --write-subs --write-auto-subs --sub-langs "en" --sub-format "json3" -o "caps.%(ext)s" "<video URL>"
~/workspace/tools/video-env/bin/python scripts/captions.py caps.en.json3
```

- Fetch **only** the exact `en` track. Requesting the whole auto-translate language list trips YouTube rate limits (HTTP 429, seen live 2026-11-02 on the `en-ar` variant).
- Creator-uploaded CC beats auto-captions; note which one you got (it shows in the deliverable).
- `--write-subs` + `--write-auto-subs` together: yt-dlp prefers the creator track when both exist.

## Step 2 — Whisper (no captions, or a local file)

```sh
~/workspace/tools/video-env/bin/python scripts/transcribe.py MEDIA --model base --out transcript.txt
```

- `base` int8 is the default: on this VM it ran **8.0× realtime** (120 s of ChrisFix narration → 15 s, 28 segments, near-verbatim vs his own captions). A 20-minute video ≈ 3 minutes; an hour lecture ≈ 8 minutes.
- Use `--model small` only when base garbles domain terms in a first sample; it costs roughly 2–3× the time. Do not reach for `medium`/`large` on CPU.
- The script decodes audio with ffmpeg and feeds samples to the model — do not "simplify" it back to passing a file path: faster-whisper's PyAV decode path breaks on current PyAV (`av.open()` dropped `metadata_errors`).
- For a long YouTube video with no captions, don't download the whole thing first if you only need part: `yt-dlp -f worstaudio --download-sections "*0-120"` fetched a clean 120 s slice (verified). For a full transcript, download full audio as m4a (never WAV — a 20-minute WAV is ~200 MB and a conversion died on a transient disk-full 2026-11-02; the m4a is ~10 MB) and slice locally with ffmpeg.

## Step 3 — frames

```sh
$V -f "bv[height<=480]" -o "video.%(ext)s" "<video URL>"     # or use the file already on hand
ffmpeg -ss 30 -i video.mp4 -frames:v 1 -q:v 3 frame_30.jpg -y
```

- **480p is the floor** (854×480): overlay text and part detail are crisp at 480p; at 144p (256×144, the `worst` format) overlay text is barely legible. Never do frame analysis below 480p.
- Pull frames at transcript timestamps that carry information: a named step, a spec, a warning, a "this one here" moment. For [Music]-trap videos, sample on the overlay changes (every ~5–10 s, or scene-change detection) instead.
- Use **one** downloaded file for both frames and transcript alignment, and spot-check one frame against its caption line — different encodes can sit a step apart at the same nominal second (seen live: t=30 showed step 1 in one encode, step 4 in another).

## Deliverables

**Mechanic how-to** → a job card: tools/parts needed (with sizes), the step list in order, every spec (torque, viscosity, quantities, gaps) with its timestamp, and the warnings. Specs get the verification treatment below.

**Lecture / research** → an outline with timestamps, the claims made and what evidence the speaker shows for each, slides captured as frames where a slide carries data the speech doesn't, and open questions the video leaves.

Either way, name the transcript source in the deliverable: `creator CC` / `YouTube auto-captions` / `Whisper base (local)`.

## Verification rules

- **Numbers are guilty until checked.** Auto-captions and Whisper both garble specs (0W-20 vs 10W-30, "4 quarts" vs "5"). Any number the user will act on gets cross-checked against a frame (overlay, label, gauge) or a second source, and the deliverable says which numbers were frame-verified and which are transcript-only.
- A delegate's or the pipeline's own summary is never the check — re-read the actual transcript lines and frames behind a claim before repeating it.
- Timestamps in the deliverable come from the transcript/frames, never estimated.

## Limits (honest)

- Frame sampling sees moments, not motion: fast action between sampled frames can be missed. For a "when exactly does X happen" question, sample densely around the transcript cue.
- Whisper quality drops with heavy accent, crosstalk, or loud background music; sample a minute first on a new channel before committing to a full run.
- YouTube access from this VM goes through an egress proxy that intermittently cuts large downloads and rate-limits bursts. Small fetches (captions, audio slices) are reliable; full-video downloads may need retries. If a video matters and the VM route keeps failing, the fallback is the user downloading the file and handing it over — not a paid service.
- Installing Python packages here has its own gotcha (proxy cuts pip's big wheels): harvest wheel URLs with `pip install --dry-run --report`, fetch with a `curl -C -` resume loop, verify sha256 against the report, install with `--no-index --find-links`. Proven 2026-11-02 for all 23 faster-whisper wheels.

## Provenance

Built and tested end-to-end 2026-11-02 on the author's order: ChrisFix "How to Change Your Oil" (O1hF25Cowv8 — 282 creator-caption lines; Whisper base matched them near-verbatim at 8.0× realtime) and AUTODOC "How to check your car's engine oil level" (SlSuCevpArU — the [Music]-trap counterexample; content recovered from 480p frames).
