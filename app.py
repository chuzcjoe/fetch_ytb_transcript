"""Web tool + JSON API that fetches subtitle tracks for a YouTube video."""

import os
import re

from flask import Flask, Response, jsonify, request, send_from_directory
from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig

app = Flask(__name__, static_folder="static", static_url_path="")


def _build_proxy_config():
    """Optional proxy for cloud hosts whose IPs YouTube blocks.

    Set WEBSHARE_PROXY_USERNAME/PASSWORD (Webshare residential proxies,
    natively supported by youtube-transcript-api), or PROXY_HTTP_URL /
    PROXY_HTTPS_URL for any other proxy. Unset = direct connection.
    """
    username = os.environ.get("WEBSHARE_PROXY_USERNAME")
    password = os.environ.get("WEBSHARE_PROXY_PASSWORD")
    if username and password:
        return WebshareProxyConfig(proxy_username=username, proxy_password=password)
    http_url = os.environ.get("PROXY_HTTP_URL")
    https_url = os.environ.get("PROXY_HTTPS_URL")
    if http_url or https_url:
        return GenericProxyConfig(http_url=http_url, https_url=https_url)
    return None


_PROXY_CONFIG = _build_proxy_config()
# Lock the API down to your site by setting e.g. ALLOWED_ORIGIN=https://you.github.io
_ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")

# Matches watch?v=, youtu.be/, shorts/, embed/, live/, /v/ URLs, or a bare 11-char id.
_VIDEO_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/|v/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)
_BARE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def extract_video_id(text: str) -> str | None:
    text = text.strip()
    if _BARE_ID_RE.match(text):
        return text
    match = _VIDEO_ID_RE.search(text)
    return match.group(1) if match else None


@app.after_request
def allow_cors(response):
    response.headers["Access-Control-Allow-Origin"] = _ALLOWED_ORIGIN
    return response


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


def _resolve(url: str):
    """Extract the video id and list its transcripts.

    Returns (video_id, transcript_list, error) where error is a ready
    (response, status) pair and the other fields are None on failure.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None, None, (
            jsonify(error="Could not find a valid YouTube video ID in that URL."),
            400,
        )
    try:
        api = YouTubeTranscriptApi(proxy_config=_PROXY_CONFIG)
        return video_id, api.list(video_id), None
    except CouldNotRetrieveTranscript as exc:
        return None, None, (jsonify(error=_clean_error(exc)), 404)
    except Exception:
        return None, None, (
            jsonify(error="Unexpected error while contacting YouTube. Please try again."),
            502,
        )


@app.route("/api/languages")
def languages():
    """List available subtitle tracks without fetching their content."""
    video_id, transcript_list, error = _resolve(request.args.get("url", ""))
    if error:
        return error

    tracks = [
        {
            "language": t.language,
            "language_code": t.language_code,
            "is_generated": t.is_generated,
        }
        for t in transcript_list
    ]
    if not tracks:
        return jsonify(error="This video has no subtitles."), 404
    return jsonify(video_id=video_id, languages=tracks)


@app.route("/api/transcripts")
def transcripts():
    fmt = request.args.get("format", "json").lower()
    if fmt not in ("json", "text", "srt"):
        return jsonify(error="format must be one of: json, text, srt."), 400

    video_id, transcript_list, error = _resolve(request.args.get("url", ""))
    if error:
        return error

    available = list(transcript_list)
    if not available:
        return jsonify(error="This video has no subtitles."), 404

    lang_param = request.args.get("lang", "")
    wanted = [c.strip().lower() for c in lang_param.split(",") if c.strip()]
    if wanted:
        selected = [t for t in available if t.language_code.lower() in wanted]
        if not selected:
            return jsonify(
                error=f"No transcript found for language(s): {lang_param}.",
                available_languages=[t.language_code for t in available],
            ), 404
    else:
        selected = available

    # text/srt are single-track formats: use the first selected track
    # (pass lang= to pick a specific one).
    if fmt in ("text", "srt"):
        transcript = selected[0]
        try:
            fetched = transcript.fetch()
        except CouldNotRetrieveTranscript as exc:
            return jsonify(error=_clean_error(exc)), 404
        if fmt == "text":
            body = "\n".join(snippet.text for snippet in fetched)
        else:
            body = _to_srt(fetched)
        return Response(body, mimetype="text/plain; charset=utf-8")

    tracks = []
    for transcript in selected:
        track = {
            "language": transcript.language,
            "language_code": transcript.language_code,
            "is_generated": transcript.is_generated,
        }
        try:
            fetched = transcript.fetch()
            track["entries"] = [
                {"text": s.text, "start": s.start, "duration": s.duration}
                for s in fetched
            ]
        except CouldNotRetrieveTranscript as exc:
            track["error"] = _clean_error(exc)
        tracks.append(track)

    return jsonify(video_id=video_id, transcripts=tracks)


def _to_srt(fetched) -> str:
    blocks = []
    for i, snippet in enumerate(fetched, 1):
        start = _srt_time(snippet.start)
        end = _srt_time(snippet.start + snippet.duration)
        blocks.append(f"{i}\n{start} --> {end}\n{snippet.text}\n")
    return "\n".join(blocks)


def _srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    hours, ms = divmod(ms, 3_600_000)
    minutes, ms = divmod(ms, 60_000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _clean_error(exc: CouldNotRetrieveTranscript) -> str:
    # The library's messages end with a long troubleshooting section; keep the first line.
    return str(exc).strip().split("\n")[0].strip()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5001)), debug=False)
