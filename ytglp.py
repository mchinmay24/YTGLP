import customtkinter as ctk
from tkinter import ttk
import threading
from tkinter import messagebox, filedialog, Spinbox
from pathlib import Path
from platformdirs import user_music_dir, user_videos_dir
import yt_dlp
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Globals
download_path = None
last_folder_selected = None
BUTTON_COLOR, HOVER_COLOR = "#9141ac", "#7e3795"

def choose_folder():
    global download_path, last_folder_selected
    folder = filedialog.askdirectory(initialdir=last_folder_selected or "/")
    if folder:
        download_path = folder
        if remember_var.get():
            last_folder_selected = folder
        folder_label.configure(text=f"Download to: {download_path}")
        download_btn.configure(state="normal")
    else:
        folder_label.configure(text="No folder selected.")
        download_btn.configure(state="disabled")

def make_spinbox_frame(parent, label):
    style = ttk.Style()
    style.theme_use("default")
    style.configure("DarkSpinbox.TSpinbox",
                    foreground="white",
                    background="#3a3a3f",
                    fieldbackground="#3a3a3f",
                    selectbackground="#5a5a5f",
                    selectforeground="white",
                    borderwidth=1)

    frame = ctk.CTkFrame(parent, fg_color="transparent")
    ctk.CTkLabel(frame, text=label, font=("Arial", 14), text_color="white").grid(row=0, column=0, padx=5)
    boxes = []
    for i, maxval in enumerate([99, 59, 59]):  # HH max 99, MM/SS max 59
        box = ttk.Spinbox(frame, from_=0, to=maxval, width=5, format="%02.0f",
                          style="DarkSpinbox.TSpinbox", state="normal", justify="center")
        box.grid(row=0, column=i+1, padx=5)
        boxes.append(box)
    frame.pack(pady=(10, 0))
    return boxes

def toggle_trim_inputs():
    state = "normal" if trim_var.get() else "disabled"
    for box in start_spin + end_spin:
        box.configure(state=state)

def on_format_change(choice):
    global download_path
    if choice in ("mp3", "wav"):
        quality_dropdown.configure(state="disabled")
        default_folder = Path(user_music_dir())
    else:
        quality_dropdown.configure(state="normal")
        default_folder = Path(user_videos_dir())

    if not download_path or not remember_var.get():
        download_path = str(default_folder)
        folder_label.configure(text=f"Download to: {download_path}")
        download_btn.configure(state="normal")

def fetch_formats():
    url = url_entry.get().strip()
    if not url:
        return messagebox.showwarning("Missing URL", "Please enter a YouTube URL or playlist.")
    log_box.delete("1.0", "end")
    log_box.insert("end", "[Fetching available formats...]\n")

    def task():
        try:
            opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            quality_options = {"best"}
            for f in formats:
                h = f.get('height')
                if h:
                    quality_options.add(f"{h}p")
            quality_options = sorted(quality_options, key=lambda x: int(x.rstrip('p')) if x != "best" else 9999, reverse=True)
            quality_dropdown.configure(values=list(quality_options))
            quality_dropdown.set("best")
            log_box.insert("end", "[Formats fetched.]\n")
        except Exception as e:
            log_box.insert("end", f"Error fetching formats:\n{e}\n")

    threading.Thread(target=task, daemon=True).start()

