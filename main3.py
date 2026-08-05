from __future__ import annotations

__INFO__ = {
   'Made_By_Mex': ':3'
}

import importlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote, urlparse

import ctypes

def _supports_color():
    if not sys.stdout.isatty():
        return False
    if os.name == 'nt':
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                return False
            if mode.value & 0x4:
                return True
            if not kernel32.SetConsoleMode(handle, mode.value | 0x4):
                return False
            return True
        except Exception:
            return False
    else:
        term = os.environ.get('TERM', '')
        if term == 'dumb':
            return False
        return True

def _char_density(c: str) -> int:
    code = ord(c)
    if 0x2800 <= code <= 0x28FF:
        bits = code - 0x2800
        try:
            return bits.bit_count()
        except AttributeError:
            return bin(bits).count('1')
    block_density = {
        0x2588: 8,
        0x2584: 4,
        0x2580: 4,
        0x258C: 4,
        0x2590: 4,
        0x2593: 6,
        0x2592: 4,
        0x2591: 2,
    }
    if code in block_density:
        return block_density[code]
    if c == ' ':
        return 0
    return 4

def _color_for_density(density: int) -> str:
    # density 0 → dark gray (232), density 8 → white (255)
    n = 232 + int(density * 23 / 8)
    return f"\033[38;5;{n}m"

def colored_banner(banner_text: str) -> str:
    if not _supports_color():
        return banner_text
    colored = []
    for ch in banner_text:
        if ch == '\n':
            colored.append(ch)
        else:
            density = _char_density(ch)
            colored.append(_color_for_density(density) + ch)
    colored.append("\033[0m")
    return ''.join(colored)

REQUIRED_PACKAGES = {
    "yt_dlp": "yt-dlp",
    "requests": "requests",
}

INVALID_FILENAME_CHARS = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]

QUALITY_MAP = {
    "1": "144",
    "2": "240",
    "3": "360",
    "4": "480",
    "5": "720",
    "6": "1080",
}

QUALITY_LABELS = ["144p", "240p", "360p", "480p", "720p", "1080p"]

FPS_PREDEFINED = [30, 60, 120, 144, 240]

TIKWM_API = "https://www.tikwm.com/api/?url={}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

