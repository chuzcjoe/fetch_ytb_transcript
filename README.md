# YouTube Transcript Fetcher and Video Summarizer

A small Python command-line tool and local Codex Skill for working with YouTube videos.

The command-line tool downloads available captions and saves them as a timestamped UTF-8 text file. The Codex Skill can then summarize the video's full spoken content. It always tries captions first; if the video has no captions, it can download the audio and transcribe it locally on a supported Mac.

## Features

- Download creator-provided or automatically generated YouTube captions.
- List all available caption languages and select a specific language.
- Save every caption segment with its start and end time.
- Summarize a video with the bundled `youtube-video-summary` Codex Skill.
- Fall back to local audio transcription when captions do not exist.
- Keep downloaded audio, transcripts, and model processing on the local machine during the fallback workflow.

## Requirements

For caption downloads:

- Python 3.10 or later
- An internet connection

For the optional audio-transcription fallback:

- macOS on Apple Silicon
- [FFmpeg](https://ffmpeg.org/)
- Enough free disk space for the downloaded audio and speech-recognition model

The audio fallback uses `mlx-whisper` with the `mlx-community/whisper-large-v3-turbo` model. The model is downloaded automatically the first time it is needed.

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/chuzcjoe/fetch_ytb_transcript.git
cd fetch_ytb_transcript
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

The standalone caption tool works wherever its Python dependencies are supported. The audio fallback is currently limited to Apple Silicon Macs.

## Download a Transcript

Pass a YouTube URL to the command-line tool:

```bash
python3 youtube_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

By default, the transcript is saved as `<video-id>_transcript.txt` in the current directory.

### Choose the output file

```bash
python3 youtube_transcript.py "YOUTUBE_URL" --output transcripts/video.txt
```

### List available caption languages

```bash
python3 youtube_transcript.py "YOUTUBE_URL" --list-languages
```

### Select a caption language

```bash
python3 youtube_transcript.py "YOUTUBE_URL" --language en
```

If no language is specified, the tool prefers the video's original language, then English, then another available manual or automatic caption track.

Each transcript includes basic video metadata followed by timestamped caption segments:

```text
Title: Example Video
URL: https://www.youtube.com/watch?v=VIDEO_ID
Video ID: VIDEO_ID
Caption language: en
Caption type: manual

[00:00:00.000 --> 00:00:04.200] First caption segment.
[00:00:04.200 --> 00:00:08.500] Next caption segment.
```

## Summarize a Video with Codex

This repository includes a local Codex Skill at `.codex/skills/youtube-video-summary/`.

From the repository workspace, ask Codex to use it with a YouTube URL. For example:

```text
Use $youtube-video-summary to summarize this video:
https://www.youtube.com/watch?v=VIDEO_ID
```

The Skill follows this workflow:

1. It tries to retrieve the video's complete caption transcript.
2. If YouTube reports that the video has no captions, it downloads the audio and transcribes it locally.
3. It reads the complete transcript and produces a thematic summary in the language used in your request.

The fallback is used only when captions are genuinely unavailable. Authentication, network, access, or dependency errors are reported instead of being treated as missing captions.

### Audio fallback setup

The Skill installs its audio dependencies in a separate environment under `work/` when needed. FFmpeg must already be installed and available on your `PATH`. On macOS with Homebrew, you can install it with:

```bash
brew install ffmpeg
```

To run the local audio transcription script directly:

```bash
python3 -m venv work/.youtube-summary-venv
work/.youtube-summary-venv/bin/python -m pip install \
  -r .codex/skills/youtube-video-summary/scripts/audio-requirements.txt
work/.youtube-summary-venv/bin/python \
  .codex/skills/youtube-video-summary/scripts/youtube_audio_transcript.py \
  "YOUTUBE_URL" \
  --output work/youtube_audio_transcript.txt
```

Downloaded audio and generated transcripts are stored under `work/`, which is excluded from Git.

## Project Structure

```text
.
├── README.md
├── requirements.txt
├── youtube_transcript.py
└── .codex/skills/youtube-video-summary/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    └── scripts/
        ├── audio-requirements.txt
        ├── requirements.txt
        ├── youtube_audio_transcript.py
        └── youtube_transcript.py
```

## Limitations and Troubleshooting

- Caption availability depends on the video owner and YouTube. Some videos have no captions or may require authentication, regional access, or age verification.
- YouTube may rate-limit or temporarily block automated requests.
- Automatically generated captions and local speech recognition can contain mistakes, especially with names, technical terms, strong accents, or poor audio.
- If `yt-dlp` cannot be imported, reactivate the virtual environment and run `python3 -m pip install -r requirements.txt`.
- If the fallback reports that FFmpeg is missing, install FFmpeg and confirm that `ffmpeg -version` works in the same terminal.
- The current local transcription fallback does not support Intel Macs, Windows, or Linux.

Only download or process videos that you are permitted to access and use.
