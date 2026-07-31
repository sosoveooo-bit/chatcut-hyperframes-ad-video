#!/usr/bin/env python3
"""Check portable ChatCut × HyperFrames bundle prerequisites."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check bundle dependencies and local panel health.")
    parser.add_argument("--material-root", help="Portable material root to verify.")
    parser.add_argument("--panel-url", default="http://127.0.0.1:8794", help="Local panel base URL.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def load_local_config() -> dict:
    config_path = Path.home() / ".codex" / "chatcut-hyperframes" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def panel_health(panel_url: str) -> tuple[bool, str]:
    try:
        with urlopen(panel_url.rstrip("/") + "/healthz", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return bool(payload.get("ok")), str(payload.get("materialRoot") or "")
    except (OSError, URLError, json.JSONDecodeError, ValueError):
        return False, ""


def main() -> int:
    args = parse_args()
    config = load_local_config()
    material_root_text = args.material_root or config.get("materialRoot") or ""
    material_root = Path(material_root_text).expanduser() if material_root_text else None
    panel_ok, panel_root = panel_health(args.panel_url)

    checks = {
        "python": {
            "ok": sys.version_info >= (3, 10),
            "detail": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        },
        "node": {"ok": shutil.which("node") is not None, "detail": shutil.which("node") or "missing"},
        "npx": {"ok": shutil.which("npx") is not None, "detail": shutil.which("npx") or "missing"},
        "ffmpeg": {
            "ok": shutil.which("ffmpeg") is not None,
            "detail": shutil.which("ffmpeg") or "optional; missing",
            "required": False,
        },
        "materialRoot": {
            "ok": bool(material_root and material_root.exists()),
            "detail": str(material_root) if material_root else "not configured",
        },
        "panel": {"ok": panel_ok, "detail": panel_root or "not running"},
        "elevenLabs": {
            "ok": bool(os.environ.get("ELEVENLABS_API_KEY")),
            "detail": "configured" if os.environ.get("ELEVENLABS_API_KEY") else "optional; configure in ChatCut or environment",
            "required": False,
        },
    }
    required_ok = all(item["ok"] for item in checks.values() if item.get("required", True))
    result = {"ok": required_ok, "checks": checks}

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for name, item in checks.items():
            marker = "OK" if item["ok"] else ("OPTIONAL" if not item.get("required", True) else "MISSING")
            print(f"[{marker}] {name}: {item['detail']}")
        print("Bundle ready" if required_ok else "Run scripts/setup.ps1 to finish setup")
    return 0 if required_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
