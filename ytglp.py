import customtkinter as ctk
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from platformdirs import user_music_dir, user_videos_dir, user_downloads_dir
import yt_dlp
import os

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Globals
#download_path = None
download_path = user_downloads_dir()
last_folder_selected = None
BUTTON_COLOR, HOVER_COLOR = "#9141ac", "#7e3795"
last_fetched_url = None
fetch_timer = None
last_fetched_url = None



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

def make_spinbox_frame(parent):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    vars = []
    for i, width in enumerate([50, 50, 50]):  # HH, MM, SS
        var = tk.StringVar(value="00")
        spinbox = tk.Spinbox(frame, from_=0, to=59, width=3, textvariable=var,
                             justify="center", font=("Arial", 14), 
                             fg="white", bg="#3a3a3f", 
                             highlightthickness=0, relief="flat",
                             validate="key", 
                             validatecommand=(frame.register(lambda s: s.isdigit() and 0 <= int(s) <= 59), '%P'))
        spinbox.grid(row=0, column=i, padx=5)
        vars.append(spinbox)
    frame.pack(pady=(5, 0))
    return vars

def toggle_trim():
    enabled = trim_var.get()
    color = "white" if enabled else "gray40"
    state = "normal" if enabled else "disabled"
    
    for spinbox in start_spin + end_spin:
        spinbox.configure(state=state)
    
    start_label.configure(text_color=color)
    end_label.configure(text_color=color)

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

def on_url_change(event=None):
    global fetch_timer
    if fetch_timer:
        root.after_cancel(fetch_timer)
    fetch_timer = root.after(800, auto_fetch_formats)

def auto_fetch_formats():
    global last_fetched_url
    url = url_entry.get().strip()

    if not url or url == last_fetched_url:
        return  # Skip if URL is empty or already fetched

    last_fetched_url = url  # Update only if fetching proceeds

    log_box.delete("1.0", "end")
    log_box.insert("end", "[Fetching available formats...]\n")
    progress_bar.set(0)

    def task():
        try:
            opts = {'quiet': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])
            quality_options = set()

            for f in formats:
                height = f.get('height')
                if height and height >= 360:
                    quality_options.add(f"{height}p")
            quality_options.add("best")

            quality_options = sorted(
                quality_options,
                key=lambda x: int(x.rstrip('p')) if x != "best" else 9999,
                reverse=True
            )

            root.after(0, lambda: quality_dropdown.configure(values=quality_options))
            root.after(0, lambda: quality_dropdown.set("best"))
            root.after(0, lambda: log_box.insert("end", "[Formats fetched.]\n"))
        except Exception as e:
            root.after(0, lambda: log_box.insert("end", f"Error fetching formats:\n{e}\n"))

    threading.Thread(target=task, daemon=True).start()

def download_video():
    global download_path
    if not download_path:
        return messagebox.showwarning("No Folder", "Choose a download folder first.")

    url = url_entry.get().strip()
    fmt = format_dropdown.get()
    qual = quality_dropdown.get()
    st_vals = [sb.get().zfill(2) for sb in start_spin]
    et_vals = [sb.get().zfill(2) for sb in end_spin]
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
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
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
            ydl_opts['postprocessor_args'] = ['-vn']
        elif fmt != "default":
            # Map quality to format selector
            fmt_map = {
                "best": "bestvideo+bestaudio/best",
            }
            if qual.endswith('p') and qual[:-1].isdigit():
                height_limit = int(qual[:-1])
                fmt_map[qual] = f"bestvideo[height<={height_limit}]+bestaudio/best"
            ydl_opts['format'] = fmt_map.get(qual, "bestvideo+bestaudio/best")
            ydl_opts['merge_output_format'] = fmt

        if trim_var.get():
            # Convert HH:MM:SS to seconds
            def to_seconds(h, m, s):
                return int(h)*3600 + int(m)*60 + int(s)

            start_sec = to_seconds(*st_vals)
            end_sec = to_seconds(*et_vals)
            if end_sec <= start_sec:
                messagebox.showwarning("Trim Error", "End time must be greater than start time.")
                return

            ydl_opts['postprocessor_args'] = ydl_opts.get('postprocessor_args', []) + [
                '-ss', str(start_sec),
                '-to', str(end_sec),
            ]

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

ctk.CTkLabel(root, text="YouTube URL / Playlist:", font=("Arial", 14), text_color="white").pack(pady=(15,5))
url_entry = ctk.CTkEntry(root, width=500, fg_color="#3a3a3f", border_color="#5a5a5f")
url_entry.pack()
url_entry.bind("<FocusOut>", lambda event: auto_fetch_formats())
url_entry.bind("<Return>", lambda event: auto_fetch_formats())
url_entry.bind("<KeyRelease>", on_url_change)


ctk.CTkLabel(root, text="Format Type:", font=("Arial", 14), text_color="white").pack(pady=(5, 2))
format_dropdown = ctk.CTkOptionMenu(root, values=["default","mp4","mkv","webm","mp3","wav"],
                                    fg_color="#3a3a3f", button_color="#5a5a5f", command=on_format_change)
format_dropdown.set("default")
format_dropdown.pack(pady=(0, 10))

ctk.CTkLabel(root, text="Video Quality:", font=("Arial", 14), text_color="white").pack(pady=(5, 2))
quality_dropdown = ctk.CTkOptionMenu(root, values=["best"], fg_color="#3a3a3f", button_color="#5a5a5f")
quality_dropdown.set("best")
quality_dropdown.pack(pady=(0, 10))

trim_var = ctk.IntVar(value=0)  # Trim off by default
trim_switch = ctk.CTkSwitch(root, text="Trim Video", variable=trim_var, command=toggle_trim)
trim_switch.pack(pady=(10, 5))

start_label = ctk.CTkLabel(root, text="Start Time (HH:MM:SS):", font=("Arial", 14), text_color="gray40")
start_label.pack()
start_spin = make_spinbox_frame(root)

end_label = ctk.CTkLabel(root, text="End Time (HH:MM:SS):", font=("Arial", 14), text_color="gray40")
end_label.pack()
end_spin = make_spinbox_frame(root)

toggle_trim()  # Initialize spinboxes & labels color

folder_label = ctk.CTkLabel(root, text="No folder selected.", font=("Arial",12), text_color="lightgray")
folder_label.pack(pady=(15,5))
ctk.CTkButton(root, text="Choose Folder", command=choose_folder,
              fg_color=BUTTON_COLOR, hover_color=HOVER_COLOR).pack()

remember_var = ctk.IntVar()

download_btn = ctk.CTkButton(root, text="Download", command=download_video,
                             fg_color=BUTTON_COLOR, hover_color=HOVER_COLOR, state="disabled")
download_btn.pack(pady=10)

progress_bar = ctk.CTkProgressBar(root, width=500)
progress_bar.set(0)
progress_bar.pack(pady=(10, 10))

ctk.CTkLabel(root, text="Download Log:", font=("Arial", 14), text_color="white").pack(pady=(5, 5))
log_box = ctk.CTkTextbox(root, width=550, height=200, fg_color="#1e1e22", text_color="white")
log_box.pack(pady=(0, 20))

folder_label.configure(text=f"Download to: {download_path}")
download_btn.configure(state="normal")
root.mainloop()
