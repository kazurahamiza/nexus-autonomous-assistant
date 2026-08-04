# ==============================================================================
# ENVIRONMENT OVERRIDES FOR TRANSFORMERS & TORCHVISION FIX
# ==============================================================================
import os
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"

import sys
import time
import json
import torch
import cv2
import asyncio
import logging
import numpy as np
import subprocess
import shutil
import sqlite3
import datetime
import edge_tts
import yt_dlp
import gradio as gr
import PIL.Image
from PIL import ImageFilter
from mutagen.mp3 import MP3

from diffusers import (
    StableDiffusionControlNetPipeline,
    ControlNetModel,
    DDIMScheduler
)

# Set up logging for tracking system execution
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

# Ensure FFmpeg is registered in current process path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")

if os.path.exists(FFMPEG_PATH):
    os.environ["PATH"] = BASE_DIR + os.path.pathsep + os.environ["PATH"]
    logging.info(f"FFmpeg registered from local path: {FFMPEG_PATH}")
else:
    logging.warning("Local ffmpeg.exe not found in root. Falling back to system PATH.")

# ==============================================================================
# MASTER PATHS & MULTI-DIRECTORY LEARNING TARGETS
# ==============================================================================
DB_PATH = os.path.abspath("./master_registry.db")
OUTPUT_DIR = os.path.abspath("./outputs")
OUTPUT_KNOWLEDGE_FILE = os.path.abspath("./absorbed_data.json")

# Linked Local Learning Directories (Discovered from file explorer screenshots)
TARGET_LEARNING_DIRS = [
    os.path.abspath("./videos"),
    os.path.abspath("./input_videos"),
    os.path.abspath("./self_learning_brutal_ai/videos")
]

# Ensure all target folders exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
for path in TARGET_LEARNING_DIRS:
    os.makedirs(path, exist_ok=True)

SUPPORTED_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.webm')

