import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
from PIL import Image
from gtts import gTTS
import torch
from transformers import CLIPModel, CLIPProcessor
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CLIPS_FOLDER = os.path.join(BASE_DIR, "local_clips")
MEMORY_FILE = os.path.join(BASE_DIR, "clip_memory.json")

# Ensure local clips directory exists
os.makedirs(CLIPS_FOLDER, exist_ok=True)

# Device Configuration
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] Visual Memory Core Active on: {device.upper()}")

# Load Neural Network Models
MODEL_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

# Persistent In-Memory Cache
visual_memory = {}


def load_memory():
    global visual_memory
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                visual_memory = json.load(f)
        except Exception:
            visual_memory = {}


def save_memory():
    with open(MEMORY_FILE, "w") as f:
        json.dump(visual_memory, f, indent=2)


def get_ffmpeg_path():
    local_ffmpeg = os.path.join(BASE_DIR, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    return "ffmpeg"


def get_audio_duration(audio_path, ffmpeg_bin):
    cmd = [ffmpeg_bin, "-i", audio_path, "-f", "null", "-"]
    res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            time_str = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = time_str.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 5.0


def extract_keyframe(video_path, ffmpeg_bin):
    thumb_path = video_path + "_thumb.jpg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss",
        "00:00:01",
        "-i",
        video_path,
        "-vframes",
        "1",
        "-q:v",
        "2",
        thumb_path,
    ]
    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    return thumb_path


def absorb_video(video_path):
    """Processes a video into vector representations and saves it to clip_memory.json."""
    file_name = os.path.basename(video_path)
    if file_name in visual_memory:
        return

    ffmpeg_bin = get_ffmpeg_path()
    try:
        thumb_path = extract_keyframe(video_path, ffmpeg_bin)
        if os.path.exists(thumb_path):
            image = Image.open(thumb_path)
            inputs = clip_processor(
                images=image, return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                image_features = clip_model.get_image_features(**inputs)
                image_features = (
                    image_features / image_features.norm(p=2, dim=-1, keepdim=True)
                )

            visual_memory[file_name] = {
                "path": video_path,
                "vector": image_features.cpu().numpy().tolist()[0],
            }
            save_memory()
            os.remove(thumb_path)
            print(f"[+] Absorbed visual memory: {file_name}")
    except Exception as e:
        print(f"[!] Error absorbing {file_name}: {e}")


def scan_and_absorb_all():
    """Initial Pass: Scans local_clips on startup."""
    load_memory()
    for f in os.listdir(CLIPS_FOLDER):
        if f.lower().endswith(".mp4"):
            absorb_video(os.path.join(CLIPS_FOLDER, f))


class AutoAbsorbHandler(FileSystemEventHandler):
    """Watches local_clips folder and absorbs files added in real time."""

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(".mp4"):
            time.sleep(1)
            absorb_video(event.src_path)


def start_folder_watcher():
    event_handler = AutoAbsorbHandler()
    observer = Observer()
    observer.schedule(event_handler, CLIPS_FOLDER, recursive=False)
    observer.daemon = True
    observer.start()


def find_best_clip_from_memory(sentence_text):
    if not visual_memory:
        return None

    inputs = clip_processor(
        text=[sentence_text], return_tensors="pt", padding=True
    ).to(device)
    with torch.no_grad():
        text_features = clip_model.get_text_features(**inputs)
        text_features = (
            text_features / text_features.norm(p=2, dim=-1, keepdim=True)
        )

    best_match = None
    highest_score = -1.0

    for file_name, data in visual_memory.items():
        if not os.path.exists(data["path"]):
            continue

        img_vec = torch.tensor(data["vector"]).to(device)
        score = torch.matmul(text_features, img_vec.T).item()

        if score > highest_score:
            highest_score = score
            best_match = data["path"]

    return best_match


def create_narrated_scene(sentence_text, index, ffmpeg_bin):
    audio_path = os.path.join(BASE_DIR, f"speech_{index}.mp3")
    video_path = os.path.join(BASE_DIR, f"segment_{index}.mp4")

    tts = gTTS(text=sentence_text, lang="en")
    tts.save(audio_path)
    duration = get_audio_duration(audio_path, ffmpeg_bin) + 0.5

    bg_path = find_best_clip_from_memory(sentence_text)

    clean_text = sentence_text.replace("'", "'\\''").replace(":", "\\:")

    if bg_path and os.path.exists(bg_path):
        cmd = [
            ffmpeg_bin,
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            bg_path,
            "-i",
            audio_path,
            "-vf",
            (
                f"scale=1280:720:force_original_aspect_ratio=increase,"
                f"crop=1280:720,"
                f"drawtext=text='{clean_text}':fontcolor=white:fontsize=28:"
                f"x=(w-text_w)/2:y=h-100:box=1:boxcolor=black@0.7:boxborderw=10"
            ),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-t",