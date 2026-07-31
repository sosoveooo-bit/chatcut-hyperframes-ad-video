#!/usr/bin/env python3
"""Generate reusable HyperFrames hook and CTA planning artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create BRIEF.md, STORYBOARD.md, and overlay-spec.json for a ChatCut enhancement."
    )
    parser.add_argument("--output-dir", required=True, help="Directory for generated artifacts.")
    parser.add_argument("--product", required=True, help="Product name shown in the brief.")
    parser.add_argument("--price", required=True, help="Confirmed display price, including currency.")
    parser.add_argument(
        "--color", action="append", default=[], help="Confirmed color name. Repeat for multiple colors."
    )
    parser.add_argument(
        "--hook-line", action="append", default=[], help="Hook line. Repeat for up to three lines."
    )
    parser.add_argument("--cta", default="今すぐチェック →", help="Final call to action.")
    parser.add_argument("--duration", type=float, default=28.0, help="Total ad duration in seconds.")
    parser.add_argument("--fps", type=int, default=30, help="Timeline frame rate.")
    parser.add_argument("--width", type=int, default=1080, help="Output width.")
    parser.add_argument("--height", type=int, default=1920, help="Output height.")
    parser.add_argument("--platform", default="Meta/Facebook", help="Target advertising platform.")
    parser.add_argument("--language", default="ja-JP", help="Primary copy language.")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.duration < 10:
        raise SystemExit("--duration must be at least 10 seconds")
    if args.fps <= 0 or args.width <= 0 or args.height <= 0:
        raise SystemExit("--fps, --width, and --height must be positive")
    if len(args.hook_line) > 3:
        raise SystemExit("Use no more than three --hook-line values")


def resolved_hook_lines(args: argparse.Namespace) -> list[str]:
    if args.hook_line:
        return args.hook_line
    return [args.product, "ディテールまできれい", "1枚でスタイリング"]


def render_brief(args: argparse.Namespace, hook_lines: list[str], cta_start: float) -> str:
    colors = " / ".join(args.color) if args.color else "ユーザー確認済みのカラー"
    hooks = "\n".join(f"- {line}" for line in hook_lines)
    return f"""# HyperFrames Enhancement Brief

## Deliverable

- Product: {args.product}
- Platform: {args.platform}
- Language: {args.language}
- Main timeline: {args.duration:g}s at {args.fps}fps
- Canvas: {args.width}×{args.height}, 9:16
- Output: transparent motion-graphic overlay for an editable ChatCut project

## Ownership

- ChatCut owns original footage, voiceover, captions, music, and the editable main timeline.
- HyperFrames owns the opening hook and final CTA only.
- Do not flatten or replace the complete ChatCut timeline.

## Hook Copy — 0–3s

{hooks}

Use a 0.2–0.4s entry, keep product-critical areas visible, and emphasize only one phrase.

## CTA Copy — {cta_start:g}–{args.duration:g}s

- Price: {args.price}
- Colors: {colors}
- CTA: {args.cta}

Hold the final CTA for at least 1.5s. Treat all commercial facts as user-confirmed inputs.

## Visual Direction

- Use Noto Sans JP or a compatible Japanese sans-serif.
- Use white supporting text, a deep navy translucent panel, and warm yellow emphasis.
- Keep the bottom 15% clear for platform UI.
- Avoid continuous floating, decorative rotation, and full-frame opaque cards.
"""


def render_storyboard(args: argparse.Namespace, hook_lines: list[str], cta_start: float) -> str:
    hook_rows = []
    line_duration = 3.0 / len(hook_lines)
    for index, line in enumerate(hook_lines):
        start = index * line_duration
        end = (index + 1) * line_duration
        hook_rows.append(f"| {start:.2f}–{end:.2f}s | Hook line {index + 1} | {line} |")
    hook_table = "\n".join(hook_rows)
    return f"""# Storyboard

| Time | Layer | Copy / action |
| --- | --- | --- |
{hook_table}
| 3.00–{cta_start:.2f}s | ChatCut base timeline | No HyperFrames overlay required by default |
| {cta_start:.2f}–{args.duration:.2f}s | CTA | {args.price} / {args.cta} |

Render the hook and CTA as transparent overlays. Verify a composed frame near 0.5s and another 0.7s before the end.
"""


def main() -> None:
    args = parse_args()
    validate_args(args)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    hook_lines = resolved_hook_lines(args)
    cta_duration = 3.0
    cta_start = args.duration - cta_duration

    brief_path = output_dir / "BRIEF.md"
    storyboard_path = output_dir / "STORYBOARD.md"
    spec_path = output_dir / "overlay-spec.json"

    brief_path.write_text(render_brief(args, hook_lines, cta_start), encoding="utf-8")
    storyboard_path.write_text(render_storyboard(args, hook_lines, cta_start), encoding="utf-8")

    overlay_spec = {
        "canvas": {"width": args.width, "height": args.height, "fps": args.fps},
        "timelineDurationSeconds": args.duration,
        "renderDurationSeconds": 6,
        "segments": [
            {
                "name": "hook",
                "sourceStartSeconds": 0,
                "timelineStartSeconds": 0,
                "durationSeconds": 3,
                "copy": hook_lines,
            },
            {
                "name": "cta",
                "sourceStartSeconds": 3,
                "timelineStartSeconds": cta_start,
                "durationSeconds": 3,
                "price": args.price,
                "colors": args.color,
                "cta": args.cta,
            },
        ],
    }
    spec_path.write_text(
        json.dumps(overlay_spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(brief_path)
    print(storyboard_path)
    print(spec_path)


if __name__ == "__main__":
    main()
