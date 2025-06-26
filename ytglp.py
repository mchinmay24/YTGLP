import customtkinter as ctk
import subprocess
from tkinter import messagebox, filedialog
import os
import threading
import json
import re
import signal

# Original button colors
button_color = "#9141ac"
hover_button_color = "#7e3795"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class YTDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Video Downloader")
        self.geometry("650x800")
        self.configure(fg_color="#2e2e32")
        self.attributes("-alpha", 0.96)

        # State
        self.download_path = None
        self.current_process = None

        self.setup_ui()

    def setup_ui(self):
        # URL entry and controls
        ctk.CTkLabel(self, text="YouTube URL(s):", font=("Arial", 14), text_color="white").pack(pady=(15, 5))
        self.url_entry = ctk.CTkTextbox(self, width=600, height=60, fg_color="#3a3a3f", text_color="white")
        self.url_entry.pack()
        self.url_entry.insert("1.0", "")

        ctk.CTkButton(self, text="Paste from Clipboard",
                      command=self.paste_clipboard,
                      fg_color=button_color,
                      hover_color=hover_button_color).pack(pady=(5, 5))

        # Format and options
        format_frame = ctk.CTkFrame(self, fg_color="transparent")
        format_frame.pack(pady=(10, 5))

        ctk.CTkLabel(format_frame, text="Convert To:", text_color="white").grid(row=0, column=0, padx=5)
        self.format_menu = ctk.CTkOptionMenu(
            format_frame,
            values=["default", "mp4", "mp3", "mkv", "webm", "wav"],
            fg_color="#3a3a3f",
            button_color="#3a3a5f",
            command=self.on_format_change
        )
        self.format_menu.set("default")
        self.format_menu.grid(row=0, column=1, padx=5)

        self.delete_checkbox = ctk.CTkCheckBox(format_frame, text="Delete original", state="disabled", text_color="white")
        self.delete_checkbox.grid(row=0, column=2, padx=5)

        self.thumb_checkbox = ctk.CTkCheckBox(self, text="Embed thumbnail (audio only)", text_color="white")
        self.thumb_checkbox.pack(pady=(0, 5))

        # Time trim
        self.time_entries("Start", "start")
        self.time_entries("End", "end")

        # Folder
        self.folder_label = ctk.CTkLabel(self, text="No folder selected", text_color="lightgray")
        self.folder_label.pack(pady=(10, 2))

        ctk.CTkButton(self, text="Choose Folder",
                      command=self.choose_folder,
                      fg_color=button_color,
                      hover_color=hover_button_color).pack()
        self.remember_checkbox = ctk.CTkCheckBox(self, text="Remember this folder", text_color="white")
        self.remember_checkbox.pack(pady=(0, 10))

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(5, 5))

        self.download_button = ctk.CTkButton(button_frame, text="Download", state="disabled",
                                             command=self.download_video,
                                             fg_color=button_color,
                                             hover_color=hover_button_color)
        self.download_button.grid(row=0, column=0, padx=5)

        self.cancel_button = ctk.CTkButton(button_frame, text="Cancel",
                                           command=self.cancel_download,
                                           fg_color="red",
                                           hover_color="#b22222")
        self.cancel_button.grid(row=0, column=1, padx=5)

        self.update_button = ctk.CTkButton(button_frame, text="Update yt-dlp",
                                           command=self.update_ytdlp,
                                           fg_color=button_color,
                                           hover_color=hover_button_color)
        self.update_button.grid(row=0, column=2, padx=5)

        self.status_label = ctk.CTkLabel(self, text="", text_color="white")
        self.status_label.pack(pady=5)

        # Progress and log
        self.progress_bar = ctk.CTkProgressBar(self, width=600)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(5, 5))

        ctk.CTkLabel(self, text="Log Output:", text_color="white").pack()
        self.log_box = ctk.CTkTextbox(self, height=250, width=600, fg_color="#1e1e22", text_color="white")
        self.log_box.pack(pady=5)

    def time_entries(self, label, prefix):
        ctk.CTkLabel(self, text=f"{label} Time (HH:MM:SS):", font=("Arial", 14), text_color="white").pack()
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack()
        setattr(self, f"{prefix}_hour", ctk.CTkEntry(frame, width=50, placeholder_text="HH"))
        setattr(self, f"{prefix}_min", ctk.CTkEntry(frame, width=50, placeholder_text="MM"))
        setattr(self, f"{prefix}_sec", ctk.CTkEntry(frame, width=50, placeholder_text="SS"))
        getattr(self, f"{prefix}_hour").grid(row=0, column=0, padx=5)
        getattr(self, f"{prefix}_min").grid(row=0, column=1, padx=5)
        getattr(self, f"{prefix}_sec").grid(row=0, column=2, padx=5)

    def on_format_change(self, choice):
        if choice == "default":
            self.delete_checkbox.configure(state="disabled")
            self.delete_checkbox.deselect()
        else:
            self.delete_checkbox.configure(state="normal")

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path or "/")
        if folder:
            self.download_path = folder
            self.folder_label.configure(text=f"Download to: {folder}")
            self.download_button.configure(state="normal")

    def paste_clipboard(self):
        try:
            clip = self.clipboard_get()
            self.url_entry.delete("1.0", "end")
            self.url_entry.insert("1.0", clip)
        except:
            pass

    def get_time(self, prefix):
        try:
            h = getattr(self, f"{prefix}_hour").get().zfill(2)
            m = getattr(self, f"{prefix}_min").get().zfill(2)
            s = getattr(self, f"{prefix}_sec").get().zfill(2)
            return f"{h}:{m}:{s}"
        except Exception:
            return "00:00:00"

    def log(self, text):
        self.log_box.insert("end", text)
        self.log_box.see("end")

    def update_ytdlp(self):
        def update():
            self.status_label.configure(text="Updating yt-dlp...")
            try:
                subprocess.run(["yt-dlp", "-U"], capture_output=True, check=True)
                messagebox.showinfo("Update", "yt-dlp updated successfully.")
            except subprocess.CalledProcessError:
                messagebox.showerror("Error", "Failed to update yt-dlp.")
            self.status_label.configure(text="")
        threading.Thread(target=update, daemon=True).start()

    def cancel_download(self):
        if self.current_process:
            self.current_process.send_signal(signal.SIGINT)
            self.status_label.configure(text="Download cancelled.")
            self.current_process = None

    def parse_progress(self, line):
        # Matches progress like: [download]  23.4%
        match = re.search(r'(\d{1,3}\.\d)%', line)
        if match:
            try:
                pct = float(match.group(1))
                self.progress_bar.set(pct / 100)
            except:
                pass
        self.log(line)

    def download_video(self):
        urls = [u.strip() for u in self.url_entry.get("1.0", "end").splitlines() if u.strip()]
        if not urls:
            messagebox.showwarning("Input Error", "Please enter at least one URL.")
            return
        if not self.download_path:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return

        self.log_box.delete("1.0", "end")
        self.progress_bar.set(0)
        self.status_label.configure(text="Starting...")

        def worker():
            for url in urls:
                self.status_label.configure(text=f"Downloading: {url}")

                base_out = os.path.join(self.download_path, "%(title)s.%(ext)s")
                cmd = ['yt-dlp', '-f', 'bestvideo+bestaudio/best', '-o', base_out]

                # Sections trim if specified
                start = self.get_time("start")
                end = self.get_time("end")
                if any([x != "00" for x in start.split(":") + end.split(":")]):
                    cmd += ['--download-sections', f"*{start}-{end}", '--force-keyframes-at-cuts']

                cmd.append(url)

                try:
                    self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

                    for line in self.current_process.stdout:
                        self.parse_progress(line)

                    self.current_process.wait()
                    if self.current_process.returncode != 0:
                        messagebox.showerror("Error", f"Download failed for {url}")
                        continue

                    # Conversion step
                    target_format = self.format_menu.get()
                    delete_orig = self.delete_checkbox.get()
                    embed_thumb = self.thumb_checkbox.get()

                    if target_format != "default":
                        convert_cmd = ['yt-dlp', '-f', 'bestaudio/best' if target_format in ['mp3','wav'] else 'bestvideo+bestaudio/best',
                                       '-o', base_out, url]

                        # Audio extraction
                        if target_format in ['mp3', 'wav']:
                            convert_cmd += ['-x', '--audio-format', target_format]
                            if embed_thumb and target_format == 'mp3':
                                convert_cmd.append('--embed-thumbnail')

                        # Video container conversion
                        else:
                            convert_cmd += ['--merge-output-format', target_format]

                        self.log(f"Converting to {target_format}...\n")
                        conv_proc = subprocess.Popen(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                        for line in conv_proc.stdout:
                            self.parse_progress(line)
                        conv_proc.wait()
                        if conv_proc.returncode != 0:
                            self.log("Conversion failed\n")
                            messagebox.showerror("Error", "Conversion failed.")
                            continue

                        if delete_orig:
                            # Find original file path (simple heuristic)
                            # Real path resolution can be more complex
                            original_path = os.path.join(self.download_path, f"{self.get_title(url)}.{self.get_ext(url)}")
                            if os.path.exists(original_path):
                                try:
                                    os.remove(original_path)
                                    self.log(f"Deleted original file: {original_path}\n")
                                except Exception as e:
                                    self.log(f"Failed to delete original: {e}\n")

                    self.progress_bar.set(1)
                    self.status_label.configure(text="Download completed")
                    self.log(f"Completed download for {url}\n")
                    messagebox.showinfo("Success", f"Download completed for {url}")

                except Exception as e:
                    self.log(f"Error: {e}\n")
                    messagebox.showerror("Error", f"An error occurred: {e}")

                finally:
                    self.current_process = None

        threading.Thread(target=worker, daemon=True).start()

    def get_title(self, url):
        try:
            out = subprocess.check_output(['yt-dlp', '--get-title', url], text=True).strip()
            return out
        except Exception:
            return "video"

    def get_ext(self, url):
        try:
            out = subprocess.check_output(['yt-dlp', '-f', 'best', '--get-filename', '-o', '%(ext)s', url], text=True).strip()
            return out
        except Exception:
            return "mp4"

if __name__ == "__main__":
    app = YTDownloaderApp()
    app.mainloop()

