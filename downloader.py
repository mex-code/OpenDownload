from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import quote, urlparse

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

TIKWM_API = "https://www.tikwm.com/api/?url={}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class DependencyStatus:
    name: str
    package: str
    installed: bool
    version: str | None


def get_dependency_status() -> list[DependencyStatus]:
    statuses = []
    for module_name, package_name in REQUIRED_PACKAGES.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "unknown")
            statuses.append(DependencyStatus(module_name, package_name, True, version))
        except ImportError:
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


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def get_downloads_root() -> Path:
    env_override = os.environ.get("DOWNLOADER_OUTPUT_DIR")
    if env_override:
        return Path(env_override).expanduser()

    android_storage = Path.home() / "storage" / "shared" / "Downloads"
    if android_storage.parent.exists():
        return android_storage

    home_downloads = Path.home() / "Downloads"
    return home_downloads


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename(name: str, max_length: int = 80) -> str:
    cleaned = name
    for char in INVALID_FILENAME_CHARS:
        cleaned = cleaned.replace(char, "_")
    cleaned = cleaned.strip().strip(".")
    return cleaned[:max_length] if cleaned else "untitled"


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except ValueError:
        return False


def format_duration(seconds: float | None) -> str:
    if not seconds:
        return "N/A"
    return str(timedelta(seconds=int(seconds)))


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def pause() -> None:
    input("\nPress Enter to continue...")


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


def fetch_youtube_info(url: str):
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "socket_timeout": 30}) as ydl:
        return ydl.extract_info(url, download=False)


def download_youtube_video(url: str, quality_choice: str, output_dir: Path) -> bool:
    import yt_dlp

    selected_quality = QUALITY_MAP.get(quality_choice)
    if not selected_quality:
        print("[-] Invalid quality selection.")
        return False

    output_template = str(output_dir / "%(title)s.%(ext)s")
    format_string = (
        f"bestvideo[height<={selected_quality}][ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
        f"best[height<={selected_quality}]"
    )

    ydl_opts = {
        "format": format_string,
        "merge_output_format": "mp4" if has_ffmpeg() else None,
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
        "progress_hooks": [youtube_progress_hook],
    }
    ydl_opts = {key: value for key, value in ydl_opts.items() if value is not None}

    print("\n[+] Downloading video...\n")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"[+] Saved to: {output_dir}")
        return True
    except Exception as error:
        print(f"\n[-] Download failed: {error}")
        return False


def download_youtube_audio(url: str, output_dir: Path) -> bool:
    import yt_dlp

    output_template = str(output_dir / "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_template,
        "noplaylist": True,
        "quiet": False,
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
    except Exception as error:
        print(f"\n[-] Download failed: {error}")
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

    print("\n=== Video Info ===")
    print(f"Title    : {info.get('title', 'N/A')}")
    print(f"Channel  : {info.get('uploader', 'N/A')}")
    print(f"Duration : {format_duration(info.get('duration'))}")
    return url, info


def run_youtube_video_flow(video_dir: Path) -> None:
    result = prompt_youtube_url_and_info()
    if not result:
        return
    url, _ = result

    print("\nAvailable Quality:")
    for index, label in enumerate(QUALITY_LABELS, start=1):
        print(f"{index}. {label}")
    quality_choice = input("\nChoose quality: ").strip()
    download_youtube_video(url, quality_choice, ensure_directory(video_dir))


def run_youtube_audio_flow(audio_dir: Path) -> None:
    result = prompt_youtube_url_and_info()
    if not result:
        return
    url, _ = result
    download_youtube_audio(url, ensure_directory(audio_dir))


def expand_tiktok_url(url: str) -> str:
    import requests

    try:
        response = requests.get(
            url,
            allow_redirects=True,
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        return response.url
    except requests.RequestException:
        return url


def download_binary_file(url: str, filepath: Path) -> bool:
    import requests

    headers = {"User-Agent": USER_AGENT}
    try:
        response = requests.get(url, stream=True, headers=headers, timeout=60)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"\n[-] Failed to start download: {error}")
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
        return False

    print("\n[+] Done!")
    return True


def fetch_tiktok_data(url: str) -> dict | None:
    import requests

    api_url = TIKWM_API.format(quote(url))
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(api_url, headers=headers, timeout=20)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"[-] Failed to reach TikTok API: {error}")
        return None

    try:
        data = response.json()
    except ValueError:
        print("[-] Failed to decode API response.")
        return None

    if data.get("code") != 0:
        print("[-] TikTok API returned an error.")
        return None

    return data.get("data", {})


def download_tiktok(url: str, video_dir: Path, music_dir: Path) -> None:
    try:
        print("\n[+] Expanding URL...")
        resolved_url = expand_tiktok_url(url)
        print(f"[+] Real URL: {resolved_url}")

        print("[+] Fetching TikTok data...")
        video_data = fetch_tiktok_data(resolved_url)
        if not video_data:
            return

        video_url = (
            video_data.get("hdplay")
            or video_data.get("play")
            or video_data.get("wmplay")
        )
        music_url = video_data.get("music")

        if not video_url:
            print("[-] No video found.")
            return

        title = sanitize_filename(video_data.get("title", "tiktok_video"))
        author = sanitize_filename(video_data.get("author", {}).get("nickname", "unknown"))
        base_name = f"{author}_{title}"

        video_path = ensure_directory(video_dir) / f"{base_name}.mp4"
        print(f"\n[+] Downloading video: {base_name}.mp4")
        if download_binary_file(video_url, video_path):
            print(f"[+] Saved video: {video_path}")

        if music_url:
            music_path = ensure_directory(music_dir) / f"{base_name}.mp3"
            print(f"\n[+] Downloading music: {base_name}.mp3")
            if download_binary_file(music_url, music_path):
                print(f"[+] Saved music: {music_path}")
        else:
            print("\n[-] No music found for this video.")

    except KeyboardInterrupt:
        print("\n[-] Cancelled by user.")
    except Exception as error:
        print(f"\n[-] Error: {error}")


def run_tiktok_flow(video_dir: Path, music_dir: Path) -> None:
    url = input("Paste TikTok URL: ").strip()
    if "tiktok.com" not in url or not is_valid_url(url):
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


def main() -> None:
    clear_screen()
    print("=== All-in-One Downloader ===")

    if not print_dependency_status():
        print("\nSome required packages are missing.")
        print("Run option 5 from the menu, or install manually with:")
        print(f"  {sys.executable} -m pip install -r requirements.txt")

    root = get_downloads_root()
    youtube_video_dir = root / "YouTube" / "Video"
    youtube_audio_dir = root / "YouTube" / "Audio"
    tiktok_video_dir = root / "TikTok" / "Video"
    tiktok_music_dir = root / "TikTok" / "Music"

    while True:
        print_menu()
        choice = input("\nChoose an option (1-6): ").strip()

        if choice in ("1", "2"):
            statuses = get_dependency_status()
            if not all(status.installed for status in statuses if status.name == "yt_dlp"):
                print("[-] yt-dlp is not installed. Choose option 5 to install it.")
            elif choice == "1":
                run_youtube_video_flow(youtube_video_dir)
            else:
                run_youtube_audio_flow(youtube_audio_dir)
        elif choice == "3":
            statuses = get_dependency_status()
            if not all(status.installed for status in statuses if status.name == "requests"):
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


if __name__ == "__main__":
    main()
