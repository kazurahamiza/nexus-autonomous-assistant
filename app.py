import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image
from gtts import gTTS
import torch
from transformers import CLIPModel, CLIPProcessor

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CLIPS_FOLDER = os.path.join(BASE_DIR, "local_clips")

# Initialize Neural Net Models
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[*] Visual AI Core Running on: {device.upper()}")

MODEL_NAME = "openai/clip-vit-base-patch32"
clip_model = CLIPModel.from_pretrained(MODEL_NAME).to(device)
clip_processor = CLIPProcessor.from_pretrained(MODEL_NAME)


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
    """Extracts a mid-point thumbnail frame from the video to analyze."""
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


def find_best_semantic_clip(sentence_text, ffmpeg_bin):
    """Visual Neural Network matching: Evaluates video content against text semantics."""
    if not os.path.exists(CLIPS_FOLDER):
        os.makedirs(CLIPS_FOLDER)

    valid_clips = [
        os.path.join(CLIPS_FOLDER, f)
        for f in os.listdir(CLIPS_FOLDER)
        if f.lower().endswith(".mp4")
    ]

    if not valid_clips:
        return None

    best_match_clip = None
    highest_similarity = -1.0

    for clip_path in valid_clips:
        try:
            # 1. Extract visual keyframe
            thumb_path = extract_keyframe(clip_path, ffmpeg_bin)

            # 2. Process image and text vectors
            image = Image.open(thumb_path)
            inputs = clip_processor(
                text=[sentence_text],
                images=image,
                return_tensors="pt",
                padding=True,
            ).to(device)

            # 3. Neural Forward Pass (Cosine Similarity Calculation)
            with torch.no_grad():
                outputs = clip_model(**inputs)
                logits_per_image = outputs.logits_per_image
                score = logits_per_image.item()

            if score > highest_similarity:
                highest_similarity = score
                best_match_clip = clip_path

            if os.path.exists(thumb_path):
                os.remove(thumb_path)

        except Exception as e:
            print(f"[!] Visual analysis error on {clip_path}: {e}")

    return best_match_clip


def create_narrated_scene(sentence_text, index, ffmpeg_bin):
    audio_path = os.path.join(BASE_DIR, f"speech_{index}.mp3")
    video_path = os.path.join(BASE_DIR, f"segment_{index}.mp4")

    # 1. Voiceover synthesis
    tts = gTTS(text=sentence_text, lang="en")
    tts.save(audio_path)
    duration = get_audio_duration(audio_path, ffmpeg_bin) + 0.5

    # 2. Visual AI Content Matcher
    bg_path = find_best_semantic_clip(sentence_text, ffmpeg_bin)

    clean_text = sentence_text.replace("'", "'\\''").replace(":", "\\:")

    # 3. FFmpeg Assembly
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

    output_path = os.path.join(BASE_DIR, output_name)
    segments_txt_path = os.path.join(BASE_DIR, "segments.txt")
    ffmpeg_bin = get_ffmpeg_path()

    status_label.config(
        text="Status: Executing Neural Vision Pass...", fg="yellow"
    )
    btn.config(state="disabled")

    def worker():
        try:
            if os.path.exists(output_path):
                os.remove(output_path)

            sentences = [
                s.strip()
                for s in story_text.replace("\n", ".").split(".")
                if len(s.strip()) > 2
            ]

            generated_files = []
            total = len(sentences)

            for i, sentence in enumerate(sentences, start=1):
                status_label.config(
                    text=f"Status: Visual Neural Engine matching scene {i}/{total}...",
                    fg="yellow",
                )
                segment_file = create_narrated_scene(sentence, i, ffmpeg_bin)
                generated_files.append(segment_file)

            with open(segments_txt_path, "w", encoding="utf-8") as f:
                for file in generated_files:
                    f.write(f"file '{file}'\n")

            status_label.config(
                text="Status: Stitching final master output...", fg="yellow"
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
                output_path,
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

            if os.path.exists(output_path):
                status_label.config(text="Status: AI Build Complete!", fg="lime")
                messagebox.showinfo(
                    "Success", f"Video output generated at:\n{output_path}"
                )
            else:
                status_label.config(text="Status: Build Failed", fg="red")
                messagebox.showerror(
                    "Error", "Output video was not generated."
                )

        except Exception as e:
            status_label.config(text="Status: Error", fg="red")
            messagebox.showerror("Error", f"Execution failed:\n{e}")
        finally:
            btn.config(state="normal")

    threading.Thread(target=worker, daemon=True).start()


root = tk.Tk()
root.title("Nexus Visual Neural AI Engine")
root.geometry("580x500")
root.configure(bg="#1e1e1e")

tk.Label(
    root,
    text="Nexus Visual AI Video Generator",
    font=("Arial", 16, "bold"),
    fg="white",
    bg="#1e1e1e",
).pack(pady=10)

story_entry = tk.Text(root, font=("Arial", 10), height=10, width=65)
story_entry.pack(padx=20, pady=5)
story_entry.insert(
    "1.0",
    "Enter story script here. Neural networks will evaluate all local videos and pair each sentence with the best visual match.",
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
output_entry.insert(0, "ai_matched_output.mp4")
output_entry.pack(pady=5)

status_label = tk.Label(
    root,
    text="Status: Ready",
    font=("Arial", 10, "italic"),
    fg="white",
    bg="#1e1e1e",
)
status_label.pack(pady=10)

btn = tk.Button(
    root,
    text="Generate AI Matched Video",
    font=("Arial", 12, "bold"),
    bg="#007acc",
    fg="white",
    padx=20,
    pady=10,
    command=run_story_generator,
)
btn.pack(pady=10)

root.mainloop()