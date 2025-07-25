# ========== Backend Logic ========== 
import subprocess
import os
import shutil
import sys
import re


class YouTubeCropperBackend:
    def __init__(self):
        self.format_id_map = {}  # global map for resolution -> format ID

    def resource_path(self, relative_path):
        """ Get the absolute path to a resource (handles PyInstaller and normal run) """
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.abspath(relative_path)

    def fetch_resolutions(self, url):
        yt_dlp_cmd = [self.resource_path("yt-dlp.exe"), "-F", url]
        result = subprocess.run(yt_dlp_cmd, capture_output=True, text=True)
        lines = result.stdout.splitlines()

        format_map = {}
        for line in lines:
            if 'video only' in line:
                match = re.match(r"^(\d+)\s+(\w+)\s+(\d+x\d+)", line)
                if match:
                    fmt_id, _, resolution_text = match.groups()
                    _, height = map(int, resolution_text.split('x'))
                    resolution = f"{height}p"
                    format_map[resolution] = fmt_id

        return format_map

    def get_video_resolution(self, path):
        ffprobe_path = self.resource_path("ffprobe.exe")
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

    def run_process(self, url, resolution, do_trim, do_crop, output_dir, base_name, segment_list, status_callback):
        # Clean up any existing temp files
        for ext in ['webm', 'mp4', 'mkv']:
            if os.path.exists(f"input.{ext}"):
                os.remove(f"input.{ext}")

        format_id = self.format_id_map.get(resolution)
        if not format_id:
            raise Exception("Selected resolution format ID not found.")

        # If neither trim nor crop, just download the full video and move it
        if not do_trim and not do_crop:
            temp_output = os.path.join(output_dir, f"{base_name}.mp4")
            yt_dlp_cmd = [
                self.resource_path("yt-dlp.exe"),
                "-f", format_id,
                "-o", "temp.%(ext)s",
                url
            ]
            try:
                status_callback("Downloading full video...")
                subprocess.run(yt_dlp_cmd, check=True)
                input_file = next((f"temp.{ext}" for ext in ['webm', 'mp4', 'mkv'] if os.path.exists(f"temp.{ext}")), None)
                if not input_file:
                    raise FileNotFoundError("Download failed.")
                shutil.move(input_file, temp_output)
                if input_file and os.path.exists(input_file):
                    os.remove(input_file)
                return temp_output
            except subprocess.CalledProcessError as e:
                raise Exception(f"yt-dlp Error: {e}")
            except Exception as e:
                raise Exception(str(e))

        output_files = []

        for i, (start, end) in enumerate(segment_list):
            temp_output = os.path.join(output_dir, f"{base_name}_{i+1}.mp4")
            yt_dlp_cmd = [
                self.resource_path("yt-dlp.exe"),
                "-f", format_id,
                "--download-sections", f"*{start}-{end}",
                "-o", "temp.%(ext)s",
                url
            ]

            try:
                status_callback(f"Downloading segment {i+1}...")
                subprocess.run(yt_dlp_cmd, check=True)

                input_file = next((f"temp.{ext}" for ext in ['webm', 'mp4', 'mkv'] if os.path.exists(f"temp.{ext}")), None)
                if not input_file:
                    raise FileNotFoundError("Segment download failed.")

                if do_crop:
                    res = self.get_video_resolution(input_file)
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
                        self.resource_path("ffmpeg.exe"), "-y", "-i", input_file,
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
                raise Exception(f"yt-dlp/ffmpeg Error: {e}")
            except Exception as e:
                raise Exception(str(e))

        # Combine output segments
        concat_list_path = os.path.join(output_dir, "concat_list.txt")
        with open(concat_list_path, "w") as f:
            for file in output_files:
                f.write(f"file '{file}'\n")

        final_output = os.path.join(output_dir, f"{base_name}.mp4")
        concat_cmd = [
            self.resource_path("ffmpeg.exe"), "-y", "-f", "concat", "-safe", "0",
            "-i", concat_list_path, "-c", "copy", final_output
        ]
        subprocess.run(concat_cmd, check=True)

        return final_output
