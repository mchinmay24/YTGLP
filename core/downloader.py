import subprocess
import os
import re
from typing import Callable, Optional


import os
import re
import subprocess
from typing import Callable, Optional


class VideoDownloader:
    """
    CLI-based wrapper around system-installed yt-dlp.
    """

    def download(
        self,
        url: str,
        fmt: str,
        resolution: str,
        outdir: str,
        progress_callback: Optional[Callable[[int], None]] = None,
        download_subs: bool = False,
        trim: bool = False,          # intentionally unused for now
        trim_start: Optional[str] = None,
        trim_end: Optional[str] = None,
        audio_fx: Optional[str] = None,
    ) -> None:
        os.makedirs(outdir, exist_ok=True)

        # -------------------------
        # Base yt-dlp command
        # -------------------------
       cmd = [
            "yt-dlp",
            "--no-playlist",
            "--progress-template",
            "download:%(progress._percent)s",
            "-o",
            os.path.join(outdir, "%(title)s.%(ext)s"),
        ]


        is_audio = False

        # -------------------------
        # Format & resolution logic
        # -------------------------
        if fmt in ("mp3", "wav"):
            # Audio-only download
            is_audio = True
            cmd += ["-x", "--audio-format", fmt]
        else:
            # Video download
            format_selector = "bestvideo+bestaudio/best"

            if resolution != "best":
                height = resolution.replace("p", "")
                format_selector = (
                    f"bestvideo[height<={height}]+bestaudio/best"
                )

            if fmt == "mp4":
                format_selector = f"{format_selector}/mp4"
            elif fmt == "webm":
                format_selector = f"{format_selector}/webm"

            cmd += ["-f", format_selector]

        # -------------------------
        # Subtitles
        # -------------------------
        if download_subs:
            cmd += ["--write-subs", "--sub-langs", "en"]

        # -------------------------
        # Audio post-processing
        # -------------------------
        if is_audio and audio_fx:
            fx = audio_fx.lower()
            if "normalize" in fx:
                cmd += ["--postprocessor-args", "-af loudnorm"]
            elif "bass" in fx:
                cmd += ["--postprocessor-args", "-af bass=g=10"]

        # -------------------------
        # URL
        # -------------------------
        cmd.append(url)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            bufsize=0,   # IMPORTANT: unbuffered
        )

        percent_re = re.compile(rb"download:(\d+(?:\.\d+)?)")
        buffer = b""

        while True:
            chunk = proc.stderr.read(1024)
            if not chunk:
                break

            buffer += chunk

            while b"\r" in buffer:
                line, buffer = buffer.split(b"\r", 1)

                match = percent_re.search(line)
                if match and progress_callback:
                    try:
                        percent = int(float(match.group(1)))
                        progress_callback(percent)
                    except Exception:
                        pass

        proc.wait()

        if progress_callback:
            progress_callback(100)