# ==============================================================================
# DATABASE SETUP
# ==============================================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            filepath TEXT,
            category TEXT,
            timestamp DATETIME
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learned_dataset (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            file_path TEXT,
            category TEXT,
            duration_sec REAL,
            resolution TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# METADATA EXTRACTION & DUAL-FILE LEARNING INDEXER
# ==============================================================================
def get_video_metadata(file_path):
    """Extracts stream and container metadata using FFprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        logging.error(f"FFprobe extraction error for {file_path}: {e}")
    return {}

def index_video_file(file_path, category="Learned Asset"):
    """Extracts metadata, logs to SQLite databases, and updates absorbed_data.json."""
    filename = os.path.basename(file_path)
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    duration = 0.0
    resolution = "Unknown"

    try:
        cap = cv2.VideoCapture(file_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if fps > 0:
                duration = round(frame_count / fps, 2)
            resolution = f"{width}x{height}"
            cap.release()
    except Exception as e:
        logging.warning(f"Metadata extraction error: {e}")

    # 1. Save to SQLite DB
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO assets (filename, filepath, category, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (filename, file_path, category, now_str))

    cursor.execute('''
        INSERT INTO learned_dataset (timestamp, filename, file_path, category, duration_sec, resolution)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (now_str, filename, file_path, category, duration, resolution))

    conn.commit()
    conn.close()

    # 2. Duplicate to absorbed_data.json learning file
    json_data = []
    if os.path.exists(OUTPUT_KNOWLEDGE_FILE):
        try:
            with open(OUTPUT_KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception:
            json_data = []

    json_entry = {
        "timestamp": now_str,
        "filename": filename,
        "file_path": file_path,
        "category": category,
        "duration_sec": duration,
        "resolution": resolution,
        "ffprobe_meta": get_video_metadata(file_path)
    }
    json_data.append(json_entry)

    with open(OUTPUT_KNOWLEDGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=4, ensure_ascii=False)

def scan_and_link_all_directories():
    """Scans all linked folders (videos, input_videos, self_learning_brutal_ai) and indexes all unindexed media files."""
    total_indexed = 0
    for target_dir in TARGET_LEARNING_DIRS:
        if not os.path.exists(target_dir):
            continue
        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    full_path = os.path.abspath(os.path.join(root, file))
                    
                    # Check if file is already logged
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM learned_dataset WHERE file_path = ?", (full_path,))
                    exists = cursor.fetchone()
                    conn.close()

                    if not exists:
                        cat_tag = f"Self-Learned ({os.path.basename(os.path.dirname(full_path))})"
                        index_video_file(full_path, category=cat_tag)
                        total_indexed += 1

    return f"Scan & Sync Complete: Indexed {total_indexed} new video assets into Database & absorbed_data.json."

# Run initial directory linking scan on launch
scan_and_link_all_directories()

# ==============================================================================
# DOWNLOADER FUNCTION (EXACT WEB TITLE & AUTO-INDEX)
# ==============================================================================
def download_video(url, selected_category, custom_tag=""):
    if not url:
        return "Please provide a valid URL.", None

    final_category = custom_tag.strip() if custom_tag.strip() else selected_category
    download_target = TARGET_LEARNING_DIRS[0]  # Default to ./videos

    ydl_opts = {
        'outtmpl': os.path.join(download_target, '%(title)s.%(ext)s'),
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info_dict)

        index_video_file(filepath, final_category)
        return f"Download & Sync Complete: Saved to {filepath} [Tag: {final_category}]", filepath
    except Exception as e:
        return f"Error downloading video: {str(e)}", None

# ==============================================================================
# STUDIO GENERATOR LOGIC (1 MINUTE TO 24 HOURS RUNTIME)
# ==============================================================================
def generate_scene(preset, custom_tag, prompt, negative_prompt, dialogue, duration_hours, duration_minutes, seed):
    total_seconds = (duration_hours * 3600) + (duration_minutes * 60)
    if total_seconds < 60:
        total_seconds = 60
    if total_seconds > 86400:
        total_seconds = 86400

    active_category = custom_tag.strip() if custom_tag.strip() else preset
    formatted_time = str(datetime.timedelta(seconds=total_seconds))
    
    status = (
        f"Initialized sequence generation under category: '{active_category}'. "
        f"Target Runtime: {formatted_time} ({total_seconds} seconds). "
        f"Seed: {seed}. Learning links active."
    )
    return status, None

# ==============================================================================
# DATABASE FETCH HELPERS
# ==============================================================================
def get_vault_assets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT filename, filepath, category, timestamp FROM assets ORDER BY id DESC")
    records = cursor.fetchall()
    conn.close()
    return records

def get_learned_dataset():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, filename, file_path, category, duration_sec, resolution FROM learned_dataset ORDER BY id DESC")
    records = cursor.fetchall()
    conn.close()
    return records

# ==============================================================================
# GRADIO INTERFACE BUILDER
# ==============================================================================
def build_ui():
    CATEGORIES = [
        "System Audit & Compliance",
        "General AI Production",
        "3D Animation & CGI Render",
        "2D Anime & Digital Art",
        "Photorealistic & Cinematic",
        "Stylized Illustration & Concept Art",
        "Cinematic Film & Drama",
        "Sci-Fi & Cyberpunk",
        "Fantasy & Mythological",
        "Action & VFX Motion",
        "Documentary & Educational",
        "Commercial & Product Showcase",
        "ASMR & Voiceover Storytelling",
        "General Adult / Mature Content",
        "Custom Category"
    ]

    with gr.Blocks(title="Apex AI Studio & Universal Downloader") as app:
        gr.Markdown("# 🎬 Apex AI Studio & Linked Learning Engine")
        
        with gr.Tabs():
            # Tab 1: Studio Generator
            with gr.Tab("Studio Generator"):
                with gr.Row():
                    with gr.Column(scale=1):
                        preset = gr.Dropdown(
                            choices=CATEGORIES,
                            value="System Audit & Compliance",
                            label="Production Category Preset"
                        )
                        custom_tag = gr.Textbox(
                            label="Custom Category / Tag Override",
                            placeholder="Type custom tag or category string here..."
                        )
                        prompt = gr.Textbox(
                            lines=3,
                            label="Image Prompt",
                            value="A high-tech master audit room filled with glowing holographic data streams..."
                        )
                        neg_prompt = gr.Textbox(
                            lines=3,
                            label="Negative Prompt",
                            value="(deformed, distorted, disfigured:1.3), poorly drawn face, poorly drawn hands..."
                        )
                        dialogue = gr.Textbox(
                            lines=2,
                            label="Voice Dialogue Track",
                            value="System audit initialized. All neural cores are online and functioning at peak capacity."
                        )
                        
                        gr.Markdown("### Video Target Runtime (1 Minute to 24 Hours)")
                        with gr.Row():
                            duration_hours = gr.Slider(
                                minimum=0, maximum=24, value=0, step=1, label="Hours"
                            )
                            duration_minutes = gr.Slider(
                                minimum=1, maximum=59, value=5, step=1, label="Minutes"
                            )

                        seed = gr.Number(value=42, label="Seed", precision=0)
                        gen_btn = gr.Button("🚀 Generate Video Scene", variant="primary")
                        
                    with gr.Column(scale=1):
                        rendered_video = gr.Video(label="Rendered Video Output")
                        gen_status = gr.Textbox(label="Status Log")

                gen_btn.click(
                    fn=generate_scene,
                    inputs=[preset, custom_tag, prompt, neg_prompt, dialogue, duration_hours, duration_minutes, seed],
                    outputs=[gen_status, rendered_video]
                )

            # Tab 2: Global Video Downloader
            with gr.Tab("Global Video Downloader"):
                gr.Markdown("### Universal Web Video Extraction Engine")
                
                url_input = gr.Textbox(label="Target Video URL", placeholder="https://...")
                cat_dropdown = gr.Dropdown(
                    choices=CATEGORIES,
                    value="General AI Production",
                    label="Assign Category Tag for Indexing"
                )
                custom_download_tag = gr.Textbox(
                    label="Custom Tag (Optional)",
                    placeholder="Type custom category tag to override dropdown..."
                )
                download_btn = gr.Button("⚡ Extract & Download Video", variant="primary")
                status_output = gr.Textbox(label="Engine Status")
                video_output = gr.Video(label="Downloaded Video Preview")

                download_btn.click(
                    fn=download_video,
                    inputs=[url_input, cat_dropdown, custom_download_tag],
                    outputs=[status_output, video_output]
                )

            # Tab 3: Master Video Vault & Linked Learning Index
            with gr.Tab("Master Video Vault & Learning Index"):
                gr.Markdown("### Linked Folders Sync & Scan")
                sync_btn = gr.Button("🔄 Scan & Sync All Local Video Folders (videos, input_videos, self_learning)", variant="secondary")
                sync_log = gr.Textbox(label="Sync Status")

                gr.Markdown("### Asset Registry Index")
                vault_table = gr.Dataframe(
                    headers=["Filename", "Filepath", "Category", "Timestamp"],
                    value=get_vault_assets
                )
                
                gr.Markdown("### Learned Dataset Index (Auto-Indexed)")
                dataset_table = gr.Dataframe(
                    headers=["Timestamp", "Filename", "File Path", "Category", "Duration (Sec)", "Resolution"],
                    value=get_learned_dataset
                )
                
                sync_btn.click(fn=scan_and_link_all_directories, outputs=[sync_log])
                sync_btn.click(fn=get_vault_assets, outputs=[vault_table])
                sync_btn.click(fn=get_learned_dataset, outputs=[dataset_table])

    return app

if __name__ == "__main__":
    app = build_ui()
    app.queue().launch(server_name="127.0.0.1", inbrowser=True)