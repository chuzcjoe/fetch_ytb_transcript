#!/usr/bin/env python3
"""Download a YouTube transcript and save it as timestamped plain text."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import unescape
from pathlib import Path
from typing import Any

try:
    from yt_dlp import YoutubeDL
    from yt_dlp.networking.common import Request
except ImportError:  # pragma: no cover - exercised only without the dependency
    print(
        "Missing dependency: yt-dlp. Install it with "
        "`python3 -m pip install -r requirements.txt`.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Save all available caption cues from a YouTube video to a .txt file."
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output .txt path (default: <video-id>_transcript.txt)",
    )
    parser.add_argument(
        "-l",
        "--language",
        help="Caption language code, for example en-orig, en, or zh-Hans",
    )
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List available caption tracks without writing a transcript",
    )
    return parser.parse_args()


def timestamp(milliseconds: int) -> str:
    total_seconds, millis = divmod(max(0, milliseconds), 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def available_tracks(info: dict[str, Any]) -> dict[str, tuple[str, list[dict[str, Any]]]]:
    tracks: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    for kind, key in (("manual", "subtitles"), ("automatic", "automatic_captions")):
        for language, formats in (info.get(key) or {}).items():
            if formats:
                tracks.setdefault(language, (kind, formats))
    return tracks


def choose_track(
    info: dict[str, Any], requested: str | None
) -> tuple[str, str, list[dict[str, Any]]]:
    tracks = available_tracks(info)
    if not tracks:
        raise RuntimeError("This video has no available captions.")

    if requested:
        if requested in tracks:
            kind, formats = tracks[requested]
            return requested, kind, formats
        prefix_matches = [code for code in tracks if code.split("-", 1)[0] == requested]
        if len(prefix_matches) == 1:
            code = prefix_matches[0]
            kind, formats = tracks[code]
            return code, kind, formats
        raise RuntimeError(
            f"Caption language {requested!r} is unavailable. "
            f"Available codes: {', '.join(sorted(tracks))}"
        )

    video_language = info.get("language")
    candidates: list[str] = []
    if video_language:
        candidates.extend((f"{video_language}-orig", video_language))
    candidates.extend(code for code in tracks if code.endswith("-orig"))
    candidates.extend(("en-orig", "en"))

    for code in candidates:
        if code in tracks:
            kind, formats = tracks[code]
            return code, kind, formats

    # Prefer creator-provided captions if no original-language hint is available.
    for code, (kind, formats) in tracks.items():
        if kind == "manual":
            return code, kind, formats
    code, (kind, formats) = next(iter(tracks.items()))
    return code, kind, formats


def json3_format(formats: list[dict[str, Any]]) -> dict[str, Any]:
    for item in formats:
        if item.get("ext") == "json3":
            return item
    raise RuntimeError("The selected caption track does not provide JSON3 data.")


def download_json3(ydl: YoutubeDL, item: dict[str, Any]) -> dict[str, Any]:
    url = item.get("url")
    if not url:
        raise RuntimeError("The selected caption track has no download URL.")
    response = ydl.urlopen(Request(url))
    try:
        return json.loads(response.read().decode("utf-8"))
    finally:
        response.close()


def caption_cues(data: dict[str, Any]) -> list[tuple[int, int, str]]:
    cues: list[tuple[int, int, str]] = []
    for event in data.get("events", []):
        segments = event.get("segs") or []
        if not segments or event.get("aAppend"):
            continue
        text = "".join(segment.get("utf8", "") for segment in segments)
        text = unescape(re.sub(r"\s+", " ", text)).strip()
        if not text:
            continue
        start = int(event.get("tStartMs", 0))
        end = start + int(event.get("dDurationMs", 0))
        cues.append((start, end, text))
    return cues


def safe_filename(value: str) -> str:
    value = re.sub(r"[^\w.-]+", "_", value, flags=re.UNICODE).strip("._")
    return value or "youtube_transcript"


def render_transcript(
    info: dict[str, Any], language: str, kind: str, cues: list[tuple[int, int, str]]
) -> str:
    lines = [
        f"Title: {info.get('title') or 'Unknown'}",
        f"URL: {info.get('webpage_url') or info.get('original_url') or ''}",
        f"Video ID: {info.get('id') or ''}",
        f"Caption language: {language}",
        f"Caption type: {kind}",
        "",
    ]
    lines.extend(
        f"[{timestamp(start)} --> {timestamp(end)}] {text}"
        for start, end, text in cues
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    options = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(args.url, download=False)
            if not isinstance(info, dict):
                raise RuntimeError("Could not read video metadata.")

            tracks = available_tracks(info)
            if args.list_languages:
                if not tracks:
                    print("No captions are available for this video.")
                    return 1
                for code, (kind, _) in sorted(tracks.items()):
                    print(f"{code}\t{kind}")
                return 0

            language, kind, formats = choose_track(info, args.language)
            data = download_json3(ydl, json3_format(formats))
            cues = caption_cues(data)
            if not cues:
                raise RuntimeError("The selected caption track is empty.")

            output = args.output
            if output is None:
                output = Path(f"{safe_filename(str(info.get('id') or 'video'))}_transcript.txt")
            if output.suffix.lower() != ".txt":
                output = output.with_suffix(".txt")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(render_transcript(info, language, kind, cues), encoding="utf-8")
            print(f"Saved {len(cues)} caption cues ({language}, {kind}) to {output.resolve()}")
            return 0
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
