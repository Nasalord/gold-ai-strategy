from __future__ import annotations

import json
import subprocess
from pathlib import Path

VIDEO_ID = "wzUk3gBabvQ"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
OUT = Path("ai8_video_recovery")
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
results.append(
    run(
        ["yt-dlp", "--skip-download", "--dump-single-json", VIDEO_URL],
        "yt_dlp_metadata",
    )
)
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
            str(OUT / "ai8_video"),
            VIDEO_URL,
        ],
        "yt_dlp_subtitles",
    )
)

try:
    from youtube_transcript_api import YouTubeTranscriptApi

    try:
        transcript = YouTubeTranscriptApi().fetch(VIDEO_ID, languages=["en"])
        snippets = [
            {"text": x.text, "start": x.start, "duration": x.duration}
            for x in transcript
        ]
        result = {"name": "youtube_transcript_api", "ok": True, "snippets": snippets}
    except Exception as exc:  # noqa: BLE001 - diagnostic artifact
        result = {"name": "youtube_transcript_api", "ok": False, "error": repr(exc)}
except Exception as exc:  # noqa: BLE001
    result = {"name": "youtube_transcript_api_import", "ok": False, "error": repr(exc)}

(OUT / "youtube_transcript_api.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
results.append(result)
(OUT / "recovery_summary.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
