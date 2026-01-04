import subprocess
import os
import re
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
        progress_callback=None,
        download_subs=False,
        trim=False,
        trim_start=None,
        trim_end=None,
        audio_fx=None,
    ):
        os.makedirs(outdir, exist_ok=True)

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--newline",
            "--progress",
            "-o",
            os.path.join(outdir, "%(title)s.%(ext)s"),
        ]

        # format logic (keep yours)
        if fmt in ("mp3", "wav"):
            cmd += ["-x", "--audio-format", fmt]
        else:
            format_selector = "bestvideo+bestaudio/best"
            if resolution != "best":
                h = resolution.replace("p", "")
                format_selector = f"bestvideo[height<={h}]+bestaudio/best"
            if fmt in ("mp4", "webm"):
                format_selector += f"/{fmt}"
            cmd += ["-f", format_selector]

        if download_subs:
            cmd += ["--write-subs", "--sub-langs", "en"]

        if audio_fx:
            fx = audio_fx.lower()
            if "normalize" in fx:
                cmd += ["--postprocessor-args", "-af loudnorm"]
            elif "bass" in fx:
                cmd += ["--postprocessor-args", "-af bass=g=10"]

        cmd.append(url)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        percent_re = re.compile(r"(\d+(?:\.\d+)?)%")

        for line in process.stdout:
            match = percent_re.search(line)
            if match and progress_callback:
                percent = max(0, min(100, int(float(match.group(1)))))
                progress_callback(percent)

        process.wait()

        if progress_callback:
            progress_callback(100)
