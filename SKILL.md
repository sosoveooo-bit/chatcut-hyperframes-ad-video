---
name: chatcut-hyperframes-ad-video
description: Orchestrate editable ecommerce short-video production by combining ChatCut timelines with HyperFrames motion graphics. Use when Codex needs to make, remix, revise, or review Meta/Facebook/TikTok ads; group source clips coherently; generate Japanese or multilingual ElevenLabs voiceover and captions; add hook, benefit, price, or CTA overlays; sync tagged materials into ChatCut; or preserve an editable ChatCut project while using HyperFrames for polished motion design.
---

# ChatCut HyperFrames Ad Video

Build the main cut in ChatCut and add motion design with HyperFrames without flattening the editable timeline.

## Start Every Task

1. Read `剪辑配置.md` in the active project when it exists. Treat current user instructions as higher priority.
2. Copy `assets/剪辑配置.template.md` into a new project only when no project configuration exists and a persistent default is useful.
3. Read `references/workflow.md` before changing a live timeline.
4. Read `references/chatcut-prompts.md` when operating ChatCut through its built-in agent.
5. Read the installed `hyperframes` entry skill before authoring, editing, or rendering a HyperFrames composition.
6. Read the active browser-control skill before operating ChatCut in a browser.

## Bootstrap the Portable Bundle

1. Run `python scripts/doctor.py` on first use or after moving to another computer.
2. If the report shows missing setup, run the bundled Windows installer:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -StartPanel
   ```

3. Let the setup script create a portable material vault, initialize the local panel, and install the official HyperFrames skills through `npx`.
4. Open `http://127.0.0.1:8794/materials.html` after setup.
5. Keep ChatCut authentication and ElevenLabs credentials in their owning applications or environment. Never write them into this repository or panel data.
6. Read `references/installation.md` for custom paths, prerequisites, and manual recovery.

## Default Production Contract

- Keep the ChatCut timeline editable.
- Use original source clips on the main video track.
- Group several usable moments from one source together before switching sources.
- Use a separate voice track, music track, caption track, and upper motion-graphic track.
- Default to 9:16, 1080×1920, 30 fps, and 20–30 seconds for direct-response ads.
- Default to muted source audio, narration-led mixing, and a clear Japanese female voice when the user provides no other direction.
- Use HyperFrames for the first 0–3 seconds, benefit callouts, offer cards, and the final CTA.
- Do not invent prices, discounts, inventory, guarantees, popularity, or body-effect claims.

## Execute the Workflow

### 1. Inspect Before Editing

- Read the current project duration, aspect ratio, tracks, clips, captions, audio, and existing overlays.
- Preserve confirmed assets, verified asset IDs, and completed tracks. Do not restart material analysis without a concrete conflict.
- Distinguish a material problem from an editing problem.
- Save or duplicate the timeline before destructive changes when the editor supports versions.

### 2. Select and Order Material

- Prefer the bundled panel at `http://127.0.0.1:8794/materials.html` when it is running.
- Import a local or NAS folder into one named product batch, assign roles and tags, and mark only reviewed items `ready`.
- Create one explicit ChatCut sync request for selected items or one product batch; never queue the entire library ambiguously.
- Use `scripts/material_sync.py manifest` to consume the exact queued request before importing assets into ChatCut.
- Assign each usable moment one role: `hook`, `try_on`, `detail`, `motion`, `proof`, `ending`, or `transition`.
- Prefer 6–12 strong moments for a 20–30 second ad.
- Keep 2–5 distinct moments from the same source in one contiguous block.
- Switch sources at story boundaries: hook → product → detail → proof → scene → offer → CTA.
- Avoid default patterns such as `A → B → A → C → A`.
- Match every narration claim to visible evidence.

### 3. Build the ChatCut Base Timeline

- Build the story as: hook → product clarity → detail → proof → use scene → offer → CTA.
- Place original video clips on `V1` and mute them unless a short action sound is intentionally useful.
- Keep visual states around 1.2–2.2 seconds by default, but finish readable actions before cutting.
- Keep the product visible in the first frame and show at least two coherent visual states in the first three seconds.
- Leave the final 2–4 seconds clean enough for an offer and one CTA.

