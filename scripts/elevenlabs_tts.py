#!/usr/bin/env python3
"""Generate narration through ElevenLabs without storing credentials."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an ElevenLabs narration file.")
    text_group = parser.add_mutually_exclusive_group(required=True)
    text_group.add_argument("--text", help="Narration text.")
    text_group.add_argument("--text-file", help="UTF-8 narration text file.")
    parser.add_argument("--voice-id", required=True, help="ElevenLabs voice ID, not a display name.")
    parser.add_argument("--output", required=True, help="Output MP3 path.")
    parser.add_argument("--model", default="eleven_multilingual_v2")
    parser.add_argument("--stability", type=float, default=0.5)
    parser.add_argument("--similarity-boost", type=float, default=0.75)
    parser.add_argument("--style", type=float, default=0.15)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--base-url", default="https://api.elevenlabs.io")
    return parser.parse_args()


def bounded(name: str, value: float, minimum: float, maximum: float) -> float:
    if not minimum <= value <= maximum:
        raise SystemExit(f"{name} must be between {minimum} and {maximum}")
    return value


def duration_seconds(path: Path) -> float | None:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return round(float(result.stdout.strip()), 3)
    except ValueError:
        return None


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        raise SystemExit("ELEVENLABS_API_KEY is not configured")
    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8").strip()
    if not text or not text.strip():
        raise SystemExit("Narration text is empty")

    payload = {
        "text": text.strip(),
        "model_id": args.model,
        "voice_settings": {
            "stability": bounded("stability", args.stability, 0.0, 1.0),
            "similarity_boost": bounded("similarity-boost", args.similarity_boost, 0.0, 1.0),
            "style": bounded("style", args.style, 0.0, 1.0),
            "speed": bounded("speed", args.speed, 0.7, 1.2),
            "use_speaker_boost": True,
        },
    }
    endpoint = args.base_url.rstrip("/") + "/v1/text-to-speech/" + quote(args.voice_id, safe="")
    request = Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
            "xi-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=120) as response:
            audio = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"ElevenLabs request failed ({error.code}): {detail}") from error
    except URLError as error:
        raise SystemExit(f"ElevenLabs request failed: {error.reason}") from error
    if not audio:
        raise SystemExit("ElevenLabs returned an empty audio file")

    output = Path(args.output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(audio)
    print(
        json.dumps(
            {
                "output": str(output),
                "bytes": len(audio),
                "durationSeconds": duration_seconds(output),
                "model": args.model,
                "voiceId": args.voice_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
