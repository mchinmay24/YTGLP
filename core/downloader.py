import yt_dlp
import subprocess
import os
import shutil
from typing import Callable, Optional


class VideoDownloader:
    """Thin wrapper around yt_dlp with optional trimming and audio FX.

    This class is GUI-framework agnostic. It never touches Qt widgets directly.
    Instead it uses an optional ``progress_callback`` to report integer
    percentages (0–100).
    """

    def __init__(self):
        self.last_output: Optional[str] = None
        # Detect JS runtime
        self.has_js_runtime = bool(
            shutil.which("node") or shutil.which("nodejs") or shutil.which("deno")
        )

    def download(
        self,
        url: str,
        fmt: str,
        resolution: str,
        outdir: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        download_subs: bool = False,
        trim: bool = False,
        trim_start: Optional[str] = None,
        trim_end: Optional[str] = None,
        audio_fx: Optional[str] = None,
    ) -> None:
        """Download a single video or audio file.

        Args:
            url: Video URL.
            fmt: Output format (e.g. "mp4", "mp3", "webm", "wav").
            resolution: "best" or a string like "1080p", "720p", etc.
            outdir: Target directory.
            progress_callback: Optional callable taking an int (0–100).
            download_subs: Whether to download English subtitles.
            trim: If True, run a trimming pass after download.
            trim_start: Start timestamp ("hh:mm:ss") if trimming.
            trim_end: End timestamp ("hh:mm:ss") if trimming.
            audio_fx: Optional audio effect for audio formats:
                      "None" / "Normalize volume" / "Bass boost".
        """
        self.last_output = None
        os.makedirs(outdir, exist_ok=True)

        ydl_opts = {
            "outtmpl": os.path.join(outdir, "%(title)s.%(ext)s"),
            "format": "bestvideo+bestaudio/best",
            "progress_hooks": [lambda d: self._hook(d, progress_callback)],
            "noplaylist": True,  # disable playlist handling
        }

        # Fallback extractor args if no JS runtime
        if not self.has_js_runtime:
            ydl_opts.setdefault("extractor_args", {})
            ydl_opts["extractor_args"].setdefault("youtube", {})
            ydl_opts["extractor_args"]["youtube"]["player_client"] = ["default"]

        # Resolution handling
        if resolution != "best":
            height = resolution.replace("p", "")
            ydl_opts["format"] = f"bestvideo[height<={height}]+bestaudio/best"

        # Format-specific handling
        is_audio_only = False
        if fmt == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            is_audio_only = True
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
        elif fmt in ("wav",):
            ydl_opts["format"] = "bestaudio/best"
            is_audio_only = True
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": fmt,
                    "preferredquality": "192",
                }
            ]

        # Optional audio FX (for audio-only outputs)
        if is_audio_only and audio_fx:
            fx = audio_fx.lower()
            filter_str = None
            if "normalize" in fx:
                filter_str = "loudnorm"
            elif "bass" in fx:
                # Simple bass boost filter
                filter_str = "bass=g=10"
            if filter_str:
                # These args are passed to ffmpeg after input
                ydl_opts["postprocessor_args"] = ["-af", filter_str]

        if download_subs:
            ydl_opts["writesubtitles"] = True
            ydl_opts["subtitleslangs"] = ["en"]
            ydl_opts["subtitlesformat"] = "best"

        # Store the final filename when finished
        def _store_filename(d):
            if d.get("status") == "finished":
                self.last_output = d.get("filename", None)

        ydl_opts["progress_hooks"].append(_store_filename)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # After download, optionally trim
        if trim and self.last_output and trim_start and trim_end:
            self.trim_last_video(trim_start, trim_end)

    def _hook(self, d, progress_callback: Optional[Callable[[int], None]]) -> None:
        """Translate yt_dlp progress dict into 0–100 progress values.

        This is designed to be exception-safe and never raise, so that it
        doesn't interfere with yt_dlp's own control flow.
        """
        if not progress_callback:
            return

        try:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    downloaded = float(d.get("downloaded_bytes", 0))
                    frac = max(0.0, min(1.0, downloaded / float(total)))
                    progress_callback(int(frac * 100))
            elif status == "finished":
                progress_callback(100)
        except Exception:
            # Never let errors in the progress callback crash the download.
            pass

    def trim_last_video(self, start: str, end: str) -> bool:
        """Use ffmpeg to trim the last downloaded file in-place.

        Returns:
            True if trimming succeeded, False otherwise.
        """
        if not self.last_output or not os.path.exists(self.last_output):
            return False

        base, ext = os.path.splitext(self.last_output)
        out_file = f"{base}_trimmed{ext}"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            self.last_output,
            "-ss",
            start,
            "-to",
            end,
            "-c",
            "copy",
            out_file,
        ]
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except Exception:
            return False
