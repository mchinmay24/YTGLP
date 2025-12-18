import yt_dlp
import requests


class MetadataFetcher:
    def get_metadata(self, url):
        info = self.get_raw_info(url)
        if not info:
            return None

        return {
            "title": info.get("title", "Unknown"),
            "uploader": info.get("uploader", "Unknown"),
            "duration": info.get("duration", 0),
        }

    def get_raw_info(self, url):
        try:
            with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception:
            return {}

    def download_thumbnail(self, thumb_url, out_path: str = "thumbnail.jpg"):
        """Download thumbnail image to disk.

        Args:
            thumb_url: URL of the thumbnail.
            out_path: Path where the image will be saved.
        """
        if not thumb_url:
            return
        try:
            r = requests.get(thumb_url, timeout=10)
            if r.status_code == 200:
                with open(out_path, "wb") as f:
                    f.write(r.content)
        except Exception:
            # thumbnail is optional; fail silently
            pass
