# Portable Installation

## Contents

1. What GitHub can migrate
2. ChatCut-native setup
3. Codex Skill installation
4. Optional local extensions
5. External prerequisites
6. Updating
7. Security boundaries

## 1. What GitHub Can Migrate

The GitHub skill repository contains:

- The complete reusable ChatCut remix workflow
- A paste-ready definition for ChatCut's own saved Skills feature
- Sanitized editing configuration and prompt templates
- HyperFrames brief generation
- Dependency and health checks
- An optional local material panel and sync-request queue
- A setup script for optional HyperFrames and panel use

It does not and must not contain ChatCut accounts, browser sessions, OAuth tokens, API keys, NAS credentials, cloud project database rows, account-specific asset IDs, or user media.

ChatCut projects, uploaded assets, and saved Skills are cloud/account data. Use the same ChatCut account on another computer, or use ChatCut project sharing for another account. GitHub is the portable workflow backup, not a replacement for ChatCut cloud storage.

## 2. ChatCut-native Setup

No local panel is required.

1. Open `https://app.chatcut.io/zh/` and sign in.
2. Open the AI panel in `Agent` mode.
3. Click `Skills` below the AI input.
4. Choose `Save this editing process as a Skill`.
5. Paste the complete contents of `assets/chatcut-direct-remix-skill.txt`.
6. Save it as `FB女装同源连续混剪`.
7. Upload source videos to `My Assets`, select the saved Skill, and ask ChatCut to mix or optimize the current project.

On another computer with the same ChatCut account, sign in and select the saved Skill. For another ChatCut account, invite that account to the project and repeat steps 3–6 using the same GitHub text asset.

## 3. Codex Skill Installation

Install the repository into the Codex skills directory on another Windows computer:

```powershell
git clone https://github.com/sosoveooo-bit/chatcut-hyperframes-ad-video.git "$HOME\.codex\skills\chatcut-hyperframes-ad-video"
```

Restart Codex or begin a new task. The Skill becomes available as `chatcut-hyperframes-ad-video`.

This Codex installation is optional when the user only wants ChatCut's own AI panel. The ChatCut-native saved Skill in section 2 is sufficient for direct web use.

## 4. Optional Local Extensions

Run this only when local/NAS tagging, batch sync, or external HyperFrames rendering is needed:

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

## 5. External Prerequisites

For ChatCut-native web use:

- A modern browser
- A ChatCut account, signed in by the user

For Codex installation and optional local extensions:

- Git
- Python 3.10 or newer
- Node.js and `npx` for HyperFrames
- A browser surface that Codex can control

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

### Optional material panel data

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

## 6. Updating

Update the Codex Skill from its GitHub repository:

```powershell
cd "$HOME\.codex\skills\chatcut-hyperframes-ad-video"
git pull --ff-only
```

Rerun the optional local setup only when those extensions are used:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -StartPanel
```

The setup preserves existing material data and refreshes only missing structure and dependencies.

## 7. Security Boundaries

- Keep ChatCut OAuth inside the ChatCut connector or browser session.
- Keep ElevenLabs keys in the environment or ChatCut integration.
- Keep NAS authentication in the operating system.
- Use ChatCut account login or project sharing to move cloud projects between computers.
- Do not copy official ChatCut plugin source or bundled vendor Skills into this repository; install the official plugin on each computer.
- Never commit material data, generated auth files, browser cookies, short-lived upload tokens, or `.env` files.
- Treat the panel as a local workstation tool, not an internet-facing service.
