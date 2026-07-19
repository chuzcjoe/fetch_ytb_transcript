#!/usr/bin/env python3
"""Download a YouTube audio track and transcribe it locally with MLX Whisper."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    import mlx_whisper
    from yt_dlp import YoutubeDL
except ImportError:  # pragma: no cover - exercised only without dependencies
    print(
        "Missing audio transcription dependencies. Install them with "
        "`python3 -m pip install -r scripts/audio-requirements.txt`.",
        file=sys.stderr,
    )
    raise SystemExit(2)


DEFAULT_MODEL = "mlx-community/whisper-large-v3-turbo"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a YouTube audio track and save a timestamped transcript."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("work/youtube_audio_transcript.txt"),
        help="Transcript .txt path (default: work/youtube_audio_transcript.txt)",
    )
    parser.add_argument(
        "-l",
        "--language",
        help="Spoken-language code such as en, zh, or yue (default: auto-detect)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"MLX Whisper model or Hugging Face repo (default: {DEFAULT_MODEL})",
    )
    return parser.parse_args()


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def ensure_runtime() -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError(
            "The bundled audio fallback requires an Apple Silicon Mac "
            "because it uses MLX Whisper."
        )
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required to decode the downloaded audio track.")


def download_audio(url: str, directory: Path) -> tuple[dict[str, Any], Path]:
    directory.mkdir(parents=True, exist_ok=True)
    options = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "outtmpl": str(directory / "%(id)s_audio.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        if not isinstance(info, dict):
            raise RuntimeError("Could not read video metadata.")
        audio_path = Path(ydl.prepare_filename(info))
    if not audio_path.is_file():
        raise RuntimeError(f"Downloaded audio file was not found: {audio_path}")
    return info, audio_path


def render_transcript(
    info: dict[str, Any], result: dict[str, Any], model: str, audio_path: Path
) -> str:
    lines = [
        f"Title: {info.get('title') or 'Unknown'}",
        f"URL: {info.get('webpage_url') or info.get('original_url') or ''}",
        f"Video ID: {info.get('id') or ''}",
        "Transcript source: downloaded audio",
        f"ASR language: {result.get('language') or 'unknown'}",
        f"ASR model: {model}",
        f"Audio file: {audio_path}",
        "",
    ]
    for segment in result.get("segments") or []:
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        start = timestamp(float(segment.get("start") or 0))
        end = timestamp(float(segment.get("end") or 0))
        lines.append(f"[{start} --> {end}] {text}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    output = args.output.with_suffix(".txt")
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        ensure_runtime()
        info, audio_path = download_audio(args.url, output.parent)
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=args.model,
            language=args.language,
            task="transcribe",
            verbose=False,
        )
        if not isinstance(result, dict) or not result.get("segments"):
            raise RuntimeError("The audio transcription returned no speech segments.")

        output.write_text(
            render_transcript(info, result, args.model, audio_path), encoding="utf-8"
        )
        json_output = output.with_suffix(".json")
        json_output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Saved {len(result['segments'])} audio transcript segments "
            f"({result.get('language') or 'unknown'}) to {output.resolve()}"
        )
        return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
