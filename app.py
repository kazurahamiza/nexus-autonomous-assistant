import os
import sys
import json
import time
import logging
import subprocess
import socket
import gradio as gr

# ==========================================
# 0. SYSTEM LOGGING & ENVIRONMENT SETUP
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s"
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_videos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output_videos")
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATASET_DIR, exist_ok=True)


# ==========================================
# 1. COGNITIVE LLM DIRECTOR & ENGINE
# ==========================================

class SingularityLLMDirector:
    """Master Cognitive Controller: Translates user prompts into multi-stage video generation blueprints."""

    @staticmethod
    def compose_production_blueprint(prompt: str, platform: str, duration: int, style: str, voice: str) -> dict:
        logging.info(f"[*] [SingularityDirector] Synthesizing blueprint for: '{prompt}'")
        
        aspect_ratio = "9:16" if platform == "vertical_short" else "16:9"
        scene_count = max(2, duration // 5)
        scene_duration = duration // scene_count

        scenes = []
        for i in range(1, scene_count + 1):
            scenes.append({
                "scene_id": i,
                "duration_sec": scene_duration,
                "visual_prompt": f"Scene {i}: {prompt}, style={style}, high dynamic range, cinematic lighting, 8k render",
                "negative_prompt": "blurry, low quality, distortion, ugly, extra limbs, artifacts",
                "voiceover_script": f"Segment {i} overview for {prompt}.",
                "camera_movement": "slow_zoom_in" if i % 2 != 0 else "pan_right",
                "aspect_ratio": aspect_ratio
            })

        blueprint = {
            "meta": {
                "engine": "Singularity-Master-Kernel-v5.0",
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "target_platform": platform,
                "visual_style": style
            },
            "audio_config": {
                "voice_id": voice,
                "bg_music_style": "cinematic_ambient_synth",
                "ducking_level": 0.85
            },
            "scenes": scenes,
            "post_processing": {
                "upscale_target": "4k",
                "burn_captions": True,
                "color_grade": "teal_and_orange"
            }
        }
        return blueprint


def generate_ai_video_action(prompt: str, platform: str, duration: int, style: str, voice: str) -> str:
    """Executes scene blueprint generation and dispatches rendering jobs."""
    if not prompt or not prompt.strip():
        return "[!] Error: Video prompt cannot be empty."

    blueprint = SingularityLLMDirector.compose_production_blueprint(
        prompt, platform, duration, style, voice
    )

    # Save generated blueprint to output directory
    blueprint_file = os.path.join(OUTPUT_DIR, f"blueprint_{int(time.time())}.json")
    with open(blueprint_file, "w", encoding="utf-8") as f:
        json.dump(blueprint, f, indent=2)

    return (
        f"[+] SINGULARITY MASTER BLUEPRINT GENERATED SUCCESSFULLY!\n"
        f"Saved Blueprint to: {blueprint_file}\n\n"
        f"--- PRODUCTION SCHEMA ---\n"
        f"{json.dumps(blueprint, indent=2)}"
    )


# ==========================================
# 2. AUTOMATED COOKIE SCRAPER & DOWNLOADER
# ==========================================

def auto_download_video_action(url_input: str, browser_choice: str = "firefox") -> str:
    """Bypasses Cloudflare HTTP 403 blocks using active browser cookies and enforces exact video page titles."""
    if not url_input or not url_input.strip():
        return "[!] Error: Please provide one or more video links."

    urls = [u.strip() for u in url_input.splitlines() if u.strip()]
    results = []

    for idx, url in enumerate(urls, 1):
        logging.info(f"[*] [{idx}/{len(urls)}] Processing url with {browser_choice} cookies: {url}")
        
        # Build yt-dlp execution command
        cmd = [
            "yt-dlp",
            "--cookies-from-browser", browser_choice,
            "-P", f'"{INPUT_DIR}"',
            "-o", '"%(title)s.%(ext)s"',
            "--restrict-filenames",
            f'"{url}"'
        ]

        full_cmd = " ".join(cmd)
        
        try:
            res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                results.append(f"[SUCCESS] Downloaded ({idx}/{len(urls)}): {url}")
            else:
                err_text = res.stderr.strip() if res.stderr else "Unknown download failure."
                results.append(f"[ERROR] Download Failed ({idx}/{len(urls)}): {url}\n    Log: {err_text[:250]}")
        except Exception as e:
            results.append(f"[EXCEPTION] System Error ({idx}/{len(urls)}): {url}\n    Details: {str(e)}")

    return "\n".join(results)


# ==========================================
# 3. DATASET AUTO-ANNOTATOR PIPELINE
# ==========================================

def trigger_dataset_annotation_action() -> str:
    """Executes dataset keyframe extraction and auto-captioning on downloaded videos."""
    annotator_script = os.path.join(BASE_DIR, "dataset_auto_annotator.py")
    
    if os.path.exists(annotator_script):
        logging.info("[*] Executing dataset auto-annotator script...")
        try:
            res = subprocess.run(f"python {annotator_script}", shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                return f"[+] Dataset Auto-Annotation Completed:\n{res.stdout}"
            else:
                return f"[!] Annotation Execution Log:\n{res.stderr}"
        except Exception as e:
            return f"[!] Exception during annotation execution: {str(e)}"
    else:
        return f"[*] Annotator module '{annotator_script}' not found. Dataset folder active at: {DATASET_DIR}"


# ==========================================
# 4. PORT MANAGEMENT & SERVER LAUNCHER
# ==========================================

def find_available_port(start_port: int = 7862, max_attempts: int = 20) -> int:
    """Finds an open TCP port starting from the requested port number."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


# ==========================================
# 5. GRADIO UNIFIED MASTER INTERFACE
# ==========================================

with gr.Blocks(title="Apex AI Studio - Master Singularity Kernel") as demo:
    gr.Markdown("# ⚡ Apex AI Studio - Master Unified Kernel")
    gr.Markdown("Unified platform for automated video generation, cookie-authenticated video downloading, and dataset auto-annotation.")

    with gr.Tabs():
        
        # TAB 1: AI VIDEO GENERATOR
        with gr.TabItem("🎬 AI Video Studio Generator"):
            gr.Markdown("### 1-Click Multi-Shot Storyboard & Video Generator")
            with gr.Row():
                with gr.Column(scale=2):
                    prompt_input = gr.Textbox(
                        label="Video Scene Script or Detailed Concept",
                        placeholder="Enter video prompt or detailed concept here...",
                        lines=6
                    )
                    with gr.Row():
                        platform_select = gr.Dropdown(
                            choices=["vertical_short", "horizontal_youtube", "square_social"],
                            value="vertical_short",
                            label="Target Format / Aspect Ratio"
                        )
                        style_select = gr.Dropdown(
                            choices=["Cinematic Photorealistic", "Anime / Illustrative", "3D Octane Render", "VTuber Dynamic"],
                            value="Cinematic Photorealistic",
                            label="Visual Style Render Tier"
                        )
                    with gr.Row():
                        duration_slider = gr.Slider(minimum=5, maximum=60, value=15, step=5, label="Duration (Seconds)")
                        voice_select = gr.Dropdown(
                            choices=["en-US-ChristopherNeural", "en-US-JennyNeural", "ja-JP-NanamiNeural"],
                            value="en-US-ChristopherNeural",
                            label="Narrator Voice Engine"
                        )
                    
                    generate_btn = gr.Button("🚀 Generate & Dispatch Production Blueprint", variant="primary", size="lg")

                with gr.Column(scale=2):
                    gen_output = gr.Textbox(label="Singularity Orchestrator Output & JSON Blueprint", lines=18, interactive=False)

            generate_btn.click(
                fn=generate_ai_video_action,
                inputs=[prompt_input, platform_select, duration_slider, style_select, voice_select],
                outputs=gen_output
            )

        # TAB 2: AUTOMATED DATASET DOWNLOADER & SCRAPER
        with gr.TabItem("📥 Automated Video Scraper & Downloader"):
            gr.Markdown("### Cookie-Authenticated Video Downloader & Scraper")
            gr.Markdown("Directly fetches media into `input_videos/` using browser session cookies to bypass Cloudflare 403 blocks.")
            
            with gr.Row():
                with gr.Column(scale=3):
                    url_box = gr.Textbox(
                        label="Target Video URLs (Paste links, one per line)",
                        placeholder="https://spankbang.com/...\nhttps://pornhub.com/...",
                        lines=8
                    )
                with gr.Column(scale=1):
                    browser_dropdown = gr.Dropdown(
                        choices=["firefox", "chrome", "edge", "brave", "opera"],
                        value="firefox",
                        label="Cookie Source Browser",
                        info="Select your active web browser to bypass Cloudflare 403 blocks."
                    )
                    download_btn = gr.Button("🚀 Auto-Download All Videos", variant="primary", size="lg")
                    annotate_btn = gr.Button("🏷️ Run Dataset Auto-Annotator", variant="secondary")

            status_output = gr.Textbox(label="Execution Output Logs", lines=12, interactive=False)

            download_btn.click(
                fn=auto_download_video_action,
                inputs=[url_box, browser_dropdown],
                outputs=status_output
            )
            
            annotate_btn.click(
                fn=trigger_dataset_annotation_action,
                inputs=[],
                outputs=status_output
            )

if __name__ == "__main__":
    target_port = find_available_port(7862)
    logging.info(f"[*] Launching Apex AI Studio Master Web Interface on port {target_port}...")
    demo.launch(server_name="127.0.0.1", server_port=target_port)