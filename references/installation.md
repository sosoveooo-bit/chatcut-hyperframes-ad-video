# Portable Installation

## Contents

1. What the bundle installs
2. One-click Windows setup
3. External prerequisites
4. Material panel data
5. Updating
6. Security boundaries

## 1. What the Bundle Installs

The GitHub skill repository contains:

- The ChatCut × HyperFrames editing skill
- A local material tagging panel
- A ChatCut sync-request queue and manifest tool
- HyperFrames brief generation
- Dependency and health checks
- A setup script that installs the official HyperFrames skills through `npx`

It does not contain accounts, browser sessions, OAuth tokens, API keys, NAS credentials, or user media.

## 2. One-click Windows Setup

After installing the skill, run from the skill directory:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -StartPanel
```

Optional parameters:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 `
  -MaterialRoot "D:\VideoMaterials" `
  -ConfigDirectory "$HOME\.codex\chatcut-hyperframes" `
  -Port 8794 `
  -HyperFramesTimeoutSeconds 300 `
  -StartPanel
```

Use `-SkipHyperFrames` when HyperFrames is already installed. Use `-CheckOnly` for a read-only diagnosis.

The setup writes only non-secret local settings to:

```text
%USERPROFILE%\.codex\chatcut-hyperframes\config.json
```

## 3. External Prerequisites

Required:

- Python 3.10 or newer
- Node.js and `npx` for HyperFrames
- A browser surface that Codex can control
- A ChatCut account, signed in by the user

Recommended:

- FFmpeg and ffprobe for media inspection
- ElevenLabs configured in ChatCut or `ELEVENLABS_API_KEY` in the user's environment

When using the bundled direct adapter, pass an ElevenLabs voice ID rather than a display name:

```powershell
$env:ELEVENLABS_API_KEY = "set-this-outside-the-repository"
python scripts/elevenlabs_tts.py `
  --text-file .\narration-ja.txt `
  --voice-id "YOUR_VOICE_ID" `
  --model eleven_multilingual_v2 `
  --output .\narration-ja.mp3
```

The setup script can install HyperFrames skills but cannot create accounts, accept terms, sign in, solve CAPTCHA, or create API credentials.

## 4. Material Panel Data

The portable material root contains:

```text
data/material-library.json
data/chatcut-sync.json
analysis/
batches/
uploads/
system/
```

The panel stores source file paths and fingerprints. It does not copy source videos unless another tool explicitly does so.

Start the panel manually:

```powershell
python -B panel/server.py --host 127.0.0.1 --port 8794 --material-root "D:\VideoMaterials"
```

Do not bind the panel to a non-loopback address unless a separate authenticated reverse proxy protects it.

## 5. Updating

Update the skill from its GitHub repository, then rerun:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -StartPanel
```

The setup preserves existing material data and refreshes only missing structure and dependencies.

## 6. Security Boundaries

- Keep ChatCut OAuth inside the ChatCut connector or browser session.
- Keep ElevenLabs keys in the environment or ChatCut integration.
- Keep NAS authentication in the operating system.
- Never commit material data, generated auth files, browser cookies, short-lived upload tokens, or `.env` files.
- Treat the panel as a local workstation tool, not an internet-facing service.
