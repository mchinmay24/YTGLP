import subprocess
import os
import re


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

        
        is_audio = fmt in ("mp3", "wav")

        if is_audio:
            cmd += ["-x", "--audio-format", fmt]
        else:
            if resolution != "best":
                h = resolution.replace("p", "")
                cmd += ["-f", f"bestvideo[height<={h}]+bestaudio/best"]

            cmd += ["--merge-output-format", fmt]


        if download_subs and not is_audio:
            cmd += [
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", "en.*",
                "--convert-subs", "srt",
                "--embed-subs",
            ]

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
                progress_callback(int(float(match.group(1))))

        process.wait()

        if progress_callback:
            progress_callback(100)
