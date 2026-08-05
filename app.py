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
from PIL import Image, ImageDraw
import cv2
import numpy as np
import gradio as gr

# Try importing pyperclip for clipboard sniffing automation
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

# ==========================================
# 0. SYSTEM LOGGING & DIRECTORY CONFIGURATION
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_videos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
CONVERTED_DIR = os.path.join(BASE_DIR, "converted_8k_videos")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")
MODELS_DIR = os.path.join(BASE_DIR, "models")
LEARNING_DB = os.path.join(BASE_DIR, "ai_learning_telemetry.json")

CATEGORY_MAP = {
    "Auto-Detect Category": "input_videos/auto_detected",
    "Adult_General_Media": "input_videos/adult_general",
    "Adult_Asian_JAV": "input_videos/adult_asian",
    "CODE100_Chinese_Sentences": "dataset/code100_chinese",
    "Anime_Illustrative_LoRA": "input_videos/anime_lora",
    "General_Datasets": "input_videos/general"
}

for path in CATEGORY_MAP.values():
    os.makedirs(os.path.join(BASE_DIR, path), exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CONVERTED_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)


# ==========================================
# 1. CATEGORY ROUTING ENGINE
# ==========================================

def auto_detect_category_from_url(url: str) -> str:
    url_lower = url.lower()
    if any(k in url_lower for k in ["spankbang", "pornhub", "xvideos", "redtube", "adult"]):
        if any(k in url_lower for k in ["japanese", "jav", "uncensored", "asian"]):
            return "Adult_Asian_JAV"
        return "Adult_General_Media"
    elif "anime" in url_lower or "hentai" in url_lower:
        return "Anime_Illustrative_LoRA"
    elif "chinese" in url_lower or "code100" in url_lower:
        return "CODE100_Chinese_Sentences"
    return "General_Datasets"


# ==========================================
# 2. TELEMETRY ENGINE
# ==========================================

