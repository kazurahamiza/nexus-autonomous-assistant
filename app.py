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
SAVED_VIDEOS_FOLDER = os.path.join(BASE_DIR, "my_saved_videos")
MEMORY_FILE = os.path.join(BASE_DIR, "clip_memory.json")

os.makedirs(CLIPS_FOLDER, exist_ok=True)
os.makedirs(SAVED_VIDEOS_FOLDER, exist_ok=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] Visual AI Core Active on: {device.upper()}")

MODEL_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)

visual_memory = {}
SUPPORTED_EXTENSIONS = (".mp4", ".mkv", ".jpg", ".png", ".jpeg")


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


def extract_keyframe(media_path, ffmpeg_bin):
    if media_path.lower().endswith((".jpg", ".png", ".jpeg")):
        return media_path

    thumb_path = media_path + "_thumb.jpg"
    cmd = [
        ffmpeg_bin,
        "-y",
        "-ss",
        "00:00:01",
        "-i",
        media_path,
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


def absorb_video(media_path):
    file_name = os.path.basename(media_path)
    if file_name in visual_memory:
        return

    ffmpeg_bin = get_ffmpeg_path()
    thumb_path = None
    try:
        thumb_path = extract_keyframe(media_path, ffmpeg_bin)
        if os.path.exists(thumb_path):
            image = Image.open(thumb_path)
            inputs = clip_processor(images=image, return_tensors="pt").to(
                device
            )
            with torch.no_grad():
                image_features = clip_model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(
                    p=2, dim=-1, keepdim=True
                )

            visual_memory[file_name] = {
                "path": media_path,
                "vector": image_features.cpu().numpy().tolist()[0],
            }
            save_memory()
            print(f"[+] Absorbed memory: {file_name}")
    except Exception as e:
        print(f"[!] Error absorbing {file_name}: {e}")
    finally:
        if (
            thumb_path
            and thumb_path != media_path
            and os.path.exists(thumb_path)
        ):
            try:
                os.remove(thumb_path)
            except Exception:
                pass


def scan_and_absorb_all():
    load_memory()
    for f in os.listdir(CLIPS_FOLDER):
        if f.lower().endswith(SUPPORTED_EXTENSIONS):
            absorb_video(os.path.join(CLIPS_FOLDER, f))


class AutoAbsorbHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(
            SUPPORTED_EXTENSIONS
        ):
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
        text_features = text_features / text_features.norm(
            p=2, dim=-1, keepdim=True
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
        if bg_path.lower().endswith((".jpg", ".png", ".jpeg")):
            cmd = [
                ffmpeg_bin,
                "-y",
                "-loop",
                "1",
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
                str(duration),
                video_path,
            ]
        else:
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
                str(duration),
                video_path,
            ]
    else:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=0x111122:s=1280x720:r=30:d={duration}",
            "-i",
            audio_path,
            "-vf",
            (
                f"drawtext=text='{clean_text}':fontcolor=white:fontsize=28:"
                f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.6:boxborderw=10"
            ),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            video_path,
        ]

    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    if os.path.exists(audio_path):
        os.remove(audio_path)

    return video_path


