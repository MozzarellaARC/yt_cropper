# ========== GUI ========== 
import tkinter as tk
from tkinter import ttk, filedialog

import subprocess
import os
import shutil
import sys
import re
from tkinter import messagebox

root = tk.Tk()
root.title("YouTube Multi Trim + Cropper")
root.configure(bg="#f0f0f0")

style = ttk.Style()
style.configure("TLabel", font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 10))
style.configure("TEntry", padding=5)

frame = ttk.Frame(root, padding=10)
frame.grid(row=0, column=0, sticky="nsew")

frame.grid_columnconfigure(0, weight=0)
frame.grid_columnconfigure(1, weight=1)
frame.grid_columnconfigure(2, weight=0)

url_entry = ttk.Entry(frame)
start_entry = ttk.Entry(frame)
end_entry = ttk.Entry(frame)
output_dir_entry = ttk.Entry(frame)
base_name_entry = ttk.Entry(frame)


resolution_var = tk.StringVar(value="")
trim_var = tk.BooleanVar(value=True)
crop_var = tk.BooleanVar(value=True)
status_var = tk.StringVar(value="")

format_id_map = {}  # global map for resolution -> format ID
segment_list = []  # global list of trim segments

def add_labeled_row(row, label, entry, pad_top=3):
    pady = (pad_top, 0)
    ttk.Label(frame, text=label).grid(row=row, column=0, sticky="e", padx=(0, 5), pady=pady)
    entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=pady, columnspan=2)

add_labeled_row(0, "YouTube URL:", url_entry)
add_labeled_row(1, "Output Directory:", output_dir_entry)
add_labeled_row(2, "Base File Name:", base_name_entry)
add_labeled_row(3, "Start Time (HH:MM:SS):", start_entry, pad_top=25)
add_labeled_row(4, "End Time (HH:MM:SS):", end_entry)

def browse_output_dir():
    d = filedialog.askdirectory()
    if d:
        output_dir_entry.delete(0, tk.END)
        output_dir_entry.insert(0, d)

ttk.Button(frame, text="Browse", command=browse_output_dir).grid(row=1, column=3, sticky="w", padx=5)

def add_segment():
    start = start_entry.get().strip()
    end = end_entry.get().strip()
    if start and end:
        segment_list.append((start, end))
        segments_box.insert(tk.END, f"{start} - {end}")
        start_entry.delete(0, tk.END)
        end_entry.delete(0, tk.END)

def remove_segment():
    selected = segments_box.curselection()
    if selected:
        idx = selected[0]
        segment_list.pop(idx)
        segments_box.delete(idx)

ttk.Button(frame, text="+ Add Segment", command=add_segment).grid(row=5, column=1, sticky="w", padx=5, pady=3)
ttk.Button(frame, text="- Remove Segment", command=remove_segment).grid(row=5, column=2, sticky="w", padx=5, pady=3)

ttk.Label(frame, text="Trim Segments:").grid(row=6, column=0, sticky="ne", padx=(0, 5), pady=3)
segments_box = tk.Listbox(frame, height=4, width=40)
segments_box.grid(row=6, column=1, columnspan=2, sticky="ew", pady=3)

ttk.Label(frame, text="Resolution:").grid(row=7, column=0, sticky="e", padx=(0, 5), pady=3)
resolution_menu = ttk.OptionMenu(frame, resolution_var, "")
resolution_menu.grid(row=7, column=1, sticky="w", padx=(0, 5), pady=3)
ttk.Button(frame, text="Fetch Resolutions", command=lambda: fetch_resolutions()).grid(row=7, column=2, sticky="w", pady=3)

checkbox_frame = ttk.Frame(frame)
checkbox_frame.grid(row=8, column=0, columnspan=3, sticky="w", pady=5)
ttk.Checkbutton(checkbox_frame, text="Trim video (multiple segments)", variable=trim_var).grid(row=0, column=0, sticky="w", padx=5)
ttk.Checkbutton(checkbox_frame, text="Crop to 9:16 vertical (auto-safe)", variable=crop_var).grid(row=0, column=1, sticky="w", padx=5)

ttk.Button(frame, text="Download & Process", command=lambda: run_process()).grid(row=9, column=0, columnspan=3, pady=10)
status_label = ttk.Label(frame, textvariable=status_var, foreground="green")
status_label.grid(row=10, column=0, columnspan=3, pady=(0, 5))

# ========== Backend Logic ========== 
def resource_path(relative_path):
    """ Get the absolute path to a resource (handles PyInstaller and normal run) """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.abspath(relative_path)

