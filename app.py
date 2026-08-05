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

try:
    from diffusers import StableVideoDiffusionPipeline
    HAS_DIFFUSERS = True
except ImportError:
    HAS_DIFFUSERS = False

# =========================================================
# 0. SYSTEM LOGGING & DIRECTORY HIERARCHY CONFIGURATION
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [MASTER-BRAIN-CORE] %(message)s",
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
KNOWLEDGE_DIR = os.path.join(DATASET_DIR, "knowledge_notes")
MODELS_DIR = os.path.join(BASE_DIR, "models")
TEMP_DIR = os.path.join(BASE_DIR, "temp_processing")
LEARNING_DB = os.path.join(BASE_DIR, "ai_learning_telemetry.json")

# Master Audit & Second Brain Category Hierarchy
CATEGORY_MAP = {
    "Audit_Chinese_Storytelling": "dataset/audit_chinese_storytelling",
    "Audit_General_Storytelling": "dataset/audit_general_storytelling",
    "Audit_Market_Trends": "dataset/audit_market_trends",
    "Audit_Financial_News": "dataset/audit_financial_news",
    "Audit_Regulatory_Compliance": "dataset/audit_regulatory_compliance",
    "Audit_Forensic_Evidence": "dataset/audit_forensic_evidence",
    "CODE100_Chinese_Sentences": "dataset/code100_chinese",
    "Anime_Illustrative_LoRA": "input_videos/anime_lora",
    "Adult_General_Media": "input_videos/adult_general",
    "Adult_Asian_JAV": "input_videos/adult_asian",
    "Auto-Detect Category": "input_videos/auto_detected"
}

# Ensure all production paths and category directories exist
for subpath in CATEGORY_MAP.values():
    os.makedirs(os.path.join(BASE_DIR, subpath), exist_ok=True)