### 4. Add Voice, Captions, and Music

- Generate narration before final caption timing.
- Prefer ElevenLabs multilingual voice synthesis when available; use the user-selected voice and model.
- If ChatCut has no configured ElevenLabs provider, run `scripts/elevenlabs_tts.py` with a user-provided voice ID and import the generated MP3 into `A1`.
- Inspect the generated audio duration before placing it. Never trim a sentence mid-phrase to fit the timeline.
- Shorten the script or regenerate slightly faster when narration exceeds the available duration.
- Generate independent captions from the final voice asset, not from a replaced draft.
- Keep captions above the bottom 15% platform-safe area and clear of faces and garment details.
- Duck music under narration and leave the CTA readable after narration ends.

### 5. Add HyperFrames Motion Graphics

- Run `scripts/create_hyperframes_brief.py` to create a reusable `BRIEF.md`, `STORYBOARD.md`, and `overlay-spec.json` when starting a new enhancement.
- Build a transparent 1080×1920, 30 fps HyperFrames overlay unless the editor requires another format.
- Keep entry motion around 0.2–0.4 seconds, hold important text for at least 1.2 seconds, and avoid meaningless rotation or continuous floating.
- Place the hook overlay at 0–3 seconds and the offer/CTA overlay in the final 2–4 seconds on an upper ChatCut track.
- Remove or hide the old CTA before adding the replacement.
- Prefer importing the rendered transparent overlay into ChatCut when upload works reliably.
- If upload fails after two grounded attempts, recreate the approved HyperFrames design as native editable ChatCut motion graphics. State clearly that this is a native recreation, not an imported HyperFrames render.

### 6. Verify the Finished Cut

- Read the final project structure and confirm the requested duration.
- Confirm the main source track, voice, music, captions, and motion graphics remain separate and editable.
- Inspect representative composed frames in the first second, around the main benefit, and near the final CTA.
- Confirm overlays do not cover faces, collars, buttons, waist details, silhouettes, or the platform-safe area.
- Confirm there is only one CTA and no stale price card underneath it.
- Confirm narration ends naturally and is not clipped.
- Report what was actually imported, recreated, preserved, or replaced.

## Recover From Common Failures

- **ChatCut sign-in required:** stop and ask the user to sign in; never request credentials.
- **Asset ID fails:** use another already verified asset in the same story role and continue.
- **File chooser does not open:** refresh locator ground truth, try the actual file input once, then use the native-motion fallback instead of looping.
- **Voice is too long:** rewrite or regenerate; do not crop speech.
- **Duplicate CTA:** remove the old overlay item before placing the new one.
- **Transparent WebM renders opaque:** verify alpha support and composed frames; use native ChatCut MG if the editor cannot preserve alpha.
- **Timeline duration changes:** trim or move only the newly added overlay unless the user requested a recut.

## Use Bundled Resources

- `references/installation.md`: portable setup, external prerequisites, and secret-handling rules.
- `references/workflow.md`: track contract, timing model, editor handoff, and verification rules.
- `references/chatcut-prompts.md`: reusable prompts for ChatCut's built-in editing agent.
- `assets/剪辑配置.template.md`: sanitized project-level editing defaults.
- `scripts/create_hyperframes_brief.py`: generate a HyperFrames enhancement brief and placement specification.
- `scripts/elevenlabs_tts.py`: generate narration through ElevenLabs using an environment key.
- `scripts/setup.ps1`: initialize the portable vault, local panel, and official HyperFrames dependency.
- `scripts/doctor.py`: report missing runtime dependencies without exposing secret values.
- `scripts/material_sync.py`: claim, manifest, and update queued ChatCut material requests.
- `scripts/self_test.py`: run an isolated end-to-end test of the portable panel and sync queue.
- `panel/`: local-only material tagging and ChatCut sync-request panel.