class AISelfLearningEngine:
    @staticmethod
    def load_telemetry():
        if os.path.exists(LEARNING_DB):
            try:
                with open(LEARNING_DB, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"generation_count": 0, "learned_weights": {"contrast": 1.1, "sharpness": 1.2, "saturation": 1.05}, "history": []}

    @staticmethod
    def save_telemetry(data):
        with open(LEARNING_DB, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def optimize_prompt(cls, raw_prompt: str, style: str) -> str:
        telemetry = cls.load_telemetry()
        telemetry["generation_count"] = telemetry.get("generation_count", 0) + 1
        enhanced_prompt = f"{raw_prompt}, full body realistic adult model, vivid sensual motion, style={style}, 8k UHD"
        telemetry["history"].append({"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "prompt": raw_prompt, "style": style})
        cls.save_telemetry(telemetry)
        return enhanced_prompt


# ==========================================
# 3. LOW-MEMORY CUDA 8K CONVERTOR
# ==========================================

def convert_video_to_8k_bullet_speed(input_file_path: str) -> str:
    if not os.path.exists(input_file_path):
        return None

    filename = os.path.basename(input_file_path)
    base_name, _ = os.path.splitext(filename)
    output_8k_path = os.path.join(CONVERTED_DIR, f"{base_name}_8K.mp4")

    ffmpeg_nvenc_cmd = [
        "ffmpeg", "-y", "-hwaccel", "cuda",
        "-i", f'"{input_file_path}"',
        "-vf", "scale=7680:4320:flags=bilinear",
        "-c:v", "h264_nvenc", "-preset", "p1", "-tune", "ll", "-c:a", "copy",
        f'"{output_8k_path}"'
    ]

    try:
        res = subprocess.run(" ".join(ffmpeg_nvenc_cmd), shell=True, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_8k_path):
            return output_8k_path
        else:
            cpu_cmd = f'ffmpeg -y -i "{input_file_path}" -vf "scale=7680:4320:flags=lanczos" -c:v libx264 -preset ultrafast -threads 0 -c:a copy "{output_8k_path}"'
            subprocess.run(cpu_cmd, shell=True, capture_output=True)
            return output_8k_path if os.path.exists(output_8k_path) else input_file_path
    except Exception:
        return input_file_path


# ==========================================
# 4. DOWNLOADHELPER AUTOMATION ENGINE
# ==========================================

AUTO_DOWNLOAD_QUEUE = []
DOWNLOAD_HISTORY = set()

def download_single_url_task(args):
    idx, url, total_count, selected_category, browser_choice, auto_convert_8k = args
    active_cat = auto_detect_category_from_url(url) if selected_category == "Auto-Detect Category" else selected_category
    target_dir = os.path.join(BASE_DIR, CATEGORY_MAP.get(active_cat, "input_videos/general"))
    os.makedirs(target_dir, exist_ok=True)

    cmd = [
        "yt-dlp", "--cookies-from-browser", browser_choice, "-N", "16",
        "-P", f'"{target_dir}"', "-o", '"%(title)s.%(ext)s"', "--restrict-filenames", f'"{url}"'
    ]

    log_entry = f"[*] [{idx}/{total_count}] DownloadHelper Processing ({active_cat}): {url}\n"
    converted_file_path = None

    try:
        res = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            log_entry += f"[SUCCESS] Downloaded: {url} -> [{active_cat}]\n"
            downloaded_files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(('.mp4', '.mkv', '.webm'))]
            if downloaded_files:
                latest_file = max(downloaded_files, key=os.path.getmtime)
                if auto_convert_8k:
                    log_entry += f"[*] [8K AUTO-CONVERT] Processing: {os.path.basename(latest_file)}...\n"
                    converted_file_path = convert_video_to_8k_bullet_speed(latest_file)
                else:
                    converted_file_path = latest_file
        else:
            log_entry += f"[ERROR] Failed: {url}\n"
    except Exception as e:
        log_entry += f"[EXCEPTION] Error on {url}: {str(e)}\n"

    return log_entry, converted_file_path


def process_multi_video_downloader(url_input: str, selected_category: str, browser_choice: str, auto_convert_8k: bool, max_parallel: int):
    if not url_input or not url_input.strip():
        return "[!] Error: No video URLs provided.", None, None

    urls = [u.strip() for u in url_input.splitlines() if u.strip()]
    logs = [f"=== STARTING DOWNLOADHELPER AUTOMATION BATCH ({len(urls)} URLs) ==="]
    converted_videos = []

    tasks = [(idx, url, len(urls), selected_category, browser_choice, auto_convert_8k) for idx, url in enumerate(urls, 1)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = [executor.submit(download_single_url_task, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            log_res, vid_path = future.result()
            logs.append(log_res)
            if vid_path and os.path.exists(vid_path):
                converted_videos.append(vid_path)

    return "\n".join(logs), (converted_videos[0] if converted_videos else None), converted_videos


# Background Clipboard Listener (Video DownloadHelper Sniffer)
def clipboard_listener_loop():
    if not HAS_PYPERCLIP:
        return
    last_clip = ""
    while True:
        try:
            curr_clip = pyperclip.paste().strip()
            if curr_clip != last_clip and curr_clip.startswith("http"):
                last_clip = curr_clip
                if any(k in curr_clip.lower() for k in ["spankbang", "pornhub", "xvideos", "redtube", "youtube", "vimeo", "adult"]):
                    if curr_clip not in DOWNLOAD_HISTORY:
                        DOWNLOAD_HISTORY.add(curr_clip)
                        logging.info(f"[+] [DOWNLOADHELPER SNIFFER] Captured URL from clipboard: {curr_clip}")
                        AUTO_DOWNLOAD_QUEUE.append(curr_clip)
        except Exception:
            pass
        time.sleep(2)

# Start background clipboard daemon thread
threading.Thread(target=clipboard_listener_loop, daemon=True).start()


def fetch_clipboard_captured_urls():
    """Returns captured URLs directly into the URL textbox."""
    if not HAS_PYPERCLIP:
        return "pyperclip module not installed. Install via: pip install pyperclip"
    if not AUTO_DOWNLOAD_QUEUE:
        return "No new video URLs captured yet. Right-click copy any video link from your browser to capture!"
    return "\n".join(AUTO_DOWNLOAD_QUEUE)


# ==========================================
# 5. ZERO-RAM-LEAK STORY RENDER ENGINE
# ==========================================

async def generate_narration_audio(text: str, voice_name: str, output_audio_path: str):
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(output_audio_path)
        return True
    except Exception as e:
        logging.error(f"[!] TTS Error: {e}")
        return False


def render_single_scene_task_low_mem(args):
    idx, scene_script, total_scenes, voice, style, timestamp = args
    temp_audio = os.path.join(OUTPUT_DIR, f"audio_{timestamp}_s{idx}.mp3")
    temp_raw_mp4 = os.path.join(OUTPUT_DIR, f"raw_{timestamp}_s{idx}.mp4")
    temp_final_scene = os.path.join(OUTPUT_DIR, f"final_s{idx}_{timestamp}.mp4")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    audio_ok = loop.run_until_complete(generate_narration_audio(scene_script, voice, temp_audio))

    duration = 6.0
    if audio_ok and os.path.exists(temp_audio):
        try:
            res = subprocess.run(f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{temp_audio}"', shell=True, capture_output=True, text=True)
            duration = max(3.0, float(res.stdout.strip()))
        except Exception:
            duration = 6.0

    fps = 30
    total_frames = max(30, int(fps * duration))
    width, height = 1280, 720

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_raw_mp4, fourcc, fps, (width, height))

    c1, c2 = np.array([20, 20, 35], dtype=np.uint8), np.array([80, 50, 110], dtype=np.uint8)

    words = scene_script.split()
    lines, curr_line = [], ""
    for w in words:
        if len(curr_line + " " + w) < 50:
            curr_line += " " + w
        else:
            lines.append(curr_line.strip())
            curr_line = w
    if curr_line:
        lines.append(curr_line.strip())

    for frame_idx in range(total_frames):
        progress = frame_idx / float(total_frames)
        interp_color = (c1 * (1 - progress) + c2 * progress).astype(np.uint8)
        frame = np.full((height, width, 3), interp_color, dtype=np.uint8)

        cx = int(width / 2 + np.sin(progress * 2 * np.pi) * 150)
        cy = int(height / 2 + np.cos(progress * 2 * np.pi) * 80)
        cv2.circle(frame, (cx, cy), 200, (int(interp_color[0]*1.3)%255, int(interp_color[1]*1.3)%255, int(interp_color[2]*1.3)%255), -1)

        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)

        draw.text((40, 40), f"ACT / SCENE {idx} of {total_scenes} [{style}]", fill=(255, 215, 0))

        y_offset = height - 160 - (len(lines) * 25)
        for line in lines[:4]:
            draw.text((40, y_offset), line, fill=(255, 255, 255))
            y_offset += 28

        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        out.write(frame)

        if frame_idx % 30 == 0:
            del frame, img_pil, draw
            gc.collect()

    out.release()

    if audio_ok and os.path.exists(temp_audio):
        merge_cmd = f'ffmpeg -y -i "{temp_raw_mp4}" -i "{temp_audio}" -c:v h264_nvenc -preset p1 -tune ll -c:a aac -shortest "{temp_final_scene}"'
        res = subprocess.run(merge_cmd, shell=True, capture_output=True)
        if res.returncode != 0:
            cpu_merge = f'ffmpeg -y -i "{temp_raw_mp4}" -i "{temp_audio}" -c:v libx264 -preset ultrafast -c:a aac -shortest "{temp_final_scene}"'
            subprocess.run(cpu_merge, shell=True, capture_output=True)
    else:
        temp_final_scene = temp_raw_mp4

    if os.path.exists(temp_raw_mp4) and os.path.exists(temp_final_scene) and temp_raw_mp4 != temp_final_scene:
        try:
            os.remove(temp_raw_mp4)
        except Exception:
            pass

    gc.collect()
    return idx, temp_final_scene if os.path.exists(temp_final_scene) else None


def render_full_scale_singularity_story_parallel(full_story: str, voice: str, style: str, target_output_mp4: str) -> str:
    timestamp = int(time.time())
    scenes = [s.strip() for s in re.split(r'\n+', full_story) if s.strip()]
    if not scenes:
        scenes = [full_story]

    tasks = [(idx, scene, len(scenes), voice, style, timestamp) for idx, scene in enumerate(scenes, 1)]
    rendered_dict = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(render_single_scene_task_low_mem, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            idx, sc_path = future.result()
            if sc_path:
                rendered_dict[idx] = sc_path

    ordered_files = [rendered_dict[k] for k in sorted(rendered_dict.keys())]

    if len(ordered_files) > 1:
        concat_txt = os.path.join(OUTPUT_DIR, f"concat_list_{timestamp}.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for sf in ordered_files:
                f.write(f"file '{sf}'\n")

        concat_cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_txt}" -c copy "{target_output_mp4}"'
        subprocess.run(concat_cmd, shell=True, capture_output=True)
    elif ordered_files:
        target_output_mp4 = ordered_files[0]

    gc.collect()
    return target_output_mp4


def generate_ai_video_with_learning_and_preview(prompt: str, category: str, platform: str, duration_hours: float, style: str, voice: str, auto_8k: bool):
    if not prompt or not prompt.strip():
        return "[!] Error: Story script cannot be empty.", None

    optimized_prompt = AISelfLearningEngine.optimize_prompt(prompt, style)
    timestamp = int(time.time())
    raw_movie_path = os.path.join(OUTPUT_DIR, f"full_movie_{category}_{timestamp}.mp4")

    rendered_file = render_full_scale_singularity_story_parallel(prompt, voice, style, raw_movie_path)
    final_output_file = convert_video_to_8k_bullet_speed(rendered_file) if auto_8k else rendered_file

    blueprint = {
        "meta": {
            "engine": "Apex-Singularity-Master-Kernel-v13.0",
            "category": category,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_platform": platform,
            "output_file": final_output_file
        },
        "learned_optimized_prompt": optimized_prompt,
        "story_script": prompt
    }

    blueprint_file = os.path.join(OUTPUT_DIR, f"learned_blueprint_{category}_{timestamp}.json")
    with open(blueprint_file, "w", encoding="utf-8") as f:
        json.dump(blueprint, f, indent=2)

    output_log = f"[+] MEMORY-OPTIMIZED MOVIE RENDERED!\nOutput File: {final_output_file}\nSaved Blueprint: {blueprint_file}"
    return output_log, final_output_file


# ==========================================
# 6. MICROSERVICES & DASHBOARD
# ==========================================

def trigger_workspace_module(module_name: str) -> str:
    script_path = os.path.join(BASE_DIR, f"{module_name}.py")
    if os.path.exists(script_path):
        try:
            res = subprocess.run(f"python {script_path} --test", shell=True, capture_output=True, text=True)
            return f"[+] {module_name} executed:\n{res.stdout if res.stdout else res.stderr}"
        except Exception as e:
            return f"[!] Module Error: {str(e)}"
    return f"[!] Script {module_name}.py not found."


def find_available_port(start_port: int = 7862, max_attempts: int = 20) -> int:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


with gr.Blocks(title="Apex AI Studio - Master All-In-One Kernel") as demo:
    gr.Markdown("# ⚡ Apex AI Studio - DownloadHelper Automation, CUDA 8K Converter & Studio Kernel")

    with gr.Tabs():
        # TAB 1: VIDEO DOWNLOADHELPER AUTOMATION & CUDA 8K CONVERT ENGINE
        with gr.TabItem("📥 Video DownloadHelper & CUDA 8K Converter"):
            with gr.Row():
                with gr.Column(scale=2):
                    url_box = gr.Textbox(
                        label="Target Video URLs (Paste multiple links OR click auto-fetch below)",
                        placeholder="https://spankbang.com/...\nhttps://pornhub.com/...\nhttps://xvideos.com/...",
                        lines=8
                    )
                    
                    fetch_clip_btn = gr.Button("📋 Auto-Fetch Right-Clicked Copied Video Links (Video DownloadHelper Mode)", variant="secondary")

                    with gr.Row():
                        category_dropdown = gr.Dropdown(choices=list(CATEGORY_MAP.keys()), value="Auto-Detect Category", label="Category Mapping")
                        browser_dropdown = gr.Dropdown(choices=["firefox", "chrome", "edge"], value="firefox", label="Cookie Source Browser")
                    with gr.Row():
                        parallel_threads_slider = gr.Slider(minimum=1, maximum=8, value=3, step=1, label="Parallel Concurrent Download Workers")
                        auto_8k_checkbox = gr.Checkbox(value=True, label="⚡ Straightaway Auto-Convert Downloads to 8K Resolution (CUDA NVENC)")

                    process_btn = gr.Button("🚀 Download Straightaway & Auto-Convert to 8K", variant="primary", size="lg")

                with gr.Column(scale=2):
                    preview_player = gr.Video(label="🎬 Primary Converted 8K Video Preview", interactive=False)
                    video_gallery = gr.Gallery(label="📁 Converted 8K Batch Video Outputs", columns=3, height=250)
                    status_output = gr.Textbox(label="Batch Terminal Processing Logs", lines=10, interactive=False)

            fetch_clip_btn.click(fn=fetch_clipboard_captured_urls, outputs=url_box)

            process_btn.click(
                fn=process_multi_video_downloader,
                inputs=[url_box, category_dropdown, browser_dropdown, auto_8k_checkbox, parallel_threads_slider],
                outputs=[status_output, preview_player, video_gallery]
            )

        # TAB 2: AI LEARNING STORY VIDEO GENERATOR
        with gr.TabItem("🎬 AI Learning Video Generator"):
            with gr.Row():
                with gr.Column(scale=2):
                    prompt_input = gr.Textbox(
                        label="AI Generation Concept / Full Story & Character Script",
                        placeholder="Paste your long adult content story script here...",
                        lines=8
                    )
                    with gr.Row():
                        gen_category_select = gr.Dropdown(choices=list(CATEGORY_MAP.keys())[1:], value="Adult_General_Media", label="Category Mapping")
                        platform_select = gr.Dropdown(choices=["horizontal_youtube", "vertical_short", "square_social"], value="horizontal_youtube", label="Target Format")
                    with gr.Row():
                        style_select = gr.Dropdown(choices=["Cinematic Photorealistic", "Anime / Illustrative", "3D Octane Render", "VTuber Dynamic"], value="Cinematic Photorealistic", label="Style Render Tier")
                        voice_select = gr.Dropdown(choices=["en-US-ChristopherNeural", "en-US-JennyNeural"], value="en-US-JennyNeural", label="Voice Engine")
                    
                    with gr.Row():
                        duration_hours_slider = gr.Slider(minimum=0.1, maximum=24.0, value=1.0, step=0.5, label="Target Duration (Hours)")
                        auto_8k_gen_checkbox = gr.Checkbox(value=False, label="⚡ Enable 8K CUDA Upscale (Uncheck for 5x Faster 1080p Generation)")

                    generate_btn = gr.Button("🚀 Generate Full-Scale AI Movie", variant="primary", size="lg")

                with gr.Column(scale=2):
                    ai_preview_player = gr.Video(label="🎬 Rendered Story Preview", interactive=False)
                    gen_output = gr.Textbox(label="Output Logs & Blueprint", lines=12, interactive=False)

            generate_btn.click(
                fn=generate_ai_video_with_learning_and_preview,
                inputs=[prompt_input, gen_category_select, platform_select, duration_hours_slider, style_select, voice_select, auto_8k_gen_checkbox],
                outputs=[gen_output, ai_preview_player]
            )

        # TAB 3: WORKSPACE MICROSERVICES
        with gr.TabItem("🛠️ Workspace Microservices"):
            with gr.Row():
                annotator_btn = gr.Button("🏷️ Run Dataset Auto-Annotator")
                trends_btn = gr.Button("📈 Run Viral Trend Analyzer")
                stems_btn = gr.Button("🎵 Run Audio Stem Separator")
                governor_btn = gr.Button("⚡ Run Hardware Resource Governor")

            module_logs = gr.Textbox(label="Sub-Module Output Logs", lines=12, interactive=False)

            annotator_btn.click(fn=lambda: trigger_workspace_module("dataset_auto_annotator"), outputs=module_logs)
            trends_btn.click(fn=lambda: trigger_workspace_module("viral_trend_analyzer"), outputs=module_logs)
            stems_btn.click(fn=lambda: trigger_workspace_module("audio_stem_separator"), outputs=module_logs)
            governor_btn.click(fn=lambda: trigger_workspace_module("kernel_level_governor"), outputs=module_logs)

if __name__ == "__main__":
    target_port = find_available_port(7862)
    demo.launch(server_name="127.0.0.1", server_port=target_port)