from __future__ import annotations

import json
import subprocess
from pathlib import Path

VIDEO_URL = "https://www.youtube.com/watch?v=J8a8wlewhTk"
OUT = Path("ai58_video_recovery")
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], name: str) -> dict[str, object]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    result = {
        "name": name,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    (OUT / f"{name}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


results: list[dict[str, object]] = []

# yt-dlp can recover the public title/description and, when YouTube permits it,
# subtitle-track metadata. Do not download the video itself.
results.append(
    run(
        [
            "yt-dlp",
            "--skip-download",
            "--dump-single-json",
            VIDEO_URL,
        ],
        "yt_dlp_metadata",
    )
)

# Try official/auto English subtitles. Failure is recorded rather than hidden.
results.append(
    run(
        [
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            "en,en-US,en-GB,en.*",
            "--sub-format",
            "vtt",
            "-o",
            str(OUT / "ai58_video"),
            VIDEO_URL,
        ],
        "yt_dlp_subtitles",
    )
)

# Second independent transcript path.
try:
    from youtube_transcript_api import YouTubeTranscriptApi

    transcript_result: dict[str, object]
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch("J8a8wlewhTk", languages=["en"])
        snippets = [
            {"text": x.text, "start": x.start, "duration": x.duration}
            for x in transcript
        ]
        transcript_result = {"ok": True, "snippets": snippets}
    except Exception as exc:  # noqa: BLE001 - diagnostic artifact
        transcript_result = {"ok": False, "error": repr(exc)}
    (OUT / "youtube_transcript_api.json").write_text(
        json.dumps(transcript_result, indent=2), encoding="utf-8"
    )
    results.append({"name": "youtube_transcript_api", **transcript_result})
except Exception as exc:  # noqa: BLE001
    results.append({"name": "youtube_transcript_api_import", "ok": False, "error": repr(exc)})

(OUT / "recovery_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
