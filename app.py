import os
import sys
import json
import time
import logging
import subprocess
import socket
import concurrent.futures
import asyncio
import re
import gc
import threading
import shutil
import glob
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import cv2
import numpy as np
import gradio as gr

# =========================================================
# OPTIONAL DEPENDENCY CHECKS & SYSTEM INTEGRATIONS
# =========================================================

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

try:
    import torch
    HAS_TORCH = True
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    HAS_TORCH = False
    CUDA_AVAILABLE = False

# =========================================================
# 0. SYSTEM LOGGING & DIRECTORY HIERARCHY CONFIGURATION
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [AI-CORE] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("system_pipeline.log", encoding="utf-8")
    ]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_videos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
CONVERTED_DIR = os.path.join(BASE_DIR, "converted_8k_videos")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
KEYFRAMES_DIR = os.path.join(DATASET_DIR, "extracted_keyframes")
MODELS_DIR = os.path.join(BASE_DIR, "models")
TEMP_DIR = os.path.join(BASE_DIR, "temp_processing")
LEARNING_DB = os.path.join(BASE_DIR, "ai_learning_telemetry.json")

CATEGORY_MAP = {
    "Auto-Detect Category": "input_videos/auto_detected",
    "Adult_General_Media": "input_videos/adult_general",
    "Adult_Asian_JAV": "input_videos/adult_asian",
    "CODE100_Chinese_Sentences": "dataset/code100_chinese",
    "Anime_Illustrative_LoRA": "input_videos/anime_lora",
    "General_Datasets": "input_videos/general"
}

# Ensure all production paths and category directories exist
for subpath in CATEGORY_MAP.values():
    os.makedirs(os.path.join(BASE_DIR, subpath), exist_ok=True)

