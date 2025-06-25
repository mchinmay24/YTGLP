import customtkinter as ctk
import subprocess
from tkinter import messagebox, filedialog
import os
import threading
import re

# Appearance settings
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Session-only variables
download_path = None
last_folder_selected = None

# Button colors
button_color = "#9141ac"
hover_button_color = "#7e3795"

# Tooltip class
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.overrideredirect(True)
        tw.geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(tw, text=self.text, fg_color="#333333", text_color="white", corner_radius=5, padx=5, pady=3)
        label.pack()

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

# Folder selection logic
def choose_folder():
    global download_path, last_folder_selected
    selected_folder = filedialog.askdirectory(initialdir=last_folder_selected or "/")
    if selected_folder:
        download_path = selected_folder
        if remember_checkbox.get():
            last_folder_selected = selected_folder
        folder_label.configure(text=f"Download to: {download_path}")
        download_button.configure(state="normal")
    else:
        folder_label.configure(text="No folder selected.")
        download_button.configure(state="disabled")

# Run shell command
def run_command(command, log_widget, on_progress=None):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    for line in process.stdout:
        log_widget.insert("end", line)
        log_widget.see("end")
        if on_progress:
            on_progress(line)
    process.wait()
    return process.returncode

# Progress parser
def parse_progress(line):
    match = re.search(r'\b(\d{1,3}\.\d)%', line)
    if match:
        try:
            percent = float(match.group(1)) / 100
            progress_bar.set(percent)
        except:
            pass

# Format dropdown logic
def on_format_change(choice):
    global delete_tooltip
    if choice == "default":
        delete_checkbox.configure(state="disabled")
        delete_checkbox.deselect()
        delete_tooltip = ToolTip(delete_checkbox, "Cannot delete original if no conversion is selected.")
    else:
        delete_checkbox.configure(state="normal")
        delete_checkbox.select()
        if 'delete_tooltip' in globals():
            delete_tooltip.hide_tip()
            delete_tooltip = None

# Main download function
def download_video():
    if not download_path:
        messagebox.showwarning("No Folder", "Please choose a download folder.")
        return

    url = url_entry.get()
    start_time = start_time_entry.get()
    end_time = end_time_entry.get()
    selected_format = format_option_menu.get()
    delete_original = delete_checkbox.get()

    if not url:
        messagebox.showwarning("Missing URL", "Please enter a YouTube URL.")
        return

    log_box.delete("1.0", "end")
    progress_bar.set(0)

    def task():
        output_template = os.path.join(download_path, "%(title)s.%(ext)s")
        download_cmd = [
            'yt-dlp',
            '-f', 'bestvideo+bestaudio/best',
            '-o', output_template,
            '--progress-template', 'download:%(progress._percent_str)s'
        ]

        if start_time and end_time:
            section_arg = f"*{start_time}-{end_time}"
            download_cmd += ['--download-sections', section_arg, '--force-keyframes-at-cuts']

        download_cmd.append(url)

        log_box.insert("end", "[Starting yt-dlp download...]\n")
        if run_command(download_cmd, log_box, on_progress=parse_progress) != 0:
            messagebox.showerror("Error", "Download failed.")
            return

        try:
            filename_cmd = [
                'yt-dlp', '--print', 'filename',
                '-f', 'bestvideo+bestaudio/best',
                '-o', output_template,
                url
            ]
            downloaded_file = subprocess.check_output(filename_cmd).decode().strip()
        except Exception:
            messagebox.showerror("Error", "Could not determine downloaded filename.")
            return

        if selected_format != "default":
            base_name, _ = os.path.splitext(downloaded_file)
            converted_file = f"{base_name}.{selected_format}"
            log_box.insert("end", f"[Converting to {selected_format}...]\n")
            progress_bar.set(0)
            if run_command(['ffmpeg', '-y', '-i', downloaded_file, converted_file], log_box) != 0:
                messagebox.showerror("Error", f"Conversion to {selected_format} failed.")
                return

            if delete_original:
                try:
                    os.remove(downloaded_file)
                    log_box.insert("end", "[Original file deleted.]\n")
                except Exception as e:
                    log_box.insert("end", f"[Failed to delete original file: {e}]\n")
        else:
            log_box.insert("end", "[Download completed with no conversion.]\n")

        progress_bar.set(1)
        msg = "Download completed with no conversion." if selected_format == "default" else f"Downloaded and converted to {selected_format}."
        messagebox.showinfo("Success", msg)

    threading.Thread(target=task, daemon=True).start()

# GUI Setup
app = ctk.CTk()
app.title("YT Video Downloader")
app.geometry("600x750")
app.configure(fg_color="#2e2e32")
app.attributes("-alpha", 0.95)

ctk.CTkLabel(app, text="YouTube URL:", font=("Arial", 14), text_color="white").pack(pady=(15, 5))
url_entry = ctk.CTkEntry(app, width=500, fg_color="#3a3a3f", border_color="#5a5a5f")
url_entry.pack()

# Format + Delete checkbox frame
format_frame = ctk.CTkFrame(app, fg_color="transparent")
format_frame.pack(pady=(15, 5))

ctk.CTkLabel(format_frame, text="Convert To Format:", font=("Arial", 14), text_color="white").grid(row=0, column=0, padx=5, pady=5)
format_option_menu = ctk.CTkOptionMenu(
    format_frame,
    values=["default", "mp4", "mp3", "mkv", "webm", "wav"],
    fg_color="#3a3a3f",
    button_color="#5a5a5f",
    command=on_format_change
)
format_option_menu.set("default")
format_option_menu.grid(row=0, column=1, padx=5)

delete_checkbox = ctk.CTkCheckBox(format_frame, text="Delete original after conversion", text_color="white", state="disabled")
delete_checkbox.grid(row=0, column=2, padx=10)

# Time inputs
ctk.CTkLabel(app, text="Start Time (e.g. 00:01:00):", font=("Arial", 14), text_color="white").pack(pady=(15, 5))
start_time_entry = ctk.CTkEntry(app, width=300, fg_color="#3a3a3f", border_color="#5a5a5f")
start_time_entry.pack()

ctk.CTkLabel(app, text="End Time (e.g. 00:03:00):", font=("Arial", 14), text_color="white").pack(pady=(10, 5))
end_time_entry = ctk.CTkEntry(app, width=300, fg_color="#3a3a3f", border_color="#5a5a5f")
end_time_entry.pack()

# Folder selection and controls
folder_label = ctk.CTkLabel(app, text="No folder selected.", font=("Arial", 12), text_color="lightgray")
folder_label.pack(pady=(15, 5))

ctk.CTkButton(app, text="Choose Folder", command=choose_folder, fg_color=button_color, hover_color=hover_button_color).pack()

remember_checkbox = ctk.CTkCheckBox(app, text="Remember folder (this session)", text_color="white")
remember_checkbox.pack(pady=(5, 10))

download_button = ctk.CTkButton(
    app,
    text="Download",
    command=download_video,
    fg_color=button_color,
    hover_color=hover_button_color,
    state="disabled"
)
download_button.pack(pady=10)

progress_bar = ctk.CTkProgressBar(app, width=500)
progress_bar.set(0)
progress_bar.pack(pady=(10, 10))

ctk.CTkLabel(app, text="Download Log:", font=("Arial", 14), text_color="white").pack(pady=(5, 5))
log_box = ctk.CTkTextbox(app, width=550, height=200, fg_color="#1e1e22", text_color="white")
log_box.pack(pady=(0, 20))

app.mainloop()