def run_story_generator():
    story_text = story_entry.get("1.0", tk.END).strip()
    output_name = output_entry.get().strip()

    if not story_text:
        messagebox.showerror("Error", "Please enter story text first!")
        return

    personal_archive_path = os.path.join(SAVED_VIDEOS_FOLDER, output_name)
    segments_txt_path = os.path.join(BASE_DIR, "segments.txt")
    ffmpeg_bin = get_ffmpeg_path()

    status_label.config(
        text="Status: Querying Visual Memory Core...", fg="yellow"
    )
    btn.config(state="disabled")

    def worker():
        try:
            if os.path.exists(personal_archive_path):
                os.remove(personal_archive_path)

            sentences = [
                s.strip()
                for s in story_text.replace("\n", ".").split(".")
                if len(s.strip()) > 2
            ]

            generated_files = []
            total = len(sentences)

            for i, sentence in enumerate(sentences, start=1):
                status_label.config(
                    text=f"Status: Matching scene {i}/{total} from memory...",
                    fg="yellow",
                )
                segment_file = create_narrated_scene(sentence, i, ffmpeg_bin)
                generated_files.append(segment_file)

            with open(segments_txt_path, "w", encoding="utf-8") as f:
                for file in generated_files:
                    f.write(f"file '{file}'\n")

            status_label.config(
                text="Status: Stitching final master video...", fg="yellow"
            )

            cmd = [
                ffmpeg_bin,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                segments_txt_path,
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                personal_archive_path,
            ]

            subprocess.run(
                cmd,
                cwd=BASE_DIR,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            for f_path in generated_files:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                    except Exception:
                        pass

            if os.path.exists(segments_txt_path):
                try:
                    os.remove(segments_txt_path)
                except Exception:
                    pass

            if os.path.exists(personal_archive_path):
                status_label.config(
                    text="Status: Duplicating video to local_clips for AI learning...",
                    fg="cyan",
                )

                auto_clip_name = f"learned_{int(time.time())}_{output_name}"
                ai_learning_path = os.path.join(CLIPS_FOLDER, auto_clip_name)
                shutil.copy(personal_archive_path, ai_learning_path)

                absorb_video(ai_learning_path)

                status_label.config(
                    text="Status: Master Saved & AI Duplicate Absorbed!",
                    fg="lime",
                )
                messagebox.showinfo(
                    "Success",
                    f"1. Saved to personal records:\n{personal_archive_path}\n\n"
                    f"2. Duplicated and absorbed by AI:\n{ai_learning_path}",
                )
            else:
                status_label.config(text="Status: Build Failed", fg="red")
                messagebox.showerror(
                    "Error", "Master output video was not created."
                )

        except Exception as e:
            status_label.config(text="Status: Error", fg="red")
            messagebox.showerror("Error", f"Execution failed:\n{e}")
        finally:
            btn.config(state="normal")

    threading.Thread(target=worker, daemon=True).start()


threading.Thread(target=scan_and_absorb_all, daemon=True).start()
start_folder_watcher()

root = tk.Tk()
root.title("Nexus Dual-Output Visual AI Engine")
root.geometry("580x500")
root.configure(bg="#1e1e1e")

tk.Label(
    root,
    text="Nexus Dual-Output Visual AI Generator",
    font=("Arial", 16, "bold"),
    fg="white",
    bg="#1e1e1e",
).pack(pady=10)

story_entry = tk.Text(root, font=("Arial", 10), height=10, width=65)
story_entry.pack(padx=20, pady=5)
story_entry.insert(
    "1.0",
    "Enter story script here. Final outputs are archived in my_saved_videos/ and duplicated into local_clips/ for AI self-learning.",
)

frame_out = tk.Frame(root, bg="#1e1e1e")
frame_out.pack(fill="x", padx=20, pady=5)

tk.Label(
    frame_out,
    text="Output File Name:",
    font=("Arial", 10),
    fg="white",
    bg="#1e1e1e",
).pack(anchor="w")

output_entry = tk.Entry(frame_out, font=("Arial", 10), width=60)
output_entry.insert(0, "record_master_output.mp4")
output_entry.pack(pady=5)

status_label = tk.Label(
    root,
    text="Status: Dual-Output System Active & Learning...",
    font=("Arial", 10, "italic"),
    fg="lime",
    bg="#1e1e1e",
)
status_label.pack(pady=10)

btn = tk.Button(
    root,
    text="Generate & Archive Video",
    font=("Arial", 12, "bold"),
    bg="#007acc",
    fg="white",
    padx=20,
    pady=10,
    command=run_story_generator,
)
btn.pack(pady=10)

root.mainloop()