for dir_path in [INPUT_DIR, OUTPUT_DIR, CONVERTED_DIR, DATASET_DIR, KEYFRAMES_DIR, MODELS_DIR, TEMP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Threading locks and execution state management
DB_LOCK = threading.Lock()
GPU_LOCK = threading.Lock()
CLIPBOARD_CACHE = ""
IS_WATCHER_RUNNING = True

logging.info(f"Initialized Core Environment. Base Path: {BASE_DIR}")
logging.info(f"Hardware Acceleration Status -> PyTorch: {HAS_TORCH}, CUDA: {CUDA_AVAILABLE}")

# =========================================================
# 1. AI TELEMETRY & AUTO-LEARNING ENGINE
# =========================================================

def load_telemetry_db():
    """Thread-safe retrieval of the active telemetry database."""
    with DB_LOCK:
        if os.path.exists(LEARNING_DB):
            try:
                with open(LEARNING_DB, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load telemetry database: {e}")
                return {"learned_videos": {}, "system_metadata": {}, "last_updated": time.time()}
        return {"learned_videos": {}, "system_metadata": {}, "last_updated": time.time()}

def save_telemetry_db(data):
    """Thread-safe persistent storage of telemetry metrics."""
    with DB_LOCK:
        data["last_updated"] = time.time()
        try:
            temp_db_path = LEARNING_DB + ".tmp"
            with open(temp_db_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_db_path, LEARNING_DB)
        except Exception as e:
            logging.error(f"Failed to persist telemetry database: {e}")

def compute_frame_descriptors(frame):
    """Extracts optical, color space, and perceptual sharpness metrics from a frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    color_means = frame.mean(axis=(0, 1)).tolist()
    edges = cv2.Canny(gray, 100, 200)
    edge_density = float(np.count_nonzero(edges) / (frame.shape[0] * frame.shape[1]))

    return {
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "sharpness_laplacian": round(laplacian_var, 2),
        "edge_density": round(edge_density, 4),
        "mean_bgr": [round(c, 2) for c in color_means]
    }

def extract_video_features(file_path):
    """Extracts video specs and samples metrics across multiple timeline points."""
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        return None

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return None

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = frame_count / fps if fps > 0 else 0.0

    if frame_count <= 0 or duration == 0:
        cap.release()
        return None

    sample_ratios = [0.10, 0.25, 0.50, 0.75, 0.90]
    frame_descriptors = []

    for ratio in sample_ratios:
        target_frame = int(frame_count * ratio)
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        if ret and frame is not None:
            descriptors = compute_frame_descriptors(frame)
            frame_descriptors.append(descriptors)

    cap.release()
    if not frame_descriptors:
        return None

    avg_brightness = float(np.mean([d["brightness"] for d in frame_descriptors]))
    avg_contrast = float(np.mean([d["contrast"] for d in frame_descriptors]))
    avg_sharpness = float(np.mean([d["sharpness_laplacian"] for d in frame_descriptors]))
    avg_edge_density = float(np.mean([d["edge_density"] for d in frame_descriptors]))

    return {
        "resolution": f"{width}x{height}",
        "width": width,
        "height": height,
        "aspect_ratio": round(width / height, 2) if height > 0 else 0,
        "fps": round(fps, 2),
        "total_frames": frame_count,
        "duration_sec": round(duration, 2),
        "file_size_mb": round(os.path.getsize(file_path) / (1024 * 1024), 2),
        "telemetry_metrics": {
            "avg_brightness": round(avg_brightness, 2),
            "avg_contrast": round(avg_contrast, 2),
            "avg_sharpness": round(avg_sharpness, 2),
            "avg_edge_density": round(avg_edge_density, 4),
            "samples_analyzed": len(frame_descriptors)
        }
    }

def process_single_video(file_path, category, db):
    """Processes an unlearned or modified video file, updating the telemetry DB."""
    file_key = os.path.relpath(file_path, BASE_DIR)
    mtime = os.path.getmtime(file_path)
    
    if file_key in db["learned_videos"]:
        if db["learned_videos"][file_key].get("mtime") == mtime:
            return False

    features = extract_video_features(file_path)
    if features is None:
        return False

    features["category"] = category
    features["learned_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    features["mtime"] = mtime
    
    db["learned_videos"][file_key] = features
    return True

def scan_and_learn_all_videos():
    """Scans all input directories and processes new or updated video files."""
    db = load_telemetry_db()
    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv', '.m4v')
    new_learned_count = 0

    for cat_name, rel_path in CATEGORY_MAP.items():
        abs_dir = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(abs_dir):
            continue

        for root, _, files in os.walk(abs_dir):
            for file in files:
                if file.lower().endswith(video_extensions):
                    full_path = os.path.join(root, file)
                    if process_single_video(full_path, cat_name, db):
                        new_learned_count += 1

    if new_learned_count > 0:
        save_telemetry_db(db)
        logging.info(f"Auto-learning scan complete. Ingested {new_learned_count} asset(s).")
    
    return len(db["learned_videos"]), new_learned_count

def background_auto_learning_loop(poll_interval=10):
    """Background monitoring loop that runs continuously."""
    logging.info("Auto-Learning background watcher active.")
    while IS_WATCHER_RUNNING:
        try:
            scan_and_learn_all_videos()
        except Exception as e:
            logging.error(f"Error in auto-learning loop: {e}")
        time.sleep(poll_interval)

watcher_thread = threading.Thread(target=background_auto_learning_loop, daemon=True)
watcher_thread.start()

# =========================================================
# 2. CLIPBOARD SNIFFER AUTOMATION
# =========================================================

def clipboard_sniffer_loop(poll_interval=2):
    """Monitors OS clipboard for video paths or URLs to ingest."""
    global CLIPBOARD_CACHE
    if not HAS_PYPERCLIP:
        return

    video_exts = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv')
    while IS_WATCHER_RUNNING:
        try:
            current_clip = pyperclip.paste().strip().strip('"').strip("'")
            if current_clip and current_clip != CLIPBOARD_CACHE:
                CLIPBOARD_CACHE = current_clip
                if os.path.exists(current_clip) and current_clip.lower().endswith(video_exts):
                    dest_dir = os.path.join(BASE_DIR, CATEGORY_MAP["Auto-Detect Category"])
                    dest_path = os.path.join(dest_dir, os.path.basename(current_clip))
                    if not os.path.exists(dest_path):
                        logging.info(f"Clipboard sniffer ingesting: {current_clip}")
                        shutil.copy2(current_clip, dest_path)
                        scan_and_learn_all_videos()
        except Exception as e:
            logging.error(f"Error in clipboard sniffer: {e}")
        time.sleep(poll_interval)

clipboard_thread = threading.Thread(target=clipboard_sniffer_loop, daemon=True)
clipboard_thread.start()

# =========================================================
# 3. DATASET CRAWLER, EXTRACTION & AUTO-TAGGER ENGINES
# =========================================================

def resize_and_bucket_frame(image, target_size=1024):
    """Resizes frames into neural network aspect-ratio buckets."""
    h, w, _ = image.shape
    aspect = w / h
    if aspect > 1.0:
        new_w = target_size
        new_h = int(target_size / aspect)
    else:
        new_h = target_size
        new_w = int(target_size * aspect)
    new_w = max((new_w // 64) * 64, 64)
    new_h = max((new_h // 64) * 64, 64)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

def extract_dataset_keyframes(frame_interval=30):
    """Extracts high-sharpness keyframes from learned videos into dataset buckets."""
    db = load_telemetry_db()
    learned = db.get("learned_videos", {})
    total_saved = 0

    for rel_path, meta in learned.items():
        full_path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(full_path):
            continue

        cap = cv2.VideoCapture(full_path)
        if not cap.isOpened():
            continue

        video_name = os.path.splitext(os.path.basename(rel_path))[0]
        out_folder = os.path.join(KEYFRAMES_DIR, video_name)
        os.makedirs(out_folder, exist_ok=True)

        avg_sharp = meta.get("telemetry_metrics", {}).get("avg_sharpness", 100.0)
        min_sharp = max(50.0, avg_sharp * 0.7)

        frame_id = 0
        video_saved = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            if frame_id % frame_interval == 0:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                if sharpness >= min_sharp:
                    bucketed = resize_and_bucket_frame(frame)
                    cv2.imwrite(os.path.join(out_folder, f"frame_{frame_id:06d}.png"), bucketed)
                    video_saved += 1
            frame_id += 1

        cap.release()
        total_saved += video_saved

    return f"Extraction Complete! Saved {total_saved} keyframes across {len(learned)} learned video(s)."

def run_auto_tagger():
    """Generates optical tag files (.txt) alongside extracted dataset keyframes."""
    color_ranges = {
        "red": ([0, 50, 50], [10, 255, 255]),
        "blue": ([100, 50, 50], [130, 255, 255]),
        "green": ([35, 50, 50], [85, 255, 255]),
        "yellow": ([20, 50, 50], [35, 255, 255]),
        "purple": ([130, 50, 50], [160, 255, 255]),
    }

    image_files = glob.glob(os.path.join(KEYFRAMES_DIR, "**", "*.png"), recursive=True) + \
                  glob.glob(os.path.join(KEYFRAMES_DIR, "**", "*.jpg"), recursive=True)

    tagged = 0
    for img_path in image_files:
        txt_path = os.path.splitext(img_path)[0] + ".txt"
        if os.path.exists(txt_path):
            continue

        img = cv2.imread(img_path)
        if img is None:
            continue

        h, w, _ = img.shape
        tags = [os.path.basename(os.path.dirname(img_path)).replace("_", " ")]

        aspect = w / h
        tags.append("square aspect" if 0.95 <= aspect <= 1.05 else ("landscape" if aspect > 1.05 else "portrait"))
        tags.append(f"{w}x{h}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        tags.append("dark lighting" if brightness < 60 else ("bright lighting" if brightness > 190 else "balanced lighting"))

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        for color_name, (lower, upper) in color_ranges.items():
            mask = cv2.inRange(hsv, np.array(lower, dtype="uint8"), np.array(upper, dtype="uint8"))
            if (np.count_nonzero(mask) / (w * h)) > 0.15:
                tags.append(f"{color_name} tone")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(", ".join(tags))
        tagged += 1

    return f"Auto-Tagging Complete! Generated {tagged} new caption tag file(s)."

# =========================================================
# 4. FFMPEG & HARDWARE ACCELERATED TRANSCODING ENGINE
# =========================================================

def apply_illustrative_filter(frame):
    """Bilateral edge cartoon rendering for Anime LoRA dataset prep."""
    color = cv2.bilateralFilter(frame, d=9, sigmaColor=300, sigmaSpace=300)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.medianBlur(gray, 7)
    edges = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 2)
    edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    return cv2.bitwise_and(color, edges_bgr)

def apply_jav_privacy_mask(frame):
    """Dynamic central region pixelation mask."""
    h, w, _ = frame.shape
    box_w, box_h = int(w * 0.4), int(h * 0.4)
    x1, y1 = int((w - box_w) / 2), int((h - box_h) / 2)
    
    roi = frame[y1:y1+box_h, x1:x1+box_w]
    if roi.size > 0:
        small = cv2.resize(roi, (16, 16), interpolation=cv2.INTER_LINEAR)
        frame[y1:y1+box_h, x1:x1+box_w] = cv2.resize(small, (box_w, box_h), interpolation=cv2.INTER_NEAREST)
    return frame

def process_video_pipeline(input_path, category, target_resolution, upscale_factor, apply_stylize, apply_mask):
    """Runs transformations, scaling, and video export."""
    if not input_path or not os.path.exists(input_path):
        return "Error: Invalid input video file."

    filename = os.path.basename(input_path)
    output_path = os.path.join(OUTPUT_DIR, f"processed_{int(time.time())}_{filename}")

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        return "Error: Unable to open video source stream."

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out_w = int(orig_w * upscale_factor)
    out_h = int(orig_h * upscale_factor)

    if target_resolution == "1080p":
        out_w, out_h = 1920, 1080
    elif target_resolution == "4K":
        out_w, out_h = 3840, 2160
    elif target_resolution == "8K":
        out_w, out_h = 7680, 4320

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (out_w, out_h))

    frame_count = 0
    start_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        if category == "Anime_Illustrative_LoRA" or apply_stylize:
            frame = apply_illustrative_filter(frame)
        elif category == "Adult_Asian_JAV" or apply_mask:
            frame = apply_jav_privacy_mask(frame)

        if (out_w, out_h) != (orig_w, orig_h):
            frame = cv2.resize(frame, (out_w, out_h), interpolation=cv2.INTER_CUBIC)

        out.write(frame)
        frame_count += 1

    cap.release()
    out.release()
    gc.collect()

    scan_and_learn_all_videos()
    elapsed = time.time() - start_time
    return f"Pipeline Finished! Rendered {frame_count} frames to: {output_path} (Elapsed: {round(elapsed, 2)}s)"

# =========================================================
# 5. CODE100 CHINESE DATASET PARSER
# =========================================================

def get_code100_summary():
    """Parses CODE100 Chinese dataset directory contents."""
    code100_dir = os.path.join(BASE_DIR, CATEGORY_MAP["CODE100_Chinese_Sentences"])
    if not os.path.exists(code100_dir):
        return "CODE100 folder empty or not created."

    files = glob.glob(os.path.join(code100_dir, "*.*"))
    if not files:
        return "No Chinese dataset files present in path."

    out = f"CODE100 Datasets Detected: {len(files)} files.\n\n"
    for f_path in files:
        out += f"• File: {os.path.basename(f_path)} ({round(os.path.getsize(f_path)/1024, 2)} KB)\n"
    return out

# =========================================================
# 6. GRADIO USER INTERFACE
# =========================================================

def get_telemetry_status():
    """Generates telemetry status and raw JSON for display."""
    db = load_telemetry_db()
    learned = db.get("learned_videos", {})
    total_videos = len(learned)
    categories_summary = {}
    
    total_duration = 0.0
    total_mb = 0.0

    for v_info in learned.values():
        cat = v_info.get("category", "Unknown")
        categories_summary[cat] = categories_summary.get(cat, 0) + 1
        total_duration += v_info.get("duration_sec", 0.0)
        total_mb += v_info.get("file_size_mb", 0.0)

    summary_str = f"=== AI TELEMETRY ENGINE STATUS REPORT ===\n"
    summary_str += f"Total Video Assets Ingested: {total_videos}\n"
    summary_str += f"Total Analyzed Duration: {round(total_duration / 60, 2)} minutes\n"
    summary_str += f"Total Tracked Disk Usage: {round(total_mb / 1024, 2)} GB\n\n"
    summary_str += "Category Breakdown:\n"
    
    for cat, count in categories_summary.items():
        summary_str += f"  • [{cat}]: {count} file(s)\n"
    
    return summary_str, json.dumps(db, indent=2, ensure_ascii=False)

def manual_rescan():
    total, new_found = scan_and_learn_all_videos()
    return f"Rescan Complete! Active Total: {total}. Newly Ingested: {new_found}."

custom_css = """
.container { max-width: 1400px; margin: auto; }
.gr-button-primary { background: linear-gradient(90deg, #4F46E5 0%, #7C3AED 100%) !important; border: none !important; }
.status-box { font-family: monospace; font-size: 13px; }
"""

with gr.Blocks(title="AI Unified Video Processing & Learning Platform", css=custom_css) as demo:
    gr.Markdown("# 🚀 Unified AI Video Processing & Auto-Learning System")
    gr.Markdown("Deep Video Telemetry | Continuous Auto-Learning | Keyframe Extraction | Optical Tagger | Transcoding Engine")

    with gr.Tab("📊 Telemetry & Auto-Learning"):
        with gr.Row():
            rescan_btn = gr.Button("🔍 Force Rescan & Ingest Now", variant="primary")
            refresh_btn = gr.Button("🔄 Refresh Metrics Display")
        
        status_output = gr.Textbox(label="System Summary Report", lines=8, elem_classes=["status-box"])
        db_viewer = gr.Code(label="Live ai_learning_telemetry.json Inspection", language="json")

        rescan_btn.click(fn=manual_rescan, inputs=[], outputs=[status_output]).then(
            fn=get_telemetry_status, inputs=[], outputs=[status_output, db_viewer]
        )
        refresh_btn.click(fn=get_telemetry_status, inputs=[], outputs=[status_output, db_viewer])

    with gr.Tab("✂️ Keyframe Extraction & Auto-Tagger"):
        gr.Markdown("### Automated Frame Bucketing & Prompt Captioning")
        with gr.Row():
            extract_btn = gr.Button("🖼️ Extract Keyframes from Learned Videos", variant="primary")
            tag_btn = gr.Button("🏷️ Run Auto-Tagger Engine")
        
        pipeline_log = gr.Textbox(label="Execution Logs", lines=6, elem_classes=["status-box"])
        extract_btn.click(fn=extract_dataset_keyframes, inputs=[], outputs=[pipeline_log])
        tag_btn.click(fn=run_auto_tagger, inputs=[], outputs=[pipeline_log])

    with gr.Tab("🎬 Video Processing & Scaling"):
        with gr.Row():
            with gr.Column():
                video_input = gr.Video(label="Input Video Asset")
                category_select = gr.Dropdown(choices=list(CATEGORY_MAP.keys()), value="Auto-Detect Category", label="Category Routing")
            with gr.Column():
                resolution_opt = gr.Radio(["Original", "1080p", "4K", "8K"], value="Original", label="Target Resolution Preset")
                scale_slider = gr.Slider(minimum=1.0, maximum=4.0, value=1.0, step=0.25, label="Custom Scale Multiplier")
                with gr.Row():
                    apply_stylize = gr.Checkbox(label="Apply Anime Cartoon Filter", value=False)
                    apply_mask = gr.Checkbox(label="Apply Privacy Pixelation Mask", value=False)

        process_btn = gr.Button("⚡ Execute Processing Pipeline", variant="primary")
        proc_output = gr.Textbox(label="Execution Telemetry", lines=4, elem_classes=["status-box"])

        process_btn.click(
            fn=process_video_pipeline,
            inputs=[video_input, category_select, resolution_opt, scale_slider, apply_stylize, apply_mask],
            outputs=[proc_output]
        )

    with gr.Tab("🈴 CODE100 Chinese Engine"):
        gr.Markdown("### CODE100 NLP Dataset Manager")
        code100_btn = gr.Button("📖 Inspect Datasets")
        code100_output = gr.Textbox(label="Dataset Analysis", lines=10, elem_classes=["status-box"])
        code100_btn.click(fn=get_code100_summary, inputs=[], outputs=[code100_output])

    demo.load(fn=get_telemetry_status, inputs=[], outputs=[status_output, db_viewer])

# =========================================================
# 7. MAIN ENTRY POINT EXECUTION
# =========================================================

if __name__ == "__main__":
    logging.info("Starting up unified pipeline engine...")
    scan_and_learn_all_videos()
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)