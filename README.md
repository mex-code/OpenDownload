# All-in-One Downloader

A single-file, cross-platform command-line tool for downloading YouTube videos/audio and TikTok videos/music, built on top of [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [requests](https://github.com/psf/requests).

## What it does

- Downloads YouTube videos at a chosen quality (144p–1080p)
- Downloads YouTube audio, converted to MP3 when FFmpeg is available
- Downloads TikTok videos in the best available quality (HD when the API provides it)
- Downloads the original TikTok background music track when available
- Automatically expands shortened TikTok links (e.g. `vm.tiktok.com`)
- Validates URLs before attempting any download
- Creates organized output folders automatically
- Sanitizes filenames using the media title/author so files are named sensibly
- Checks and reports installed dependency versions from the CLI menu
- Offers a guided, one-step dependency install without touching your system silently

## Supported platforms

| Platform | Status | Notes |
|---|---|---|
| Windows | Full support | Requires Python 3.9+ |
| macOS | Full support | Requires Python 3.9+ |
| Linux | Full support | Requires Python 3.9+ |
| Android (Termux) | Full support | Auto-detects `~/storage/shared/Downloads`; run `termux-setup-storage` first |
| iOS (Pythonista / a-Shell / Pyto) | Best-effort | Networking and filesystem access depend on the app; some apps sandbox file access and disable subprocess calls |

The script never hardcodes an OS-specific path. It uses `pathlib.Path.home()` and falls back sensibly:

1. If the `DOWNLOADER_OUTPUT_DIR` environment variable is set, that path is used.
2. If an Android/Termux shared storage folder is detected, downloads go there.
3. Otherwise, files are saved under the user's `~/Downloads` folder.

## Installation

```bash
git clone https://github.com/your-username/all-in-one-downloader.git
cd all-in-one-downloader
python3 -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On Android (Termux):

```bash
pkg install python ffmpeg
termux-setup-storage
pip install -r requirements.txt
```

If you skip installing dependencies up front, the program will detect what is missing on startup and let you install it from the in-app menu (option 5) instead of installing anything silently in the background.

## Usage

```bash
python3 downloader.py
```

You will see a menu:

```
=== All-in-One Downloader ===
1. YouTube video
2. YouTube audio
3. TikTok video
4. Check dependencies
5. Install missing dependencies
6. Exit
```

Example: downloading a YouTube video

```
Choose an option (1-6): 1
Paste YouTube URL: https://www.youtube.com/watch?v=example

=== Video Info ===
Title    : Example Video
Channel  : Example Channel
Duration : 0:03:21

Available Quality:
1. 144p
2. 240p
3. 360p
4. 480p
5. 720p
6. 1080p

Choose quality: 5
```

Example: downloading a TikTok video

```
Choose an option (1-6): 3
Paste TikTok URL: https://vm.tiktok.com/example/
```

Files are saved under:

```
<Downloads root>/YouTube/Video/
<Downloads root>/YouTube/Audio/
<Downloads root>/TikTok/Video/
<Downloads root>/TikTok/Music/
```

## Dependency notes

Required packages (in `requirements.txt`):

- `yt-dlp` — powers all YouTube downloads
- `requests` — powers TikTok link resolution and file downloads

The app checks these on startup and prints installed versions. If something required is missing, downloads that need it are disabled until you install it — nothing is installed automatically without your action. Use menu option 5, or run manually:

```bash
pip install -r requirements.txt
```

## FFmpeg notes

FFmpeg is optional but recommended:

- If FFmpeg is detected on your system `PATH`, it is used automatically to merge high-quality video+audio streams into MP4 and to convert audio downloads to MP3.
- If FFmpeg is **not** found, the tool still works: video downloads fall back to a pre-merged format when available, and audio downloads are saved in their original container (e.g. `.m4a`) instead of being converted to MP3.

Install FFmpeg:

- **Windows**: `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` (or your distro's package manager)
- **Termux**: `pkg install ffmpeg`

## Legal notice

This tool is provided for downloading content you own, have created, or have explicit permission or rights to download (for example, content under a license that permits it, or your own uploads). Downloading copyrighted content without authorization from its rightsholder may violate the terms of service of YouTube, TikTok, or applicable copyright law in your jurisdiction. You are solely responsible for how you use this tool.
