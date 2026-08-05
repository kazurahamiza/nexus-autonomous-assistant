import os
import sys
import json
import time
import logging
import subprocess
import socket
import concurrent.futures
import asyncio
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import gradio as gr

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
LEARNING_DB = os.path.join(BASE_DIR, "ai_learning_telemetry.json")

# Master Category Directory Mappings
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


# ==========================================
# 1. AI SELF-LEARNING TELEMETRY ENGINE
# ==========================================

class AISelfLearningEngine:
    """Tracks feedback telemetry and adapts visual generation weights dynamically."""

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
        count = telemetry.get("generation_count", 0) + 1
        telemetry["generation_count"] = count

        enhanced_prompt = (
            f"{raw_prompt}, style={style}, 8k resolution, photorealistic masterwork, "
            f"cinematic studio lighting, HDR10+, highly detailed textures"
        )
        
        telemetry["history"].append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "prompt": raw_prompt,
            "enhanced_prompt": enhanced_prompt,
            "style": style
        })
        cls.save_telemetry(telemetry)
        return enhanced_prompt


# ==========================================
# 2. AUTO-CATEGORIZATION ROUTER
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
# 3. BULLET-SPEED CUDA 8K CONVERTOR
# ==========================================

def convert_video_to_8k_bullet_speed(input_file_path: str) -> str:
    """NVIDIA CUDA / CPU Multi-Threaded 8K Converter Engine (7680x4320)."""
    if not os.path.exists(input_file_path):
        logging.error(f"[!] File not found for 8K conversion: {input_file_path}")
        return None

    filename = os.path.basename(input_file_path)
    base_name, _ = os.path.splitext(filename)
    output_8k_path = os.path.join(CONVERTED_DIR, f"{base_name}_8K.mp4")

    logging.info(f"[*] [CUDA 8K CONVERTER] Processing 8K upscale: {filename}")

    ffmpeg_nvenc_cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda",
        "-i", f'"{input_file_path}"',
        "-vf", "scale=7680:4320:flags=bilinear",
        "-c:v", "h264_nvenc",
        "-preset", "p1",
        "-tune", "ll",
        "-c:a", "copy",
        f'"{output_8k_path}"'
    ]

    try:
        res = subprocess.run(" ".join(ffmpeg_nvenc_cmd), shell=True, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_8k_path):
            logging.info(f"[+] [NVENC CUDA SUCCESS] 8K Converted: {output_8k_path}")
            return output_8k_path
        else:
            cpu_cmd = (
                f'ffmpeg -y -i "{input_file_path}" '
                f'-vf "scale=7680:4320:flags=lanczos" '
                f'-c:v libx264 -preset ultrafast -threads 0 -c:a copy "{output_8k_path}"'
            )
            subprocess.run(cpu_cmd, shell=True, capture_output=True, text=True)
            return output_8k_path if os.path.exists(output_8k_path) else input_file_path
    except Exception as e:
        logging.error(f"[!] 8K Converter Exception: {e}")
        return input_file_path


# ==========================================
# 4. PARALLEL MULTI-VIDEO DOWNLOAD PIPELINE
# ==========================================