def download_video():
    global download_path
    if not download_path:
        return messagebox.showwarning("No Folder", "Choose a download folder first.")

    url = url_entry.get().strip()
    fmt = format_dropdown.get()
    qual = quality_dropdown.get()
    st_vals = [box.get().zfill(2) for box in start_spin]
    et_vals = [box.get().zfill(2) for box in end_spin]
    st = ":".join(st_vals)
    et = ":".join(et_vals)

    if not url:
        return messagebox.showwarning("Missing URL", "Enter a URL or playlist link.")

    log_box.delete("1.0", "end")
    progress_bar.set(0)
    log_box.insert("end", "[Starting download...]\n")

    def progress_hook(d):
        if d.get('status') == 'downloading':
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 1)
            progress_bar.set(downloaded / total)

    def task():
        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
        }

        if fmt in ("mp3", "wav"):
            ydl_opts['format'] = "bestaudio/best"
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': fmt,
            }]
        elif fmt != "default":
            fmt_map = {
                "best": "bestvideo+bestaudio/best",
            }
            if qual.endswith('p') and qual[:-1].isdigit():
                height_limit = int(qual[:-1])
                fmt_map[qual] = f"bestvideo[height<={height_limit}]+bestaudio/best"
            ydl_opts['format'] = fmt_map.get(qual, "bestvideo+bestaudio/best")
            ydl_opts['merge_output_format'] = fmt

        if trim_var.get() and any(x != "00" for x in st_vals + et_vals):
            ydl_opts['download_sections'] = [f"*{st}-{et}"]
            ydl_opts['force_keyframes_at_cuts'] = True

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            progress_bar.set(1)
            messagebox.showinfo("Success", "Download completed!")
        except Exception as exc:
            messagebox.showerror("Error", f"Download failed:\n{exc}")

    threading.Thread(target=task, daemon=True).start()

# ==== GUI ====
root = ctk.CTk()
root.title("YTGLP")
root.geometry("600x850")
root.configure(fg_color="#2e2e32")
root.attributes("-alpha", 0.95)

ctk.CTkLabel(root, text="YouTube URL / Playlist:", font=("Arial", 14), text_color="white").pack(pady=(15, 5))
url_entry = ctk.CTkEntry(root, width=500, fg_color="#3a3a3f", border_color="#5a5a5f")
url_entry.pack()

ctk.CTkButton(root, text="Fetch Video Qualities", command=fetch_formats,
              fg_color=BUTTON_COLOR, hover_color=HOVER_COLOR).pack(pady=10)

ctk.CTkLabel(root, text="Format Type:", font=("Arial", 14), text_color="white").pack(pady=(5, 2))
format_dropdown = ctk.CTkOptionMenu(root, values=["default", "mp4", "mkv", "webm", "mp3", "wav"],
                                    fg_color="#3a3a3f", button_color="#5a5a5f", command=on_format_change)
format_dropdown.set("default")
format_dropdown.pack(pady=(0, 10))

ctk.CTkLabel(root, text="Video Quality:", font=("Arial", 14), text_color="white").pack(pady=(5, 2))
quality_dropdown = ctk.CTkOptionMenu(root, values=["best"], fg_color="#3a3a3f", button_color="#5a5a5f")
quality_dropdown.set("best")
quality_dropdown.pack(pady=(0, 10))

# Trim Switch
trim_var = ctk.BooleanVar(value=False)
trim_switch = ctk.CTkSwitch(root, text="Trim Video", variable=trim_var, command=toggle_trim_inputs)
trim_switch.pack(pady=(10, 5))

start_spin = make_spinbox_frame(root, "Start Time (HH:MM:SS):")
end_spin = make_spinbox_frame(root, "End Time (HH:MM:SS):")
toggle_trim_inputs()

folder_label = ctk.CTkLabel(root, text="No folder selected.", font=("Arial", 12), text_color="lightgray")
folder_label.pack(pady=(15, 5))

ctk.CTkButton(root, text="Choose Folder", command=choose_folder,
              fg_color=BUTTON_COLOR, hover_color=HOVER_COLOR).pack()
remember_var = ctk.IntVar()
remember_checkbox = ctk.CTkCheckBox(root, text="Remember folder (session)", text_color="white", variable=remember_var)
remember_checkbox.pack(pady=(5, 10))

download_btn = ctk.CTkButton(root, text="Download", command=download_video,
                             fg_color=BUTTON_COLOR, hover_color=HOVER_COLOR, state="disabled")
download_btn.pack(pady=10)

progress_bar = ctk.CTkProgressBar(root, width=500)
progress_bar.set(0)
progress_bar.pack(pady=(10, 10))

ctk.CTkLabel(root, text="Download Log:", font=("Arial", 14), text_color="white").pack(pady=(5, 5))
log_box = ctk.CTkTextbox(root, width=550, height=200, fg_color="#1e1e22", text_color="white")
log_box.pack(pady=(0, 20))

root.mainloop()

