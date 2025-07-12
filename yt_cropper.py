import yt_dlp
import subprocess
import json

def main():
    # Download video with yt-dlp
    ydl_opts = {'outtmpl': 'video.%(ext)s'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(['https://www.youtube.com/watch?v=jNQXAC9IVRw'])

    # Path to your downloaded ffmpeg.exe and ffprobe.exe
    ffmpeg_path = r"C:\Users\M\Desktop\yt_cropper\ffmpeg.exe"
    ffprobe_path = r"C:\Users\M\Desktop\yt_cropper\ffprobe.exe"

    # Get video dimensions using ffprobe
    probe_cmd = [ffprobe_path, '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', 'video.mp4']
    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
        probe_json = json.loads(probe_result.stdout)
        width = probe_json['streams'][0]['width']
        height = probe_json['streams'][0]['height']
        print(f"Video dimensions: {width}x{height}")
    except Exception as e:
        print("Could not get video dimensions:", e)
        return

    # Set crop size to half the width and height, centered
    crop_w = width // 2
    crop_h = height // 2
    crop_x = (width - crop_w) // 2
    crop_y = (height - crop_h) // 2
    crop_filter = f"crop={crop_w}:{crop_h}:{crop_x}:{crop_y}"
    print(f"Using crop filter: {crop_filter}")

    # Run ffmpeg via subprocess
    ffmpeg_cmd = [
        ffmpeg_path, "-y",
        "-i", "video.mp4",
        "-vf", crop_filter,
        "-c:v", "libx264",
        "-preset", "veryslow",
        "-crf", "24",
        "cropped_video.mp4"
    ]
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
        print("FFmpeg output:", result.stdout)
        print("FFmpeg error output:", result.stderr)
    except subprocess.CalledProcessError as e:
        print("FFmpeg failed:", e.stderr)

if __name__ == "__main__":
    main()