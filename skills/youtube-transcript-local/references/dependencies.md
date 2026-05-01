# Dependencies

## Required binaries
- `python3`
- `yt-dlp`
- `ffmpeg`

## Required Python packages
- `faster-whisper`

## Bootstrap behavior

`bootstrap.sh` attempts the following, in order:

1. Reuse an already installed command when found.
2. Install missing Python packages through `python3 -m pip install`.
3. Install missing `yt-dlp` through `python3 -m pip install yt-dlp` when the standalone binary is absent.
4. Try to install `ffmpeg` through an available package manager:
   - Homebrew: `brew install ffmpeg`
   - apt-get: `sudo apt-get update && sudo apt-get install -y ffmpeg`
   - dnf: `sudo dnf install -y ffmpeg`
5. If no supported installer is available, fail explicitly and print the missing dependency.

## Runtime policy

- Default device is CPU.
- If `nvidia-smi` is present, runtime switches to CUDA with `float16`.
- No cloud ASR fallback is allowed.
