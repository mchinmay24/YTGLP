import json
import os
from pathlib import Path


class SettingsManager:
    def __init__(self):
        self.file = "settings.json"

        # Default to the user's Downloads directory (fallback to cwd if it doesn't exist)
        default_download_dir = Path.home() / "Downloads"
        if not default_download_dir.exists():
            default_download_dir = Path.cwd()

        self.data = {
            "output_folder": str(default_download_dir),
            
        }
        self.load()

    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, "r") as f:
                    self.data.update(json.load(f))
            except Exception:
                # If settings are corrupt, ignore and use defaults
                pass

    def save(self):
        with open(self.file, "w") as f:
            json.dump(self.data, f, indent=4)