banner = """
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠖⠃⠀⠀⠀⡁⠀⠀⠀⠀⠀⠐⠆⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⢔⡤⠊⠁⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠁⠀⠀⠘⠁⢀⠀⠀⠀⠀⢈⠓⠂⠠⡄⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣶⠿⠞⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠒⠁⠀⠠⡚⠁⢀⣙⣀⣈⡩⠬⢁⠀⢑⠶⠤⡆⠤⡀⠀⠀⠀⠀⠀⠀⢀⠴⢲⣋⣽⣷⠟⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⢠⠀⠀⣶⠃⠗⣡⣶⣮⣿⡿⠿⠿⢿⣿⣷⣶⣤⣤⠤⠴⠦⠬⣤⣤⠄⣉⠉⠝⢲⣿⡷⠻⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠁⡀⡸⠁⣰⣿⡿⠛⠋⣁⡀⠤⠤⢄⡀⠈⠛⢯⣿⣟⣾⣶⣶⣮⣭⣵⣾⣿⣟⠿⠉⢨⠖⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠀⢠⠳⡧⣻⡿⠋⢀⠒⠉⠀⠀⠀⠀⠀⠀⠉⠢⠀⠀⠙⠛⣻⣿⣿⣿⢿⣿⣿⠟⡱⠖⠊⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⢠⣧⠓⣾⣿⠁⠀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢦⣠⣾⣿⠿⣿⣿⣿⡿⣫⠏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠂⢃⣸⣿⠇⢠⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣴⣿⠟⢿⠁⠸⡿⣿⣯⡶⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⢘⡄⠘⣿⣿⠀⠸⡀⠀⠀⠀⠀⠀⢀⣀⣴⣾⣿⡿⡟⡋⠐⡇⠀⢸⣿⣿⠃⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢡⠘⢰⣿⡿⡆⠀⣇⠀⣀⣠⣤⣶⣿⢷⢟⠻⠀⠈⠀⠀⠀⡇⠀⣼⣿⣿⠂⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠔⢀⡴⢯⣾⠟⡏⢀⣠⣿⣿⣿⣟⢟⡋⠅⠘⠉⠀⠀⠀⠀⢀⠀⠁⢠⣿⣟⠃⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠞⣻⣷⡿⢙⣩⣶⡿⠿⠛⠉⠑⢡⡁⠀⠀⠀⠀⠀⠀⢀⠔⠁⠀⣰⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣡⣾⣥⣾⢫⡦⠾⠛⠙⠉⠀⠀⢀⣀⠀⠈⠙⠓⠦⠤⠤⠀⠘⠁⢀⡤⣾⡿⠏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠔⣴⣾⣿⣿⢟⢝⠢⠃⢀⣤⢴⣾⣮⣷⣶⢿⣶⡤⣐⡀⠀⣠⣤⢶⣪⣿⣿⡿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⡀⣦⣾⡿⡛⠵⠺⢈⡠⠶⠿⠥⠥⡭⠉⠉⢱⡛⠻⠿⣿⣿⣿⣿⣿⠿⠿⠿⠟⠭⠛⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢀⢴⠕⣋⠝⠕⠐⠀⠔⠉⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠁⠉⠁⠁⠁⠁⠈⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢀⣠⠁⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
NETWORK_TIMEOUT = 20
DOWNLOAD_TIMEOUT = 60

_FPS_CUSTOM = object()


@dataclass
class DependencyStatus:
    name: str
    package: str
    installed: bool
    version: str | None


def get_dependency_status() -> list[DependencyStatus]:
    statuses = []
    for module_name, package_name in REQUIRED_PACKAGES.items():
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            try:
                module = importlib.import_module(module_name)
                version = getattr(module, "__version__", "unknown")
                statuses.append(DependencyStatus(module_name, package_name, True, version))
            except ImportError:
                statuses.append(DependencyStatus(module_name, package_name, False, None))
        else:
            statuses.append(DependencyStatus(module_name, package_name, False, None))
    return statuses


def print_dependency_status() -> bool:
    statuses = get_dependency_status()
    print("\n=== Dependency Check ===")
    all_ok = True
    for status in statuses:
        if status.installed:
            print(f"  [OK] {status.package} ({status.version})")
        else:
            print(f"  [MISSING] {status.package}")
            all_ok = False

    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"  [OK] ffmpeg ({ffmpeg_path})")
    else:
        print("  [OPTIONAL MISSING] ffmpeg - audio conversion and video merging will be limited")

    return all_ok


def is_package_installed(module_name: str) -> bool:
    return any(
        s.installed for s in get_dependency_status() if s.name == module_name
    )


def install_missing_dependencies() -> None:
    statuses = get_dependency_status()
    missing = [status.package for status in statuses if not status.installed]
    if not missing:
        print("\nAll required dependencies are already installed.")
        return

    print(f"\nInstalling missing packages: {', '.join(missing)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("Installation complete. Please restart the program.")
    except subprocess.CalledProcessError as error:
        print(f"Installation failed: {error}")
    except FileNotFoundError:
        print("Installation failed: pip was not found for this Python interpreter.")


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def get_downloads_root() -> Path:
    env_override = os.environ.get("DOWNLOADER_OUTPUT_DIR")
    if env_override:
        return Path(env_override).expanduser()

    android_storage = Path.home() / "storage" / "shared" / "Downloads"
    if android_storage.exists():
        return android_storage

    return Path.home() / "Downloads"


def ensure_directory(path: Path) -> Path:
    try:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"[+] Created directory: {path}")
        else:
            print(f"[+] Using existing directory: {path}")
    except PermissionError as e:
        print(f"[-] Permission denied creating directory {path}: {e}")
        raise
    return path


def sanitize_filename(name: str, max_length: int = 80) -> str:
    cleaned = name
    for char in INVALID_FILENAME_CHARS:
        cleaned = cleaned.replace(char, "_")
    cleaned = "".join(char for char in cleaned if char.isprintable())
    cleaned = cleaned.strip().strip(".").lstrip(".")
    cleaned = cleaned.replace("..", "_")
    return cleaned[:max_length] if cleaned else "untitled"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def is_valid_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "N/A"
    try:
        secs = int(seconds)
        if secs < 0:
            return "N/A"
        return str(timedelta(seconds=secs))
    except (TypeError, ValueError):
        return "N/A"


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    try:
        input("\nPress Enter to continue...")
    except (EOFError, KeyboardInterrupt):
        pass


def print_progress(percent: float, downloaded_mb: float, total_mb: float) -> None:
    print(
        f"\r[+] Progress: {percent:.1f}% ({downloaded_mb:.2f}MB / {total_mb:.2f}MB)",
        end="",
        flush=True,
    )


def youtube_progress_hook(status: dict) -> None:
    if status.get("status") == "downloading":
        percent = status.get("_percent_str", "?").strip()
        speed = status.get("_speed_str", "N/A").strip()
        eta = status.get("_eta_str", "N/A").strip()
        print(f"\r[+] {percent} | Speed: {speed} | ETA: {eta}", end="", flush=True)
    elif status.get("status") == "finished":
        print("\n[+] Download complete, processing file...")
    elif status.get("status") == "error":
        print("\n[-] An error occurred during download.")


def fetch_youtube_info(url: str) -> dict:
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "socket_timeout": 30, "noplaylist": True}) as ydl:
        return ydl.extract_info(url, download=False)


def get_available_fps(info: dict) -> list[int]:
    fps_set: set[int] = set()
    for fmt in info.get("formats", []):
        fps = fmt.get("fps")
        if fps and isinstance(fps, (int, float)) and fps > 0:
            fps_set.add(int(fps))
    return sorted(fps_set)


def download_youtube_video(
    url: str,
    quality_choice: str,
    output_dir: Path,
    fps_target: int | None,
) -> bool:
    import yt_dlp

    selected_quality = QUALITY_MAP.get(quality_choice)
    if not selected_quality:
        print("[-] Invalid quality selection.")
        return False

    if fps_target is not None:
        format_string = (
            f"bestvideo[height<={selected_quality}][fps={fps_target}][ext=mp4][vcodec^=avc1]"
            f"+bestaudio[ext=m4a]/"
            f"bestvideo[height<={selected_quality}][fps<={fps_target}][ext=mp4][vcodec^=avc1]"
            f"+bestaudio[ext=m4a]/"
            f"bestvideo[height<={selected_quality}][fps<={fps_target}]+bestaudio/"
            f"bestvideo[height<={selected_quality}]+bestaudio/"
            f"best[height<={selected_quality}]/best"
        )
    else:
        format_string = (
            f"bestvideo[height<={selected_quality}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={selected_quality}]+bestaudio/"
            f"best[height<={selected_quality}]/best"
        )

    output_template = str(output_dir / "%(title).150B [%(id)s].%(ext)s")
    ydl_opts = {
        "format": format_string,
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "windowsfilenames": True,
        "retries": MAX_RETRIES,
        "progress_hooks": [youtube_progress_hook],
    }
    if has_ffmpeg():
        ydl_opts["merge_output_format"] = "mp4"

    print("\n[+] Downloading video...\n")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"[+] Saved to: {output_dir}")
        return True
    except yt_dlp.utils.DownloadError as error:
        print(f"\n[-] Download failed: {error}")
        return False
    except KeyboardInterrupt:
        print("\n[-] Cancelled by user.")
        return False
    except Exception as error:
        print(f"\n[-] Unexpected error: {error}")
        return False


def download_youtube_audio(url: str, output_dir: Path) -> bool:
    import yt_dlp

    output_template = str(output_dir / "%(title).150B [%(id)s].%(ext)s")
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "windowsfilenames": True,
        "retries": MAX_RETRIES,
        "progress_hooks": [youtube_progress_hook],
    }

    if has_ffmpeg():
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }]
    else:
        print("[!] ffmpeg not found, audio will be saved in its original format.")

    print("\n[+] Downloading audio...\n")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"[+] Saved to: {output_dir}")
        return True
    except yt_dlp.utils.DownloadError as error:
        print(f"\n[-] Download failed: {error}")
        return False
    except KeyboardInterrupt:
        print("\n[-] Cancelled by user.")
        return False
    except Exception as error:
        print(f"\n[-] Unexpected error: {error}")
        return False


def prompt_youtube_url_and_info() -> tuple[str, dict] | None:
    url = input("Paste YouTube URL: ").strip()
    if not is_valid_url(url):
        print("[-] Invalid URL.")
        return None

    print("\n[+] Fetching video info...")
    try:
        info = fetch_youtube_info(url)
    except Exception as error:
        print(f"[-] Failed to fetch video info: {error}")
        return None

    if not info:
        print("[-] Could not retrieve video info for this URL.")
        return None

    print("\n=== Video Info ===")
    print(f"Title    : {info.get('title', 'N/A')}")
    print(f"Channel  : {info.get('uploader', 'N/A')}")
    print(f"Duration : {format_duration(info.get('duration'))}")
    return url, info


def run_youtube_video_flow(video_dir: Path) -> None:
    result = prompt_youtube_url_and_info()
    if not result:
        return
    url, info = result

    print("\nAvailable Quality:")
    for idx, label in enumerate(QUALITY_LABELS, start=1):
        print(f"{idx}. {label}")
    quality_choice = input("\nChoose quality: ").strip()
    if quality_choice not in QUALITY_MAP:
        print("[-] Invalid quality selection.")
        return

    available_fps = get_available_fps(info)
    print("\nAvailable FPS values in this video:", available_fps if available_fps else "Unknown")

    print("\nSelect FPS:")
    option_map: dict[str, int | None | object] = {}
    option_idx = 1

    print(f"{option_idx}. Any (default)")
    option_map[str(option_idx)] = None
    option_idx += 1

    for fps in FPS_PREDEFINED:
        label = f"{fps} fps"
        if fps in available_fps:
            label += " ✓"
        print(f"{option_idx}. {label}")
        option_map[str(option_idx)] = fps
        option_idx += 1

    print(f"{option_idx}. Custom (enter any number)")
    option_map[str(option_idx)] = _FPS_CUSTOM

    choice = input("\nChoose FPS (Enter for default 'Any'): ").strip()

    fps_target: int | None
    if choice == "":
        fps_target = None
    elif choice in option_map:
        val = option_map[choice]
        if val is _FPS_CUSTOM:
            custom_input = input("Enter desired FPS (e.g., 50): ").strip()
            try:
                fps_target = int(custom_input)
                if fps_target <= 0:
                    raise ValueError("FPS must be positive")
            except ValueError as e:
                print(f"[-] Invalid number ({e}), using 'Any'.")
                fps_target = None
        else:
            fps_target = val
    else:
        print("[-] Invalid selection, using 'Any'.")
        fps_target = None

    if fps_target is not None:
        print(f"[+] Using FPS target: {fps_target}")
    else:
        print("[+] Using any FPS.")

    try:
        ensure_directory(video_dir)
    except PermissionError:
        return
    download_youtube_video(url, quality_choice, video_dir, fps_target)


def run_youtube_audio_flow(audio_dir: Path) -> None:
    result = prompt_youtube_url_and_info()
    if not result:
        return
    url, _ = result
    try:
        ensure_directory(audio_dir)
    except PermissionError:
        return
    download_youtube_audio(url, audio_dir)


def expand_tiktok_url(url: str) -> str:
    import requests

    try:
        response = requests.get(
            url,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            timeout=NETWORK_TIMEOUT,
        )
        resolved = response.url
        if resolved != url:
            return resolved
        return url
    except requests.RequestException as e:
        print(f"[!] URL expansion failed ({e}), proceeding with original URL.")
        return url


def download_binary_file(url: str, filepath: Path) -> bool:
    import requests

    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
    except PermissionError as e:
        print(f"\n[-] Permission denied creating directory {filepath.parent}: {e}")
        return False

    filepath = unique_path(filepath)
    headers = {"User-Agent": USER_AGENT}

    response = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                url, stream=True, headers=headers, timeout=DOWNLOAD_TIMEOUT
            )
            response.raise_for_status()
            break
        except requests.RequestException as error:
            response = None
            if attempt == MAX_RETRIES:
                print(f"\n[-] Failed to start download after {MAX_RETRIES} attempts: {error}")
                return False
            print(f"\n[!] Attempt {attempt} failed ({error}), retrying in "
                  f"{RETRY_BACKOFF_SECONDS * attempt}s...")
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    if response is None:
        print("\n[-] No response received.")
        return False

    total = int(response.headers.get("content-length", 0))
    downloaded = 0
    chunk_size = 1024 * 512

    try:
        with open(filepath, "wb") as file_handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                file_handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 / total
                    print_progress(percent, downloaded / 1024 / 1024, total / 1024 / 1024)
    except OSError as error:
        print(f"\n[-] Failed to write file: {error}")
        filepath.unlink(missing_ok=True)
        return False
    finally:
        response.close()

    if total and downloaded < total:
        print(f"\n[-] Incomplete download ({downloaded}/{total} bytes).")
        filepath.unlink(missing_ok=True)
        return False

    print("\n[+] Done!")
    return True


def fetch_tiktok_data(url: str) -> dict | None:
    import requests

    api_url = TIKWM_API.format(quote(url))
    headers = {"User-Agent": USER_AGENT}

    response = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(api_url, headers=headers, timeout=NETWORK_TIMEOUT)
            if response.status_code == 429:
                wait = RETRY_BACKOFF_SECONDS * (2 ** attempt)
                print(f"[!] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                response = None
                continue
            response.raise_for_status()
            break
        except requests.RequestException as error:
            response = None
            if attempt == MAX_RETRIES:
                print(f"[-] Failed after {MAX_RETRIES} attempts: {error}")
                return None
            print(f"[!] Attempt {attempt} failed ({error}), retrying...")
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    if response is None:
        print("[-] All attempts exhausted (rate limited or network failure).")
        return None

    try:
        data = response.json()
    except (ValueError, json.JSONDecodeError):
        print("[-] Failed to decode API response.")
        return None

    if data.get("code") != 0:
        print(f"[-] TikTok API error: {data.get('msg', 'unknown')}")
        return None

    return data.get("data", {})


def _image_extension_from_url(url: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower()
    return ext if ext in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def download_tiktok(url: str, video_dir: Path, music_dir: Path) -> None:
    try:
        print("\n[+] Expanding URL...")
        resolved_url = expand_tiktok_url(url)
        print(f"[+] Real URL: {resolved_url}")

        print("[+] Fetching TikTok data...")
        video_data = fetch_tiktok_data(resolved_url)
        if not video_data:
            return

        title = sanitize_filename(video_data.get("title") or "tiktok_post")
        author = sanitize_filename(
            (video_data.get("author") or {}).get("nickname") or "unknown"
        )
        duration = video_data.get("duration", 0)
        likes = video_data.get("digg_count", 0)
        print("\n=== TikTok Info ===")
        print(f"Author   : {author}")
        print(f"Title    : {title}")
        print(f"Duration : {format_duration(duration)}")
        print(f"Likes    : {likes}")

        print("\nWhat to download?")
        print("1. Video + Audio (best quality)")
        print("2. Video only")
        print("3. Audio only")
        mode = input("Choose (1-3): ").strip()
        if mode not in ("1", "2", "3"):
            print("[-] Invalid choice, defaulting to Video + Audio.")
            mode = "1"

        video_url: str | None = None
        if mode in ("1", "2"):
            print("\nVideo quality:")
            print("1. No watermark (HD) – recommended")
            print("2. Watermarked (SD)")
            quality = input("Choose (1-2): ").strip()
            if quality == "2":
                video_url = video_data.get("wmplay") or video_data.get("play")
            else:
                video_url = video_data.get("hdplay") or video_data.get("play")

            if not video_url:
                images = video_data.get("images")
                if images:
                    print(f"\n[+] This is a photo slideshow ({len(images)} images).")
                    base_name = f"{author}_{title}"
                    try:
                        image_dir = ensure_directory(video_dir / base_name)
                    except PermissionError:
                        return
                    for idx, img_url in enumerate(images, start=1):
                        ext = _image_extension_from_url(img_url)
                        img_path = image_dir / f"{base_name}_{idx}{ext}"
                        if download_binary_file(img_url, img_path):
                            print(f"[+] Saved image {idx}/{len(images)}")
                    return
                else:
                    print("[-] No video URL or images found.")
                    return

        music_url: str | None = video_data.get("music") if mode in ("1", "3") else None
        base_name = f"{author}_{title}"

        if video_url and mode in ("1", "2"):
            try:
                ensure_directory(video_dir)
            except PermissionError:
                return
            video_path = video_dir / f"{base_name}.mp4"
            print(f"\n[+] Downloading video: {video_path.name}")
            if download_binary_file(video_url, video_path):
                print(f"[+] Saved: {video_path}")

        if music_url and mode in ("1", "3"):
            try:
                ensure_directory(music_dir)
            except PermissionError:
                return
            music_path = music_dir / f"{base_name}.mp3"
            print(f"\n[+] Downloading audio: {music_path.name}")
            if download_binary_file(music_url, music_path):
                print(f"[+] Saved: {music_path}")

        if mode == "1" and not music_url:
            print("\n[!] No separate music track found for this post.")

    except KeyboardInterrupt:
        print("\n[-] Cancelled by user.")
    except Exception as error:
        print(f"\n[-] Error: {error}")


def run_tiktok_flow(video_dir: Path, music_dir: Path) -> None:
    url = input("Paste TikTok URL: ").strip()
    if not is_valid_url(url) or "tiktok.com" not in urlparse(url).netloc:
        print("[-] Invalid TikTok URL.")
        return
    download_tiktok(url, video_dir, music_dir)


def print_menu() -> None:
    print("\n=== All-in-One Downloader ===")
    print("1. YouTube video")
    print("2. YouTube audio")
    print("3. TikTok video")
    print("4. Check dependencies")
    print("5. Install missing dependencies")
    print("6. Exit")


def _handle_sigterm(signum: int, frame: object) -> None:
    print("\n[-] Received SIGTERM. Exiting cleanly.")
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGINT, signal.default_int_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_sigterm)

    clear_screen()
    print(colored_banner(banner))
    print("=== All-in-One Downloader ===")
    print("checking file...")

    if not print_dependency_status():
        print("\nSome required packages are missing.")
        print("Run option 5 from the menu, or install manually with:")
        print(f"  {sys.executable} -m pip install yt-dlp requests")

    root = get_downloads_root()
    print(f"\n[+] Download root folder: {root}")
    if not root.exists():
        print("[!] Root folder does not exist yet – it will be created when needed.")

    youtube_video_dir = root / "YouTube" / "Video"
    youtube_audio_dir = root / "YouTube" / "Audio"
    tiktok_video_dir = root / "TikTok" / "Video"
    tiktok_music_dir = root / "TikTok" / "Music"

    while True:
        try:
            print_menu()
            choice = input("\nChoose an option (1-6): ").strip()

            if choice in ("1", "2"):
                if not is_package_installed("yt_dlp"):
                    print("[-] yt-dlp is not installed. Choose option 5 to install it.")
                elif choice == "1":
                    run_youtube_video_flow(youtube_video_dir)
                else:
                    run_youtube_audio_flow(youtube_audio_dir)
            elif choice == "3":
                if not is_package_installed("requests"):
                    print("[-] requests is not installed. Choose option 5 to install it.")
                else:
                    run_tiktok_flow(tiktok_video_dir, tiktok_music_dir)
            elif choice == "4":
                print_dependency_status()
            elif choice == "5":
                install_missing_dependencies()
            elif choice == "6":
                print("\nGoodbye!")
                break
            else:
                print("[-] Invalid option.")

            pause()
        except KeyboardInterrupt:
            print("\n\n[-] Interrupted. Exiting.")
            break
        except EOFError:
            print("\n\nGoodbye!")
            break


if __name__ == "__main__":
    main()