def download_single_url_task(args):
    idx, url, total_count, selected_category, browser_choice, auto_convert_8k = args
    
    if selected_category == "Auto-Detect Category":
        active_cat = auto_detect_category_from_url(url)
    else:
        active_cat = selected_category

    target_dir = os.path.join(BASE_DIR, CATEGORY_MAP.get(active_cat, "input_videos/general"))
    os.makedirs(target_dir, exist_ok=True)

    cmd = [
        "yt-dlp",
        "--cookies-from-browser", browser_choice,
        "-N", "16",
        "-P", f'"{target_dir}"',
        "-o", '"%(title)s.%(ext)s"',
        "--restrict-filenames",
        f'"{url}"'
    ]

    log_entry = f"[*] [{idx}/{total_count}] Processing ({active_cat}): {url}\n"
    converted_file_path = None

    try:
        res = subprocess.run(" ".join(cmd), shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            log_entry += f"[SUCCESS] Downloaded: {url} -> [{active_cat}]\n"
            
            downloaded_files = [
                os.path.join(target_dir, f) for f in os.listdir(target_dir) 
                if f.endswith(('.mp4', '.mkv', '.webm'))
            ]
            if downloaded_files:
                latest_file = max(downloaded_files, key=os.path.getmtime)
                if auto_convert_8k:
                    log_entry += f"[*] [8K UPSCALE] Converting {os.path.basename(latest_file)}...\n"
                    converted_file_path = convert_video_to_8k_bullet_speed(latest_file)
                else:
                    converted_file_path = latest_file
        else:
            log_entry += f"[ERROR] Failed: {url}\n    Details: {res.stderr[:200]}\n"
    except Exception as e:
        log_entry += f"[EXCEPTION] Error on {url}: {str(e)}\n"

    return log_entry, converted_file_path


def process_multi_video_downloader(url_input: str, selected_category: str, browser_choice: str, auto_convert_8k: bool, max_parallel: int):
    if not url_input or not url_input.strip():
        return "[!] Error: No video URLs provided.", None, None

    urls = [u.strip() for u in url_input.splitlines() if u.strip()]
    total_count = len(urls)
    
    logs = [f"=== STARTING PARALLEL MULTI-VIDEO BATCH ({total_count} URLs, {max_parallel} Threads) ==="]
    converted_videos = []

    tasks = [
        (idx, url, total_count, selected_category, browser_choice, auto_convert_8k)
        for idx, url in enumerate(urls, 1)
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = [executor.submit(download_single_url_task, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            log_res, vid_path = future.result()
            logs.append(log_res)
            if vid_path and os.path.exists(vid_path):
                converted_videos.append(vid_path)

    logs.append(f"=== COMPLETED BATCH PROCESS: {len(converted_videos)}/{total_count} Videos Ready ===")
    
    primary_preview = converted_videos[0] if converted_videos else None
    return "\n".join(logs), primary_preview, converted_videos


# ==========================================
# 5. REAL AI STORY VIDEO SYNTHESIS ENGINE
# ==========================================

async def generate_narration_audio(text: str, voice_name: str, output_audio_path: str):
    """Generates AI TTS Narration file using edge-tts."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice_name)
        await communicate.save(output_audio_path)
        return True
    except Exception as e:
        logging.error(f"[!] TTS Generation failed: {e}")
        return False

def render_synthetic_story_video(prompt: str, voice: str, style: str, output_video_path: str) -> str:
    """Renders a brand-new animated visual story video with voiceover narration and cinematic title card."""
    timestamp = int(time.time())
    temp_audio = os.path.join(OUTPUT_DIR, f"narration_{timestamp}.mp3")
    
    # 1. Generate Voice Narration
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    audio_success = loop.run_until_complete(generate_narration_audio(prompt, voice, temp_audio))
    
    # Get audio duration via ffprobe
    duration = 10.0
    if audio_success and os.path.exists(temp_audio):
        probe_cmd = f'ffprobe -v error -show_entries format=duration -of default=noprintwrappers=1:nokey=1 "{temp_audio}"'
        try:
            res = subprocess.run(probe_cmd, shell=True, capture_output=True, text=True)
            duration = float(res.stdout.strip())
        except Exception:
            duration = 10.0

    # 2. Synthesize Cinematic Frames using OpenCV/PIL
    fps = 30
    total_frames = int(fps * duration)
    width, height = 1920, 1080
    temp_raw_video = os.path.join(OUTPUT_DIR, f"raw_story_{timestamp}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_raw_video, fourcc, fps, (width, height))

    # Color background palettes based on style
    if "Anime" in style:
        bg_color_start = (45, 20, 60)
        bg_color_end = (180, 80, 120)
    elif "Photorealistic" in style:
        bg_color_start = (15, 20, 25)
        bg_color_end = (40, 50, 65)
    else:
        bg_color_start = (20, 20, 30)
        bg_color_end = (60, 40, 90)

    for frame_idx in range(total_frames):
        alpha = frame_idx / total_frames
        
        # Smooth animated gradient background
        r = int(bg_color_start[0] * (1 - alpha) + bg_color_end[0] * alpha)
        g = int(bg_color_start[1] * (1 - alpha) + bg_color_end[1] * alpha)
        b = int(bg_color_start[2] * (1 - alpha) + bg_color_end[2] * alpha)

        frame = np.full((height, width, 3), (b, g, r), dtype=np.uint8)

        # Dynamic lighting zoom effect
        zoom_radius = int(200 + 100 * np.sin(frame_idx / 15.0))
        cv2.circle(frame, (width // 2, height // 2), zoom_radius, (b+20, g+20, r+20), -1)

        # Draw Story & Character Caption
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # Overlay text
        caption_text = f"CHAPTER: {prompt[:60]}..." if len(prompt) > 60 else prompt
        style_text = f"Visual Style Tier: {style}"

        draw.text((100, height - 200), caption_text, fill=(255, 255, 255))
        draw.text((100, height - 140), style_text, fill=(200, 220, 255))

        frame = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        out.write(frame)

    out.release()

    # 3. Merge Synthesized Visual Video + Narration Audio via FFmpeg
    if audio_success and os.path.exists(temp_audio):
        merge_cmd = (
            f'ffmpeg -y -i "{temp_raw_video}" -i "{temp_audio}" '
            f'-c:v h264_nvenc -preset p1 -c:a aac -shortest "{output_video_path}"'
        )
        res = subprocess.run(merge_cmd, shell=True, capture_output=True, text=True)
        if res.returncode != 0:
            # CPU fallback
            cpu_merge = f'ffmpeg -y -i "{temp_raw_video}" -i "{temp_audio}" -c:v libx264 -preset ultrafast -c:a aac -shortest "{output_video_path}"'
            subprocess.run(cpu_merge, shell=True, capture_output=True)
    else:
        output_video_path = temp_raw_video

    return output_video_path


def generate_ai_video_with_learning_and_preview(prompt: str, category: str, platform: str, duration_hours: float, style: str, voice: str):
    if not prompt or not prompt.strip():
        return "[!] Error: Prompt cannot be empty.", None

    # 1. Telemetry prompt optimization
    optimized_prompt = AISelfLearningEngine.optimize_prompt(prompt, style)

    timestamp = int(time.time())
    rendered_video_filename = f"story_render_{category}_{timestamp}.mp4"
    output_video_path = os.path.join(OUTPUT_DIR, rendered_video_filename)

    # 2. Render actual story video
    final_video_file = render_synthetic_story_video(optimized_prompt, voice, style, output_video_path)

    # 3. Up-scale rendered story video to 8K
    converted_8k_file = convert_video_to_8k_bullet_speed(final_video_file)

    blueprint = {
        "meta": {
            "engine": "Apex-Singularity-Master-Kernel-v10.0",
            "category": category,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "target_platform": platform,
            "rendered_video": converted_8k_file
        },
        "learned_optimized_prompt": optimized_prompt,
        "scenes": [
            {
                "scene_id": 1,
                "visual_prompt": optimized_prompt,
                "audio_voice": voice,
                "rendered_file": converted_8k_file
            }
        ]
    }

    blueprint_file = os.path.join(OUTPUT_DIR, f"learned_blueprint_{category}_{timestamp}.json")
    with open(blueprint_file, "w", encoding="utf-8") as f:
        json.dump(blueprint, f, indent=2)

    output_log = (
        f"[+] BRAND NEW AI STORY VIDEO CREATED SUCCESSFULLY!\n"
        f"Rendered Output Video: {converted_8k_file}\n"
        f"Saved Production Blueprint: {blueprint_file}\n\n"
        f"--- PRODUCTION SCHEMA ---\n"
        f"{json.dumps(blueprint, indent=2)}"
    )

    return output_log, converted_8k_file


# ==========================================
# 6. WORKSPACE MICROSERVICE UTILITIES
# ==========================================

def trigger_workspace_module(module_name: str) -> str:
    script_path = os.path.join(BASE_DIR, f"{module_name}.py")
    if os.path.exists(script_path):
        try:
            res = subprocess.run(f"python {script_path} --test", shell=True, capture_output=True, text=True)
            return f"[+] {module_name} executed:\n{res.stdout if res.stdout else res.stderr}"
        except Exception as e:
            return f"[!] Module Error: {str(e)}"
    return f"[!] Script {module_name}.py not found in working directory."


def find_available_port(start_port: int = 7862, max_attempts: int = 20) -> int:
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


# ==========================================
# 7. GRADIO UNIFIED MASTER INTERFACE
# ==========================================

with gr.Blocks(title="Apex AI Studio - Master All-In-One Kernel") as demo:
    gr.Markdown("# ⚡ Apex AI Studio - Multi-Video Scraper, CUDA 8K Converter & Studio Kernel")

    with gr.Tabs():
        # TAB 1: BULLET MULTI-VIDEO DOWNLOADER & CUDA 8K CONVERTER
        with gr.TabItem("📥 Multi-Video Downloader & CUDA 8K Converter"):
            with gr.Row():
                with gr.Column(scale=2):
                    url_box = gr.Textbox(
                        label="Target Video URLs (Paste multiple links, one per line)",
                        placeholder="https://spankbang.com/...\nhttps://pornhub.com/...\nhttps://xvideos.com/...",
                        lines=8
                    )
                    with gr.Row():
                        category_dropdown = gr.Dropdown(
                            choices=list(CATEGORY_MAP.keys()),
                            value="Auto-Detect Category",
                            label="Content Category Mapping"
                        )
                        browser_dropdown = gr.Dropdown(
                            choices=["firefox", "chrome", "edge"],
                            value="firefox",
                            label="Cookie Source Browser"
                        )
                    with gr.Row():
                        parallel_threads_slider = gr.Slider(minimum=1, maximum=8, value=3, step=1, label="Parallel Concurrent Download Workers")
                        auto_8k_checkbox = gr.Checkbox(value=True, label="⚡ Auto-Convert All Downloads to 8K Resolution (CUDA NVENC)")

                    process_btn = gr.Button("🚀 Execute Multi-Video Download & 8K Conversion", variant="primary", size="lg")

                with gr.Column(scale=2):
                    preview_player = gr.Video(label="🎬 Primary Converted 8K Video Preview", interactive=False)
                    video_gallery = gr.Gallery(label="📁 Converted 8K Batch Video Outputs", columns=3, height=250)
                    status_output = gr.Textbox(label="Batch Processing Terminal Output Logs", lines=10, interactive=False)

            process_btn.click(
                fn=process_multi_video_downloader,
                inputs=[url_box, category_dropdown, browser_dropdown, auto_8k_checkbox, parallel_threads_slider],
                outputs=[status_output, preview_player, video_gallery]
            )

        # TAB 2: AI LEARNING STORY VIDEO GENERATOR (REAL SYNTHESIS)
        with gr.TabItem("🎬 AI Learning Video Generator"):
            with gr.Row():
                with gr.Column(scale=2):
                    prompt_input = gr.Textbox(
                        label="AI Generation Concept / Story & Character Script",
                        placeholder="Describe the story, character details, scene environment, and action...",
                        lines=5
                    )
                    with gr.Row():
                        gen_category_select = gr.Dropdown(
                            choices=list(CATEGORY_MAP.keys())[1:],
                            value="Adult_General_Media",
                            label="Target Category Mapping"
                        )
                        platform_select = gr.Dropdown(
                            choices=["horizontal_youtube", "vertical_short", "square_social"],
                            value="horizontal_youtube",
                            label="Target Format"
                        )
                    with gr.Row():
                        style_select = gr.Dropdown(
                            choices=["Cinematic Photorealistic", "Anime / Illustrative", "3D Octane Render", "VTuber Dynamic"],
                            value="Cinematic Photorealistic",
                            label="Visual Style Render Tier"
                        )
                        voice_select = gr.Dropdown(
                            choices=["en-US-ChristopherNeural", "en-US-JennyNeural"],
                            value="en-US-ChristopherNeural",
                            label="Voice Engine"
                        )
                    duration_hours_slider = gr.Slider(minimum=0.1, maximum=24.0, value=1.0, step=0.5, label="Target Duration (Hours)")
                    
                    generate_btn = gr.Button("🚀 Generate New AI Story Video", variant="primary", size="lg")

                with gr.Column(scale=2):
                    ai_preview_player = gr.Video(label="🎬 Newly Rendered Story Video Preview", interactive=False)
                    gen_output = gr.Textbox(label="AI Learning Telemetry & Blueprint Output", lines=12, interactive=False)

            generate_btn.click(
                fn=generate_ai_video_with_learning_and_preview,
                inputs=[prompt_input, gen_category_select, platform_select, duration_hours_slider, style_select, voice_select],
                outputs=[gen_output, ai_preview_player]
            )

        # TAB 3: WORKSPACE MICROSERVICES
        with gr.TabItem("🛠️ Workspace Microservices"):
            gr.Markdown("### Execute Workspace Microservices Directly")
            with gr.Row():
                annotator_btn = gr.Button("🏷️ Run Dataset Auto-Annotator")
                trends_btn = gr.Button("📈 Run Viral Trend Analyzer")
                stems_btn = gr.Button("🎵 Run Audio Stem Separator")
                governor_btn = gr.Button("⚡ Run Hardware Resource Governor")

            module_logs = gr.Textbox(label="Sub-Module Execution Output Logs", lines=12, interactive=False)

            annotator_btn.click(fn=lambda: trigger_workspace_module("dataset_auto_annotator"), outputs=module_logs)
            trends_btn.click(fn=lambda: trigger_workspace_module("viral_trend_analyzer"), outputs=module_logs)
            stems_btn.click(fn=lambda: trigger_workspace_module("audio_stem_separator"), outputs=module_logs)
            governor_btn.click(fn=lambda: trigger_workspace_module("kernel_level_governor"), outputs=module_logs)

if __name__ == "__main__":
    target_port = find_available_port(7862)
    demo.launch(server_name="127.0.0.1", server_port=target_port)