for dir_path in [INPUT_DIR, OUTPUT_DIR, CONVERTED_DIR, DATASET_DIR, KEYFRAMES_DIR, KNOWLEDGE_DIR, MODELS_DIR, TEMP_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# Threading locks and execution state management
DB_LOCK = threading.Lock()
GPU_LOCK = threading.Lock()
CLIPBOARD_CACHE = ""
IS_WATCHER_RUNNING = True

logging.info(f"Initialized Master Second Brain Environment. Base Path: {BASE_DIR}")
logging.info(f"Hardware Acceleration Status -> PyTorch: {HAS_TORCH}, CUDA: {CUDA_AVAILABLE}, Diffusers: {HAS_DIFFUSERS}")

# =========================================================
# 1. TELEMETRY DATABASE ENGINE
# =========================================================

def load_telemetry_db():
    """Thread-safe retrieval of the active telemetry database."""
    with DB_LOCK:
        if os.path.exists(LEARNING_DB):
            try:
                with open(LEARNING_DB, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        data = {}
                    data.setdefault("learned_videos", {})
                    data.setdefault("knowledge_base", {})
                    return data
            except Exception as e:
                logging.error(f"Failed to load telemetry database: {e}")
                return {"learned_videos": {}, "knowledge_base": {}, "system_metadata": {}, "last_updated": time.time()}
        return {"learned_videos": {}, "knowledge_base": {}, "system_metadata": {}, "last_updated": time.time()}

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

# =========================================================
# 2. SECOND BRAIN TEXT & NOTES INGESTION ENGINE
# =========================================================

def scan_and_index_text_knowledge():
    """Scans and indexes raw text notes, audit briefs, and scripts into the second brain."""
    db = load_telemetry_db()
    db.setdefault("knowledge_base", {})
    
    text_files = glob.glob(os.path.join(KNOWLEDGE_DIR, "**", "*.txt"), recursive=True) + \
                 glob.glob(os.path.join(KNOWLEDGE_DIR, "**", "*.md"), recursive=True) + \
                 glob.glob(os.path.join(KNOWLEDGE_DIR, "**", "*.json"), recursive=True)
                 
    new_docs = 0
    for file_path in text_files:
        rel_key = os.path.relpath(file_path, BASE_DIR)
        mtime = os.path.getmtime(file_path)
        
        if rel_key in db["knowledge_base"] and db["knowledge_base"][rel_key].get("mtime") == mtime:
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                
            words = re.findall(r'\b\w{4,}\b', content.lower())
            freq = {}
            for w in words:
                freq[w] = freq.get(w, 0) + 1
            top_keywords = sorted(freq, key=freq.get, reverse=True)[:12]
            
            db["knowledge_base"][rel_key] = {
                "mtime": mtime,
                "size_kb": round(os.path.getsize(file_path) / 1024, 2),
                "indexed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "top_keywords": top_keywords,
                "char_count": len(content),
                "snippet": content[:300].replace("\n", " ")
            }
            new_docs += 1
        except Exception as e:
            logging.error(f"Error indexing text document {file_path}: {e}")
            
    if new_docs > 0:
        save_telemetry_db(db)
        logging.info(f"Second Brain Note Engine: Ingested {new_docs} new document(s).")
    return len(db["knowledge_base"]), new_docs

def search_second_brain(query_term):
    """Queries both video telemetry assets and indexed knowledge notes."""
    if not query_term or query_term.strip() == "":
        return "Please enter a search term."
        
    db = load_telemetry_db()
    query_lower = query_term.lower()
    results = []
    
    # 1. Search Video Assets
    for path, meta in db.get("learned_videos", {}).items():
        cat = meta.get("category", "")
        if query_lower in path.lower() or query_lower in cat.lower():
            results.append(f"📹 [VIDEO ASSET] {path}\n    └─ Category: {cat} | Res: {meta.get('resolution')} | Duration: {meta.get('duration_sec')}s | Size: {meta.get('file_size_mb')} MB")
            
    # 2. Search Text Knowledge Notes
    for path, meta in db.get("knowledge_base", {}).items():
        keywords = meta.get("top_keywords", [])
        snippet = meta.get("snippet", "")
        if query_lower in path.lower() or any(query_lower in k for k in keywords) or query_lower in snippet.lower():
            results.append(f"📄 [KNOWLEDGE NOTE] {path}\n    └─ Keywords: {', '.join(keywords[:6])}\n    └─ Snippet: \"{snippet[:150]}...\"")
            
    if not results:
        return f"No direct memory matches found for query term: '{query_term}'"
        
    return f"=== SECOND BRAIN MEMORY MATCHES ({len(results)}) ===\n\n" + "\n\n".join(results)

# =========================================================
# 3. OPTICAL FEATURE EXTRACTION & AUTO-LEARNING
# =========================================================

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
    
    learned_videos = db.get("learned_videos", {})
    if file_key in learned_videos:
        if learned_videos[file_key].get("mtime") == mtime:
            return False

    features = extract_video_features(file_path)
    if features is None:
        return False

    features["category"] = category
    features["learned_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    features["mtime"] = mtime
    
    db.setdefault("learned_videos", {})[file_key] = features
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
    
    scan_and_index_text_knowledge()
    return len(db.get("learned_videos", {})), new_learned_count

def background_auto_learning_loop(poll_interval=10):
    """Background monitoring loop that runs continuously."""
    while IS_WATCHER_RUNNING:
        try:
            scan_and_learn_all_videos()
        except Exception as e:
            logging.error(f"Error in auto-learning loop: {e}")
        time.sleep(poll_interval)

watcher_thread = threading.Thread(target=background_auto_learning_loop, daemon=True)
watcher_thread.start()

# =========================================================
# 4. CLIPBOARD SNIFFER AUTOMATION
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
# 5. DATASET CRAWLER, EXTRACTION & AUTO-TAGGER ENGINES
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

    return f"Keyframe Extraction Complete! Saved {total_saved} frames across {len(learned)} learned asset(s)."

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
# 6. ACTION VIDEO GENERATION PIPELINE (GPU + PROCEDURAL)
# =========================================================

def generate_ai_action_video(script_text, init_image, category_target, motion_scale, target_duration_frames):
    """Executes dynamic video synthesis with action movement parameters."""
    if not script_text or script_text.strip() == "":
        script_text = "Master Audit Cinematic Storytelling, dynamic camera action movement, real models, 8k background"

    temp_img_path = None
    if init_image is not None:
        temp_img_path = os.path.join(TEMP_DIR, f"init_seed_{int(time.time())}.png")
        if isinstance(init_image, np.ndarray):
            cv2.imwrite(temp_img_path, cv2.cvtColor(init_image, cv2.COLOR_RGB2BGR))
        elif isinstance(init_image, Image.Image):
            init_image.save(temp_img_path)

    # 1. GPU Diffusion Pipeline Execution (If PyTorch + CUDA + Diffusers active)
    if HAS_TORCH and CUDA_AVAILABLE and HAS_DIFFUSERS:
        try:
            logging.info("Executing GPU Stable Video Diffusion Pipeline...")
            pipe = StableVideoDiffusionPipeline.from_pretrained(
                "stabilityai/stable-video-diffusion-img2vid-xt",
                torch_dtype=torch.float16,
                variant="fp16"
            )
            pipe.enable_model_cpu_offload()

            if temp_img_path and os.path.exists(temp_img_path):
                img_input = Image.open(temp_img_path).convert("RGB").resize((1024, 576))
            else:
                img_input = Image.new("RGB", (1024, 576), color=(20, 20, 30))

            generator = torch.manual_seed(42)
            frames = pipe(
                img_input,
                decode_chunk_size=8,
                generator=generator,
                motion_bucket_id=int(motion_scale),
                noise_aug_strength=0.02,
                num_frames=int(min(target_duration_frames, 25))
            ).frames[0]

            out_filename = f"gen_gpu_action_{int(time.time())}.mp4"
            out_path = os.path.join(OUTPUT_DIR, out_filename)
            writer = cv2.VideoWriter(out_path, cv2.VideoWriter_fourcc(*'mp4v'), 24, (1024, 576))

            for f_frame in frames:
                f_np = np.array(f_frame)
                writer.write(cv2.cvtColor(f_np, cv2.COLOR_RGB2BGR))
            writer.release()

            scan_and_learn_all_videos()
            return out_path, f"GPU Diffusion Video Generation Complete! Exported to: {out_path}"
        except Exception as e:
            logging.error(f"GPU Diffusion Execution Fallback: {e}")

    # 2. High-Performance Procedural Action Movement Engine (Local Fallback)
    output_filename = f"action_story_{int(time.time())}.mp4"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    fps = 30
    w, h = 1280, 720
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

    if temp_img_path and os.path.exists(temp_img_path):
        base_frame = cv2.imread(temp_img_path)
        base_frame = cv2.resize(base_frame, (w, h))
    else:
        base_frame = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.rectangle(base_frame, (0, 0), (w, h), (25, 20, 15), -1)
        cv2.putText(base_frame, "MASTER AUDIT REAL ACTION ENGINE", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)

    total_frames = int(target_duration_frames)
    motion_factor = float(motion_scale) / 50.0

    for i in range(total_frames):
        frame = base_frame.copy()
        
        # Pan / Zoom / Tilt dynamic affine transform
        scale_val = 1.0 + 0.08 * np.sin(i * 0.05 * motion_factor)
        dx = int(25 * np.cos(i * 0.08 * motion_factor))
        dy = int(15 * np.sin(i * 0.08 * motion_factor))
        
        M = np.float32([[scale_val, 0, dx], [0, scale_val, dy]])
        frame = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)
        
        # Action Movement: Tracking sweep & pulse render
        cx = int(w / 2 + 220 * np.sin(i * 0.1 * motion_factor))
        cy = int(h / 2 + 60 * np.cos(i * 0.1 * motion_factor))
        
        overlay = frame.copy()
        cv2.circle(overlay, (cx, cy), 130, (255, 180, 50), -1)
        cv2.addWeighted(overlay, 0.35, frame, 0.65, 0, frame)

        # Telemetry HUD Overlay
        cv2.putText(frame, f"ACTION FRAME: {i+1}/{total_frames} | MOTION BUCKET: {motion_scale}", (40, h - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)

        writer.write(frame)

    writer.release()
    gc.collect()

    # Route output to designated category folder
    target_rel_dir = CATEGORY_MAP.get(category_target, "input_videos/auto_detected")
    target_abs_dir = os.path.join(BASE_DIR, target_rel_dir)
    shutil.copy2(output_path, os.path.join(target_abs_dir, output_filename))
    scan_and_learn_all_videos()

    return output_path, f"Rendered {total_frames} Action Motion Frames to: {output_path}"

def fetch_local_generated_videos():
    """Returns local output MP4 files sorted by timestamp."""
    files = glob.glob(os.path.join(OUTPUT_DIR, "*.mp4"))
    if not files:
        return []
    files.sort(key=os.path.getmtime, reverse=True)
    return files

# =========================================================
# 7. CODE100 CHINESE DATASET PARSER
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
# 8. GRADIO USER INTERFACE
# =========================================================

def get_telemetry_status():
    """Generates telemetry status and raw JSON for display."""
    db = load_telemetry_db()
    learned = db.get("learned_videos", {})
    knowledge = db.get("knowledge_base", {})
    total_videos = len(learned)
    total_notes = len(knowledge)
    categories_summary = {}
    
    total_duration = 0.0
    total_mb = 0.0

    for v_info in learned.values():
        cat = v_info.get("category", "Unknown")
        categories_summary[cat] = categories_summary.get(cat, 0) + 1
        total_duration += v_info.get("duration_sec", 0.0)
        total_mb += v_info.get("file_size_mb", 0.0)

    summary_str = f"=== MASTER SECOND BRAIN & TELEMETRY REPORT ===\n"
    summary_str += f"Total Video Assets Ingested: {total_videos}\n"
    summary_str += f"Total Knowledge Notes/Docs Indexed: {total_notes}\n"
    summary_str += f"Total Analyzed Video Duration: {round(total_duration / 60, 2)} minutes\n"
    summary_str += f"Total Tracked Media Disk Usage: {round(total_mb / 1024, 2)} GB\n\n"
    summary_str += "Category Breakdown:\n"
    
    for cat, count in categories_summary.items():
        summary_str += f"  • [{cat}]: {count} asset(s)\n"
    
    return summary_str, json.dumps(db, indent=2, ensure_ascii=False)

def manual_rescan():
    total, new_found = scan_and_learn_all_videos()
    return f"Rescan Complete! Active Video Total: {total}. Newly Ingested: {new_found}."

custom_css = """
.container { max-width: 1400px; margin: auto; }
.gr-button-primary { background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 100%) !important; border: none !important; }
.status-box { font-family: monospace; font-size: 13px; }
"""

with gr.Blocks() as demo:
    gr.Markdown("# ⚡ Apex AI Studio - DownloadHelper Automation, CUDA 8K Converter & Studio Kernel")
    gr.Markdown("Second Brain Memory | Action Motion Generation | Chinese Storytelling Datasets | Optical Tagger")

    with gr.Tab("📥 Video DownloadHelper & CUDA 8K Converter"):
        gr.Markdown("### Direct Media Export & Batch Downloader")
        refresh_downloads_btn = gr.Button("🔄 Refresh Output Videos List", variant="primary")
        download_dropdown = gr.Dropdown(choices=fetch_local_generated_videos(), label="Select Generated Output Video")
        download_file_widget = gr.File(label="Download Media File Target")

        def update_download_file(selected_path):
            if selected_path and os.path.exists(selected_path):
                return selected_path
            return None

        refresh_downloads_btn.click(
            fn=lambda: gr.update(choices=fetch_local_generated_videos()),
            outputs=[download_dropdown]
        )
        download_dropdown.change(fn=update_download_file, inputs=[download_dropdown], outputs=[download_file_widget])

    with gr.Tab("🎬 AI Learning Video Generator"):
        gr.Markdown("### Full Action Motion & Character Story Video Generator")
        with gr.Row():
            with gr.Column(scale=1):
                script_input = gr.Textbox(
                    label="AI Generation Concept / Full Story Script",
                    placeholder="Paste full script or story narrative here...",
                    lines=8
                )
                seed_image = gr.Image(label="Optional Seed Image / Model Anchor", type="pil")
                gen_category = gr.Dropdown(
                    choices=list(CATEGORY_MAP.keys()),
                    value="Audit_Chinese_Storytelling",
                    label="Target Category Routing"
                )
                motion_slider = gr.Slider(
                    minimum=1,
                    maximum=255,
                    value=180,
                    step=1,
                    label="Motion Bucket / Action Intensity Strength"
                )
                frame_slider = gr.Slider(
                    minimum=30,
                    maximum=300,
                    value=90,
                    step=10,
                    label="Target Frame Count (Duration)"
                )
                generate_video_btn = gr.Button("⚡ Generate Full Action Video Now", variant="primary")

            with gr.Column(scale=1):
                video_preview = gr.Video(label="Rendered Story Preview")
                gen_logs = gr.Textbox(label="Output Logs & Execution Telemetry", lines=6, elem_classes=["status-box"])

        generate_video_btn.click(
            fn=generate_ai_action_video,
            inputs=[script_input, seed_image, gen_category, motion_slider, frame_slider],
            outputs=[video_preview, gen_logs]
        )

    with gr.Tab("🧠 Second Brain Knowledge Search"):
        gr.Markdown("### Query Video Telemetry & Text Notes Memory Bank")
        with gr.Row():
            query_box = gr.Textbox(label="Search Term / Keyword", placeholder="e.g. audit, market, video, chinese, telemetry...", scale=3)
            search_btn = gr.Button("🔍 Search Memory Bank", variant="primary", scale=1)
        
        search_output = gr.Textbox(label="Second Brain Retrieval Results", lines=12, elem_classes=["status-box"])
        search_btn.click(fn=search_second_brain, inputs=[query_box], outputs=[search_output])

    with gr.Tab("📊 Telemetry & Auto-Learning"):
        with gr.Row():
            rescan_btn = gr.Button("🔍 Force Rescan & Ingest Now", variant="primary")
            refresh_btn = gr.Button("🔄 Refresh Metrics Display")
        
        status_output = gr.Textbox(label="Master Summary Report", lines=8, elem_classes=["status-box"])
        db_viewer = gr.Code(label="Live ai_learning_telemetry.json Inspection", language="json")

        rescan_btn.click(fn=manual_rescan, inputs=[], outputs=[status_output]).then(
            fn=get_telemetry_status, inputs=[], outputs=[status_output, db_viewer]
        )
        refresh_btn.click(fn=get_telemetry_status, inputs=[], outputs=[status_output, db_viewer])

    with gr.Tab("✂️ Keyframe Extraction & Auto-Tagger"):
        gr.Markdown("### Automated Frame Bucketing & Optical Captioning")
        with gr.Row():
            extract_btn = gr.Button("🖼️ Extract Keyframes from Learned Assets", variant="primary")
            tag_btn = gr.Button("🏷️ Run Optical Auto-Tagger")
        
        pipeline_log = gr.Textbox(label="Execution Logs", lines=6, elem_classes=["status-box"])
        extract_btn.click(fn=extract_dataset_keyframes, inputs=[], outputs=[pipeline_log])
        tag_btn.click(fn=run_auto_tagger, inputs=[], outputs=[pipeline_log])

    with gr.Tab("🈴 CODE100 Chinese Engine"):
        gr.Markdown("### CODE100 NLP Dataset Manager")
        code100_btn = gr.Button("📖 Inspect Datasets")
        code100_output = gr.Textbox(label="Dataset Analysis", lines=10, elem_classes=["status-box"])
        code100_btn.click(fn=get_code100_summary, inputs=[], outputs=[code100_output])

    demo.load(fn=get_telemetry_status, inputs=[], outputs=[status_output, db_viewer])

# =========================================================
# 9. MAIN ENTRY POINT EXECUTION
# =========================================================

if __name__ == "__main__":
    logging.info("Starting up Master Second Brain & Video pipeline engine...")
    scan_and_learn_all_videos()
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=custom_css
    )