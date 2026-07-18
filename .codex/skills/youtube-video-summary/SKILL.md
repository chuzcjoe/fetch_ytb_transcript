---
name: youtube-video-summary
description: Fetch a YouTube video's available captions with the bundled Python transcript script, then synthesize the whole video into a concise thematic summary without a timeline or timestamps. Use when the user invokes this skill with a YouTube URL, asks for a YouTube video summary based on subtitles, or wants the video's central ideas, arguments, and conclusions.
---

# YouTube Video Summary

Use the bundled `scripts/youtube_transcript.py` as the sole caption-fetching implementation. Do not replace it with a different downloader or transcript API.

## Workflow

1. Extract the YouTube URL from the user's request. Handle one video per invocation unless the user explicitly supplies several.
2. Run `scripts/youtube_transcript.py` to create a timestamped UTF-8 `.txt` transcript in the current workspace's `work/` directory. Treat this file as an intermediate artifact unless the user asks for it.
3. Read the entire transcript. For a long transcript, process it in chunks internally, then combine and deduplicate the ideas before writing the final response.
4. Summarize in the user's language unless they request another language. Preserve technical terms, names, numbers, and qualifications from the captions.
5. Organize the final response by meaning and importance rather than by the video's sequence. Connect related points from different parts of the video into a coherent synthesis.
6. Return the summary in chat. Do not include timestamps, a timeline, or a chronological scene-by-scene outline unless the user explicitly asks for one. Do not reproduce the full transcript unless explicitly requested.

## Running the bundled script

Resolve paths relative to this `SKILL.md` directory.

Use an existing Python environment containing `yt-dlp` when available:

```bash
python3 scripts/youtube_transcript.py "YOUTUBE_URL" --output work/youtube_transcript.txt
```

If `yt_dlp` cannot be imported, create or reuse a task-local virtual environment and install the bundled requirements before running the same script:

```bash
python3 -m venv work/.youtube-summary-venv
work/.youtube-summary-venv/bin/python -m pip install -r scripts/requirements.txt
work/.youtube-summary-venv/bin/python scripts/youtube_transcript.py "YOUTUBE_URL" --output work/youtube_transcript.txt
```

Use `--language CODE` only when the user requests a language. Use `--list-languages` to inspect available tracks. Otherwise let the script prefer the video's original caption track.

## Summary format

Adapt depth to the video's length and substance. Prefer this compact structure:

- A concise overview that states the video's central thesis or purpose.
- A thematic synthesis of the main ideas, arguments, evidence, or demonstrations.
- Practical takeaways, decisions, or conclusions when applicable.
- Important caveats, limitations, or disagreements when they materially affect the message.

Do not mirror the subtitle order or summarize cue by cue. Remove repetition, promotional digressions, greetings, and calls to like or subscribe. For a very short or simple video, merge sections rather than padding the response. For tutorials, reconstruct the useful method and its dependencies instead of narrating when each step appeared. For discussions or essays, synthesize the thesis, supporting reasoning, counterarguments, and conclusion.

## Accuracy rules

- Base the summary on the fetched captions. Do not invent visual details that are absent from the captions.
- Flag unclear names or phrases when automatic captions appear unreliable.
- Distinguish the speaker's claims from verified facts; summarize rather than endorse.
- Do not omit important caveats or counterarguments merely to shorten the summary.
- If the video has no accessible captions or the script fails, report the specific error and stop. Do not fabricate a summary.
