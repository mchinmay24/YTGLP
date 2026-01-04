# core/dependencies.py
import sys
import shutil
import platform

REQUIRED_TOOLS = ["yt-dlp", "ffmpeg"]

LINUX_PACKAGE_MANAGERS = [
    ("apt", "sudo apt install yt-dlp ffmpeg"),
    ("dnf", "sudo dnf install yt-dlp ffmpeg"),
    ("pacman", "sudo pacman -S yt-dlp ffmpeg"),
    ("zypper", "sudo zypper install yt-dlp ffmpeg"),
]

TERMINALS = {
    "x-terminal-emulator": ["x-terminal-emulator", "-e"],
    "gnome-terminal": ["gnome-terminal", "--"],
    "konsole": ["konsole", "-e"],
    "kitty": ["kitty"],
    "alacritty": ["alacritty", "-e"],
    "xfce4-terminal": ["xfce4-terminal", "--command"],
    "mate-terminal": ["mate-terminal", "--"],
    "xterm": ["xterm", "-e"],
}


def missing_dependencies():
    return ["\n\n           " + tool for tool in REQUIRED_TOOLS if not shutil.which(tool)]


def is_windows():
    return sys.platform.startswith("win")


def is_linux():
    return sys.platform.startswith("linux")


def detect_package_manager():
    for pm, cmd in LINUX_PACKAGE_MANAGERS:
        if shutil.which(pm):
            return pm, cmd
    return None, None


def detect_terminal():
    for term, args in TERMINALS.items():
        if shutil.which(term):
            return term, args
    return None, None
