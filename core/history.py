import json


class HistoryManager:
    def __init__(self):
        self.file = "history.json"
        self.data = []
        self.load()

    def load(self):
        try:
            with open(self.file, "r") as f:
                self.data = json.load(f)
        except Exception:
            self.data = []

    def save(self):
        with open(self.file, "w") as f:
            json.dump(self.data, f, indent=4)

    def add(self, url):
        self.data.append(url)
        self.save()

    def clear(self):
        self.data = []
        self.save()
