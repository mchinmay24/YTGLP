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

def get_time_from_entries(hour_entry, min_entry, sec_entry):
    h = hour_entry.get().zfill(2) if hour_entry.get().strip() else "00"
    m = min_entry.get().zfill(2) if min_entry.get().strip() else "00"
    s = sec_entry.get().zfill(2) if sec_entry.get().strip() else "00"
    return f"{h}:{m}:{s}"

# Main download function
def download_video():
    if not download_path:
        messagebox.showwarning("No Folder", "Please choose a download folder.")
        return

    url = url_entry.get()
    start_time = get_time_from_entries(start_hour_entry, start_min_entry, start_sec_entry)
    end_time = get_time_from_entries(end_hour_entry, end_min_entry, end_sec_entry)
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

        # Determine if trimming is needed
        if any(x != "00" for x in (start_time.split(":") + end_time.split(":"))):
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
            if selected_format in ["mp3", "wav"]:  # Audio
                download_cmd += ['-x', '--audio-format', selected_format]
            else:  # Video container
                download_cmd += ['--merge-output-format', selected_format]
                    
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

# Start Time Inputs
ctk.CTkLabel(app, text="Start Time (HH:MM:SS):", font=("Arial", 14), text_color="white").pack(pady=(15, 5))
start_time_frame = ctk.CTkFrame(app, fg_color="transparent")
start_time_frame.pack()

start_hour_entry = ctk.CTkEntry(start_time_frame, width=50, placeholder_text="HH")
start_min_entry = ctk.CTkEntry(start_time_frame, width=50, placeholder_text="MM")
start_sec_entry = ctk.CTkEntry(start_time_frame, width=50, placeholder_text="SS")
start_hour_entry.grid(row=0, column=0, padx=5)
start_min_entry.grid(row=0, column=1, padx=5)
start_sec_entry.grid(row=0, column=2, padx=5)

# End Time Inputs
ctk.CTkLabel(app, text="End Time (HH:MM:SS):", font=("Arial", 14), text_color="white").pack(pady=(10, 5))
end_time_frame = ctk.CTkFrame(app, fg_color="transparent")
end_time_frame.pack()

end_hour_entry = ctk.CTkEntry(end_time_frame, width=50, placeholder_text="HH")
end_min_entry = ctk.CTkEntry(end_time_frame, width=50, placeholder_text="MM")
end_sec_entry = ctk.CTkEntry(end_time_frame, width=50, placeholder_text="SS")
end_hour_entry.grid(row=0, column=0, padx=5)
end_min_entry.grid(row=0, column=1, padx=5)
end_sec_entry.grid(row=0, column=2, padx=5)

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
