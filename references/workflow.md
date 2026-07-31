# ChatCut × HyperFrames Workflow

## Contents

1. Ownership split
2. Panel-to-ChatCut sync
3. Default timeline contract
4. Timing model
5. HyperFrames handoff
6. Upload fallback
7. Verification contract

## 1. Ownership Split

Use ChatCut for:

- Original media import and source trimming
- Source-contiguous clip ordering
- Narration, captions, music, and basic speed changes
- The editable project of record

Use HyperFrames for:

- The 0–3 second hook
- Short benefit emphasis cards
- Price, offer, color, guarantee, or scarcity cards backed by confirmed facts
- The final CTA

Never replace the complete ChatCut timeline with one flattened HyperFrames render.

## 2. Panel-to-ChatCut Sync

1. Import one local or NAS folder into a named product batch in the bundled panel.
2. Assign roles and tags, then mark reviewed items `ready`.
3. Queue selected items or one explicit batch with a ChatCut project URL and product key.
4. Read the next request:

   ```powershell
   python scripts/material_sync.py next
   ```

5. Claim it before upload and generate an exact manifest:

   ```powershell
   python scripts/material_sync.py claim --request-id REQUEST_ID
   python scripts/material_sync.py manifest --request-id REQUEST_ID --output .\manifest.json
   ```

6. Verify the requested project through the ChatCut connector when available.
7. Create one ChatCut import session and upload every readable manifest path once. Do not store OAuth or short-lived upload tokens in the panel.
8. Write per-item results back:

   ```powershell
   python scripts/material_sync.py mark --request-id REQUEST_ID --updates-file .\updates.json
   ```

9. Keep failed items retryable and preserve fingerprints to prevent duplicate project imports.
10. Syncing assets does not replace or recut the existing timeline unless the user explicitly asks for a remix.

## 3. Default Timeline Contract

| Track | Purpose | Rule |
| --- | --- | --- |
| `V3 HF_Hook_CTA` | Hook and CTA motion graphics | Transparent overlay or native recreation |
| `V2 Overlay` | Optional secondary overlay | Leave empty after replacing a stale CTA |
| `V1 Main` | Original source video | Keep editable; mute by default |
| `A1 VO` | Final narration | Complete sentences; no end truncation |
| `A2 BGM` | Music bed | Duck under VO; fade near the end |
| Captions | Final narration captions | Regenerate after voice replacement |

Track names may differ. Preserve their functional separation.

## 4. Timing Model

For a 20–30 second direct-response video:

| Time | Function | Visual requirement |
| --- | --- | --- |
| `0–3s` | Hook | Product visible immediately; two coherent visual states |
| `3–8s` | Product/detail | Full product, then one or two close details |
| `8–15s` | Fit/proof | Front, side, back, movement, or construction proof |
| `15–21s` | Motion/use | Walking, turning, styling, or real use scene |
| `21–25s` | Options/summary | Colors, styling range, or clean product summary |
| Final `2–4s` | Offer/CTA | Confirmed offer plus one explicit action |

Adapt the boundaries to narration and available evidence. Preserve story order rather than forcing exact seconds.

## 5. HyperFrames Handoff

1. Generate the enhancement brief:

   ```powershell
   python scripts/create_hyperframes_brief.py `
     --output-dir .\hyperframes-enhancement `
     --product "商品名" `
     --price "6,580円" `
     --color "ダークブルー" `
     --color "ベージュ" `
     --hook-line "シャツのきちんと感" `
     --hook-line "ロングワンピのラクさ" `
     --hook-line "1枚で叶う" `
     --cta "今すぐチェック →"
   ```

2. Build and validate the HyperFrames composition.
3. Render a six-second transparent overlay by default:
   - Source `0–3s`: opening hook
   - Source `3–6s`: final CTA
4. Import the overlay once into ChatCut.
5. Place source `0–3s` at timeline `0–3s`.
6. Place source `3–6s` in the final three seconds.
7. Remove the previous CTA item.

Use separate assets instead of one six-second overlay when the editor cannot reuse source ranges cleanly.

## 6. Upload Fallback

Prefer this order:

1. ChatCut connector or asset-import helper, when available
2. Browser file chooser through the real file input
3. One grounded retry through the visible upload control
4. Native ChatCut motion-graphic recreation using the approved HyperFrames layout

Do not repeatedly click a broken upload control. Do not claim that HyperFrames was imported when only a native recreation was added.

For the native fallback:

- Create one upper track named `HF_Hook_CTA`.
- Recreate the same copy, colors, typography, placement, and timing.
- Keep the background transparent.
- Use Noto Sans JP for Japanese when available.
- Emphasize one phrase or price with warm yellow; keep supporting text white.
- Keep the bottom 15% clear.

## 7. Verification Contract

Verify structure:

- Requested total duration remains unchanged.
- Main video, voice, music, captions, and overlays are separate.
- The old CTA no longer overlaps the replacement.
- Voice duration fits without truncation.

Verify frames:

- Inspect about `0.5s` for the hook.
- Inspect one mid-video proof frame.
- Inspect about `0.7s` before the end for CTA readability.
- Confirm the product and person remain legible behind transparent graphics.

Verify claims:

- Price, colors, discount, stock, trial, and guarantee match user-confirmed facts or the current landing page.
- Remove unsupported slimming numbers, body shaming, exaggerated before/after language, and false scarcity.
