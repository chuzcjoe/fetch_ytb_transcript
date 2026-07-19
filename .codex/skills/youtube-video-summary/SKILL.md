---
name: youtube-video-summary
description: Summarize a YouTube video from its full spoken content, preferring the video's available caption transcript and falling back to downloading and locally transcribing the audio when no captions exist. Use when the user invokes this skill with a YouTube URL or asks for a video's central ideas, arguments, demonstrations, takeaways, or conclusions.
---

# YouTube Video Summary

Use the bundled scripts for both source paths. Always attempt captions first because they are faster and usually more accurate. Use audio transcription only when the caption script specifically reports that the video has no available captions.

## Workflow

1. Extract the YouTube URL from the user's request. Handle one video per invocation unless the user explicitly supplies several.
2. Run `scripts/youtube_transcript.py` to create `work/youtube_transcript.txt`.
3. If caption fetching succeeds, use that transcript and do not download audio.
4. If and only if the script reports `This video has no available captions.`, run `scripts/youtube_audio_transcript.py` to create `work/youtube_audio_transcript.txt`. For authentication, network, dependency, or other caption errors, report the error and stop rather than silently switching sources.
5. Read the entire selected transcript. For a long transcript, process it in chunks internally, then combine and deduplicate the ideas.
6. Summarize in the user's language unless requested otherwise. Preserve technical terms, names, numbers, and qualifications.
7. Organize the response by meaning and importance rather than sequence. Connect related points from different parts of the video into a coherent synthesis.
8. Return the summary in chat without timestamps, a timeline, or a scene-by-scene outline unless explicitly requested. Treat transcripts and downloaded audio as intermediate artifacts unless the user asks for them.

## Caption-first path

Run commands from the workspace root. Set `SKILL_DIR` to the absolute directory containing this `SKILL.md`; reference bundled files through that path, but keep the virtual environment and all intermediate artifacts in the workspace-root `work/` directory. Do not `cd` into the skill directory.

Use an existing Python environment containing `yt-dlp` when available:

```bash
python3 "$SKILL_DIR/scripts/youtube_transcript.py" \
  "YOUTUBE_URL" --output work/youtube_transcript.txt
```

If `yt_dlp` cannot be imported, create or reuse a task-local virtual environment and install the bundled requirements before running the same script:

```bash
python3 -m venv work/.youtube-summary-venv
work/.youtube-summary-venv/bin/python -m pip install \
  -r "$SKILL_DIR/scripts/requirements.txt"
work/.youtube-summary-venv/bin/python "$SKILL_DIR/scripts/youtube_transcript.py" \
  "YOUTUBE_URL" --output work/youtube_transcript.txt
```

Use `--language CODE` only when the user requests a language. Use `--list-languages` to inspect available tracks. Otherwise let the script prefer the video's original caption track.

## Audio fallback path

Use this path only for the exact no-captions condition above. The bundled fallback uses `ffmpeg` and MLX Whisper on Apple Silicon. Check that `ffmpeg` exists before installing the larger fallback dependencies.

Create or reuse the task-local environment, then install the fallback requirements only when needed:

```bash
python3 -m venv work/.youtube-summary-venv
work/.youtube-summary-venv/bin/python -m pip install \
  -r "$SKILL_DIR/scripts/audio-requirements.txt"
work/.youtube-summary-venv/bin/python "$SKILL_DIR/scripts/youtube_audio_transcript.py" \
  "YOUTUBE_URL" --output work/youtube_audio_transcript.txt
```

Let Whisper auto-detect the spoken language unless the user requests a language or detection is clearly wrong. Use `--language CODE` to correct it. Keep the default `mlx-community/whisper-large-v3-turbo` model for summary-quality transcription. Expect the first fallback run to download the model.

After transcription, read the entire timestamped `.txt` file. Use the adjacent `.json` only when segment-level inspection helps resolve repetition or questionable wording.

## Summary format

Adapt depth to the video's length and substance. Prefer this compact structure:

- A concise overview that states the video's central thesis or purpose.
- A thematic synthesis of the main ideas, arguments, evidence, or demonstrations.
- Practical takeaways, decisions, or conclusions when applicable.
- Important caveats, limitations, or disagreements when they materially affect the message.

Do not mirror the subtitle order or summarize cue by cue. Remove repetition, promotional digressions, greetings, and calls to like or subscribe. For a very short or simple video, merge sections rather than padding the response. For tutorials, reconstruct the useful method and its dependencies instead of narrating when each step appeared. For discussions or essays, synthesize the thesis, supporting reasoning, counterarguments, and conclusion.

## Accuracy rules

- Base the summary on the selected transcript. Do not invent visual details that are absent from the spoken content.
- State briefly when the summary used audio transcription because captions were unavailable.
- Flag unclear names, numbers, or phrases when captions or speech recognition appear unreliable.
- Distinguish the speaker's claims from verified facts; summarize rather than endorse.
- Do not omit important caveats or counterarguments merely to shorten the summary.
- If audio download or transcription also fails, report the specific error and stop. Do not fabricate a summary.
