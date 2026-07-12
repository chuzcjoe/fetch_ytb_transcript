# YouTube Transcript Fetcher

A minimal web tool and JSON API: give it a YouTube video link and get back every available subtitle track (manual and auto-generated).

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
.venv/bin/python app.py
```

Then open http://127.0.0.1:5001 for the web UI (set the `PORT` env var to use a different port).

## API

CORS is enabled (`Access-Control-Allow-Origin: *`), so the API can be called from scripts, tools, or other web apps.

### `GET /api/transcripts`

Fetch subtitle content.

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | yes | YouTube link (`watch`, `youtu.be`, Shorts, live, embed) or a bare 11-char video ID |
| `lang` | no | Comma-separated language codes to filter, e.g. `en` or `en,de`. Default: all tracks |
| `format` | no | `json` (default), `text` (plain text), or `srt` (SubRip). `text`/`srt` return the first matching track, so pass `lang` to pick one |

```bash
# All tracks as JSON
curl "http://127.0.0.1:5001/api/transcripts?url=https://www.youtube.com/watch?v=VIDEO_ID"

# Only the English track
curl "http://127.0.0.1:5001/api/transcripts?url=https://youtu.be/VIDEO_ID&lang=en"

# Plain text (no timestamps)
curl "http://127.0.0.1:5001/api/transcripts?url=VIDEO_ID&format=text"

# Download as .srt
curl -o subs.srt "http://127.0.0.1:5001/api/transcripts?url=VIDEO_ID&lang=en&format=srt"
```

JSON response:

```json
{
  "video_id": "...",
  "transcripts": [
    {
      "language": "English",
      "language_code": "en",
      "is_generated": false,
      "entries": [{ "text": "...", "start": 1.2, "duration": 2.16 }]
    }
  ]
}
```

### `GET /api/languages`

List available subtitle tracks without fetching their content (fast).

```bash
curl "http://127.0.0.1:5001/api/languages?url=https://youtu.be/VIDEO_ID"
```

```json
{
  "video_id": "...",
  "languages": [
    { "language": "English", "language_code": "en", "is_generated": false }
  ]
}
```

### Errors

Errors are JSON with an `error` field and a matching HTTP status: `400` (bad URL or bad `format`), `404` (no subtitles, or requested `lang` not available — response includes `available_languages`), `502` (upstream failure).

## Web UI

Paste a link, click **Get Transcripts**: tracks shown as tabs with manual/auto badges, timestamped view, copy to clipboard, download as `.txt` or `.srt`.

## Deploying to Render (or similar)

The repo ships with [render.yaml](render.yaml) (Render blueprint) and a [Procfile](Procfile) (Railway/Heroku-style platforms). Production server is gunicorn.

1. Push this repo to GitHub.
2. On [render.com](https://render.com): **New → Web Service**, connect the repo. Build command `pip install -r requirements.txt`, start command `gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 app:app` (pre-filled if you use **New → Blueprint**, which reads render.yaml).
3. Test: `curl "https://<your-service>.onrender.com/api/languages?url=<video-url>"`.

### Environment variables

| Variable | Purpose |
|----------|---------|
| `ALLOWED_ORIGIN` | Lock CORS to your site, e.g. `https://you.github.io`. Default `*` |
| `WEBSHARE_PROXY_USERNAME` / `WEBSHARE_PROXY_PASSWORD` | Route YouTube requests through [Webshare](https://www.webshare.io/) residential proxies |
| `PROXY_HTTP_URL` / `PROXY_HTTPS_URL` | Any other HTTP(S) proxy |
| `PORT` | Listen port (set automatically by most platforms) |

### YouTube blocking cloud IPs

YouTube aggressively blocks requests from data-center IPs. If the deployed API returns errors like `IpBlocked`/`RequestBlocked` while the same request works locally, configure a proxy (see env vars above — Webshare residential proxies are natively supported by youtube-transcript-api and are the documented fix). Free-tier Render also spins the service down after ~15 min idle; the first request afterwards takes up to a minute.

Built with [Flask](https://flask.palletsprojects.com/) and [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api). Transcripts are fetched from YouTube's public endpoints; heavy use from data-center IPs may be rate-limited by YouTube.
