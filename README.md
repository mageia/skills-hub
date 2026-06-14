# Skills Hub

This repository hosts installable agent skills.

## Waninter Creative

Waninter Creative is a Codex/Agent skill for generating images and videos through the Waninter Creative API.

It supports:

- API Key setup through a local config file
- Text-to-image generation
- Image editing / image-to-image requests
- Text-to-video generation
- Image-to-video generation
- Async task polling
- Local output saving and JSON metadata

Skill path in this repository:

```text
skills/waninter-creative
```

---

## For beginner users

If you do not know how to install the skill yourself, copy this README link and send it to your Agent/Codex with this message:

```text
Please read this README, install the Waninter Creative skill from this GitHub repository, and help me initialize the API Key configuration.
```

The Agent should then follow the installation instructions below.

---

## Agent installation instructions

Install the skill into the user's Codex skills directory.

### 1. Clone the repository

```bash
git clone https://github.com/mageia/skills-hub.git /tmp/skills-hub
```

If the repository already exists locally, pull the latest version instead.

### 2. Copy the skill

```bash
mkdir -p ~/.codex/skills
rm -rf ~/.codex/skills/waninter-creative
cp -R /tmp/skills-hub/skills/waninter-creative ~/.codex/skills/waninter-creative
```

### 3. Initialize API Key config

Run:

```bash
python3 ~/.codex/skills/waninter-creative/scripts/configure_api_key.py
```

Ask the user to paste their Waninter Creative API Key when prompted.

For most users, leave the following prompts unchanged by pressing Enter:

```text
Base URL [https://creative-studio.waninter.com]:
Default image model [wan-image]:
Default video model [wan-video]:
Image generation path [/v1/images/generations]:
Image edit path [/v1/images/edits]:
Video generation path [/v1/videos/generations]:
Task status path [/v1/tasks/{task_id}]:
```

The config file is saved at:

```text
~/.config/waninter-creative/config.json
```

The script sets file permissions to `600`.

Do not print or expose the user's API Key.

---

## Quick test

After setup, test image generation:

```bash
python3 ~/.codex/skills/waninter-creative/scripts/generate_image.py \
  --prompt "A cinematic sci-fi city poster at sunset" \
  --aspect-ratio 16:9
```

Test video generation:

```bash
python3 ~/.codex/skills/waninter-creative/scripts/generate_video.py \
  --prompt "A futuristic city at night, slow cinematic camera movement" \
  --duration 5 \
  --aspect-ratio 16:9
```

Generated outputs are saved under:

```text
./outputs/waninter-creative/YYYYMMDD-HHMMSS/
```

---

## One-command install for Agents

Agents may use this command when appropriate:

```bash
set -euo pipefail
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
git clone https://github.com/mageia/skills-hub.git "$TMP_DIR/skills-hub"
mkdir -p "$HOME/.codex/skills"
rm -rf "$HOME/.codex/skills/waninter-creative"
cp -R "$TMP_DIR/skills-hub/skills/waninter-creative" "$HOME/.codex/skills/waninter-creative"
python3 "$HOME/.codex/skills/waninter-creative/scripts/configure_api_key.py"
```

This command installs the skill and starts interactive API Key configuration.

---

## Security notes

- API Keys are stored only in `~/.config/waninter-creative/config.json`.
- Do not commit API Keys to Git.
- Do not paste API Keys into public chats or issue trackers.
- Do not print API Keys in logs or generated metadata.