def fetch_resolutions():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("Missing Info", "Please enter a YouTube URL.")
        return

    try:
        status_var.set("Fetching formats...")
        root.update()

        yt_dlp_cmd = [sys.executable, "-m", "yt_dlp", "-F", url]
        result = subprocess.run(yt_dlp_cmd, capture_output=True, text=True)
        lines = result.stdout.splitlines()

        format_map = {}
        for line in lines:
            if 'video only' in line:
                match = re.match(r"^(\d+)\s+(\w+)\s+(\d+x\d+)", line)
                if match:
                    fmt_id, _, res_text = match.groups()
                    _, height = map(int, res_text.split('x'))
                    resolution = f"{height}p"
                    format_map[resolution] = fmt_id

        if not format_map:
            raise Exception("No video-only formats found.")

        menu = resolution_menu["menu"]
        menu.delete(0, "end")
        for res in sorted(format_map.keys(), key=lambda r: int(re.sub("[^0-9]", "", r))):
            menu.add_command(label=res, command=lambda r=res: resolution_var.set(r))

        global format_id_map
        format_id_map = format_map

        resolution_var.set(max(format_map.keys(), key=lambda r: int(re.sub("[^0-9]", "", r))))
        status_var.set("Resolution list updated.")

    except Exception as e:
        status_var.set("Error")
        messagebox.showerror("Error", f"Could not fetch formats:\n{e}")

def get_video_resolution(path):
    ffprobe_path = resource_path("ffprobe.exe")
    result = subprocess.run(
        [ffprobe_path, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", path],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        try:
            w, h = map(int, result.stdout.strip().split('x'))
            return w, h
        except:
            return None
    return None

def run_process():
    url = url_entry.get().strip()
    resolution = resolution_var.get()
    do_trim = trim_var.get()
    do_crop = crop_var.get()
    output_dir = output_dir_entry.get().strip()
    base_name = base_name_entry.get().strip()

    if not url:
        messagebox.showerror("Missing Info", "Please enter a YouTube URL.")
        return
    if not output_dir:
        messagebox.showerror("Missing Info", "Please enter an output directory.")
        return
    if not base_name:
        messagebox.showerror("Missing Info", "Please enter a base name.")
        return
    if do_trim and not segment_list:
        messagebox.showerror("Missing Segments", "Please add at least one trim segment.")
        return
    if resolution not in format_id_map:
        messagebox.showerror("Missing Format", "Please fetch available resolutions first.")
        return

    status_var.set("Preparing...")
    root.update()

    for ext in ['webm', 'mp4', 'mkv']:
        if os.path.exists(f"input.{ext}"):
            os.remove(f"input.{ext}")

    format_id = format_id_map.get(resolution)
    if not format_id:
        messagebox.showerror("Format Error", "Selected resolution format ID not found.")
        return

    output_files = []

    for i, (start, end) in enumerate(segment_list):
        temp_output = os.path.join(output_dir, f"{base_name}_{i+1}.mp4")
        yt_dlp_cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", format_id,
            "--download-sections", f"*{start}-{end}",
            "-o", "temp.%(ext)s",
            url
        ]

        try:
            status_var.set(f"Downloading segment {i+1}...")
            root.update()
            subprocess.run(yt_dlp_cmd, check=True)

            input_file = next((f"temp.{ext}" for ext in ['webm', 'mp4', 'mkv'] if os.path.exists(f"temp.{ext}")), None)
            if not input_file:
                raise FileNotFoundError("Segment download failed.")

            if do_crop:
                res = get_video_resolution(input_file)
                if res is None:
                    raise Exception("Could not detect resolution.")
                w, h = res
                target_width = int(h * 9 / 16)
                if target_width <= w:
                    crop_x = f"(in_w-{target_width})/2"
                    crop_filter = f"crop={target_width}:{h}:{crop_x}:0"
                else:
                    crop_filter = f"scale={int(h * 9 / 16)}:{h}"

                ffmpeg_cmd = [
                    resource_path("ffmpeg.exe"), "-y", "-i", input_file,
                    "-filter:v", crop_filter,
                    "-an", temp_output
                ]
                subprocess.run(ffmpeg_cmd, check=True)
            else:
                shutil.move(input_file, temp_output)

            output_files.append(temp_output)

            if input_file and os.path.exists(input_file):
                os.remove(input_file)

        except subprocess.CalledProcessError as e:
            status_var.set("Error")
            messagebox.showerror("yt-dlp/ffmpeg Error", str(e))
            return
        except Exception as e:
            status_var.set("Error")
            messagebox.showerror("Error", str(e))
            return

    # Combine output segments
    concat_list_path = os.path.join(output_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for file in output_files:
            f.write(f"file '{file}'\n")

    final_output = os.path.join(output_dir, f"{base_name}.mp4")
    concat_cmd = [
        resource_path("ffmpeg.exe"), "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list_path, "-c", "copy", final_output
    ]
    subprocess.run(concat_cmd, check=True)

    status_var.set("All segments saved and combined!")
    messagebox.showinfo("Success", f"Final video saved to:\n{final_output}")

root.mainloop()