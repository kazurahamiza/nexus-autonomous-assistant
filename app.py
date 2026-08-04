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
# MASTER PATHS & DATABASE SETUP
# ==============================================================================
DB_PATH = os.path.abspath("./master_registry.db")
OUTPUT_DIR = os.path.abspath("./outputs")
VIDEOS_DIR = os.path.abspath("./videos")
OUTPUT_KNOWLEDGE_FILE = os.path.abspath("./absorbed_data.json")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(VIDEOS_DIR, exist_ok=True)

SUPPORTED_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.webm')

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
# METADATA EXTRACTION & SELF-LEARNING LOGIC
# ==============================================================================
def get_video_metadata(file_path):
    """Uses FFmpeg / FFprobe to extract metadata from video/audio container."""
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

def index_video_file(file_path, category="Dataset Asset"):
    """Extracts metadata via OpenCV/FFprobe and logs into SQLite databases."""
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

# ==============================================================================
# DOWNLOADER FUNCTION (EXACT TITLE & AUTO-INDEX)
# ==============================================================================
def download_video(url, selected_category):
    if not url:
        return "Please provide a valid URL.", None

    ydl_opts = {
        'outtmpl': os.path.join(OUTPUT_DIR, '%(title)s.%(ext)s'),
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filepath = ydl.prepare_filename(info_dict)

        index_video_file(filepath, selected_category)
        return f"Download & Indexing Complete: Saved to {filepath}", filepath
    except Exception as e:
        return f"Error downloading video: {str(e)}", None

# ==============================================================================
# DATABASE FETCH HELPERS
# ==============================================================================
def generate_scene(preset, prompt, negative_prompt, dialogue, seed):
    status = f"Generated scene using preset: {preset} with seed {seed}."
    return status, None

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
    # Master Production Categories List (Extracted from Video Titles & Screenshots)
    CATEGORIES = [
        "System Audit & Compliance",
        "AI Generated (General)",
        "3D CGI Stylized / Render",
        "Cyberpunk & Sci-Fi Erotica",
        "Futanari & Trans AI Art",
        "Hentai & 2D Anime NSFW",
        "Uncensored Hentai & 2D Animation",
        "Cosplay & Parody (Gaming/Anime/Vocaloid)",
        "Step-Family & Domestic Parody",
        "Threesome & Double Penetration (DP)",
        "Gangbang, Orgy & Group Action",
        "Interracial & BWC / BBC",
        "Public, Outdoor & BangBus / Van",
        "BDSM, Bondage, Fetish & Tickling",
        "Office, Workplace & Secretary Roleplay",
        "Fitness, Workout & Massage Roleplay",
        "Japanese, Asian & Korean Amateur / Pro",
        "Sound & ASMR / POV Storytelling",
        "Front Missionary & Doggy POV",
        "Romantic & Passionate",
        "Grinding & Dance Motion",
        "Hardcore & Creampie Compilation",
        "Lesbian & Female Solo",
        "HD Adult / Photorealistic",
        "Verified Amateurs & Real Action",
        "MILF & Mature Fantasy",
        "Exclusive & Conceptual",
        "Cinematic Film & Drama",
        "Fantasy & Digital Illustration",
        "Custom Category"
    ]

    with gr.Blocks(title="Apex AI Studio & Universal Downloader") as app:
        gr.Markdown("# 🎬 Apex AI Studio & Universal Downloader")
        
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
                        seed = gr.Number(value=42, label="Seed", precision=0)
                        gen_btn = gr.Button("🚀 Generate Video Scene", variant="primary")
                        
                    with gr.Column(scale=1):
                        rendered_video = gr.Video(label="Rendered Video Output")
                        gen_status = gr.Textbox(label="Status Log")

                gen_btn.click(
                    fn=generate_scene,
                    inputs=[preset, prompt, neg_prompt, dialogue, seed],
                    outputs=[gen_status, rendered_video]
                )

            # Tab 2: Global Video Downloader
            with gr.Tab("Global Video Downloader"):
                gr.Markdown("### Universal Web Video Extraction Engine")
                gr.Markdown("Paste any video URL from TikTok, YouTube, Twitter/X, Instagram, Facebook, Bilibili, Vimeo, etc.")
                
                url_input = gr.Textbox(label="Target Video URL", placeholder="https://...")
                cat_dropdown = gr.Dropdown(
                    choices=CATEGORIES,
                    value="AI Generated (General)",
                    label="Assign Category Tag for Indexing"
                )
                download_btn = gr.Button("⚡ Extract & Download Video", variant="primary")
                status_output = gr.Textbox(label="Engine Status")
                video_output = gr.Video(label="Downloaded Video Preview")

                download_btn.click(
                    fn=download_video,
                    inputs=[url_input, cat_dropdown],
                    outputs=[status_output, video_output]
                )

            # Tab 3: Master Video Vault & Indexed Dataset
            with gr.Tab("Master Video Vault"):
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
                
                refresh_btn = gr.Button("Refresh Registry & Indexes")
                refresh_btn.click(fn=get_vault_assets, outputs=[vault_table])
                refresh_btn.click(fn=get_learned_dataset, outputs=[dataset_table])

    return app

if __name__ == "__main__":
    app = build_ui()
    app.queue().launch(server_name="127.0.0.1", inbrowser=True)