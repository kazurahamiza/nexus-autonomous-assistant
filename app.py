# ==============================================================================
# ENVIRONMENT OVERRIDES FOR TRANSFORMERS & TORCHVISION FIX
# ==============================================================================
import os
os.environ["USE_TORCH"] = "1"
os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"

import sys
import torch
import cv2
import asyncio
import numpy as np
import subprocess
import shutil
import sqlite3
import datetime
import edge_tts
import gradio as gr
import PIL.Image
from PIL import ImageFilter
from mutagen.mp3 import MP3

from diffusers import (
    StableDiffusionControlNetPipeline, 
    ControlNetModel, 
    DDIMScheduler
)

# ==============================================================================
# MASTER ASSET REGISTRY (DATABASE)
# ==============================================================================

DB_PATH = os.path.abspath("./master_registry.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS render_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            category TEXT,
            prompt TEXT,
            dialogue TEXT,
            duration_sec REAL,
            video_path TEXT
        )
    """)
    conn.commit()
    conn.close()

def register_render(category, prompt, dialogue, duration_sec, video_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO render_logs (timestamp, category, prompt, dialogue, duration_sec, video_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), category, prompt, dialogue, duration_sec, video_path))
    conn.commit()
    conn.close()

def get_registered_videos():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, category, duration_sec, video_path FROM render_logs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [f"[{r[0]}] {r[1]} | {r[2]} | {r[3]:.1f}s -> {r[4]}" for r in rows]

# ==============================================================================
# CATEGORY PRESET ENGINE
# ==============================================================================

CATEGORY_PRESETS = {
    "System Audit & Compliance": {
        "style": "professional corporate environment, sleek modern workstation, high contrast, dramatic shadows, cinematic lighting, 8k resolution",
        "cfg": 7.5,
        "steps": 30,
        "voice": "en-US-ChristopherNeural"
    },
    "Cinematic Film / Drama": {
        "style": "35mm film grain, moody atmospheric lighting, deep contrast, anamorphic lens flares, cinematic composition",
        "cfg": 8.0,
        "steps": 35,
        "voice": "en-GB-SoniaNeural"
    },
    "Cyberpunk / Tech Audit": {
        "style": "futuristic neon lighting, dark atmospheric corridor, glowing holographic interfaces, detailed hardware",
        "cfg": 7.0,
        "steps": 30,
        "voice": "en-US-JennyNeural"
    },
    "Documentary / Realism": {
        "style": "raw documentary style, natural ambient daylight, realistic textures, unpolished environment, lifelike details",
        "cfg": 6.5,
        "steps": 25,
        "voice": "en-US-ChristopherNeural"
    }
}

# ==============================================================================
# CORE RENDER ENGINE
# ==============================================================================

class ApexRenderEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.pipe = None
        self.output_dir = os.path.abspath("./outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        init_db()

    def load_models(self):
        if self.pipe is None:
            print(f"[ENGINE] Initializing Pipeline on {self.device}...")
            model_id = "runwayml/stable-diffusion-v1-5"
            
            controlnet = ControlNetModel.from_pretrained(
                "lllyasviel/sd-controlnet-openpose",
                torch_dtype=self.torch_dtype
            )
            
            self.pipe = StableDiffusionControlNetPipeline.from_pretrained(
                model_id,
                controlnet=controlnet,
                torch_dtype=self.torch_dtype,
                safety_checker=None
            )
            
            self.pipe.scheduler = DDIMScheduler.from_config(self.pipe.scheduler.config)
            
            if self.device == "cuda":
                self.pipe.enable_model_cpu_offload()
                try:
                    self.pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    print("[ENGINE] Standard attention fallback active.")
            print("[ENGINE] Pipeline successfully initialized.")

    async def _generate_audio(self, text: str, voice: str, output_path: str):
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)

    def generate_video(self, category: str, base_prompt: str, negative_prompt: str, dialogue: str, seed: int):
        self.load_models()
        
        preset = CATEGORY_PRESETS.get(category, CATEGORY_PRESETS["System Audit & Compliance"])
        full_prompt = f"{base_prompt}, {preset['style']}"
        steps = preset["steps"]
        cfg = preset["cfg"]
        voice = preset["voice"]

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(self.output_dir, f"audio_{timestamp_str}.mp3")
        temp_raw_path = os.path.join(self.output_dir, f"raw_{timestamp_str}.mp4")
        final_web_path = os.path.join(self.output_dir, f"render_{timestamp_str}.mp4")

        # 1. Synthesize Speech & Auto-Calculate Duration
        print("[AUDIO] Synthesizing audio track...")
        asyncio.run(self._generate_audio(dialogue, voice, audio_path))
        
        # Determine exact audio duration using mutagen
        audio_info = MP3(audio_path)
        duration_sec = audio_info.info.length
        fps = 24
        total_frames = int(max(24, duration_sec * fps))
        print(f"[DURATION] Dialogue duration: {duration_sec:.2f}s | Target frame count: {total_frames} frames @ {fps}fps")

        # 2. Encode Prompts Cleanly
        print(f"[RENDER] Generating frame embedding (Seed: {seed})...")
        width, height = 720, 1280
        blank_pose = PIL.Image.fromarray(np.zeros((height, width, 3), dtype=np.uint8))
        
        prompt_embeds, negative_embeds = self.pipe.encode_prompt(
            prompt=full_prompt,
            device=self.device,
            num_images_per_prompt=1,
            do_classifier_free_guidance=True,
            negative_prompt=negative_prompt
        )
        
        generator = torch.Generator(device=self.device).manual_seed(int(seed))
        
        # 3. Render Image Frame via Diffusion Pipeline
        result = self.pipe(
            prompt_embeds=prompt_embeds,
            negative_prompt_embeds=negative_embeds,
            image=blank_pose,
            num_inference_steps=int(steps),
            guidance_scale=float(cfg),
            controlnet_conditioning_scale=0.85,
            generator=generator,
            width=width,
            height=height
        )
        rendered_frame = result.images[0].filter(ImageFilter.SMOOTH_MORE)

        # 4. Write OpenCV Video Stream Matched to Audio Duration
        print("[ENCODER] Compiling video stream matched to dialogue duration...")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_raw_path, fourcc, fps, (width, height))
        numpy_frame = cv2.cvtColor(np.array(rendered_frame), cv2.COLOR_RGB2BGR)
        
        for _ in range(total_frames):
            out.write(numpy_frame)
        out.release()

        # 5. Transcode to Web-Compatible H.264 MP4
        print("[TRANSCODER] Muxing audio and video streams via FFmpeg...")
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-i', temp_raw_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-shortest',
            final_web_path
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception as e:
            print(f"[WARNING] Transcoding fallback active: {e}")
            shutil.copy(temp_raw_path, final_web_path)

        # 6. Save Record in Master Database
        register_render(category, base_prompt, dialogue, duration_sec, final_web_path)

        print("[COMPLETE] Video generation complete.")
        return final_web_path, get_registered_videos()

# ==============================================================================
# GRADIO INTERFACE
# ==============================================================================

engine = ApexRenderEngine()

def run_pipeline(category, prompt, negative_prompt, dialogue, seed):
    return engine.generate_video(category, prompt, negative_prompt, dialogue, seed)

default_neg_prompt = (
    "(deformed, distorted, disfigured:1.3), poorly drawn face, poorly drawn hands, "
    "missing fingers, extra limbs, mutated hands, fused fingers, too many fingers, bad anatomy, "
    "bad proportions, bad hands, floating limbs, disconnected limbs, mutation, ugly, blurry, duplicate, "
    "cloned face, (3d render, anime, cartoon, illustration, drawing, painting, 2d, CG, unreal engine, "
    "octane render, video game:1.4), plastic skin, wax skin, airbrushed skin, oversaturated, "
    "unrealistic lighting, watermark, signature, text overlay, captions, logo, jpeg artifacts, "
    "flickering, frame jump, jitter, temporal inconsistency, character morphing, identity drift, "
    "shaky camera, static frame, cropped, low quality, worst quality"
)

with gr.Blocks(title="Apex AI Video Studio") as demo:
    gr.Markdown("# 🎬 Apex AI Video Studio")
    
    with gr.Tabs():
        with gr.Tab("Studio Generator"):
            with gr.Row():
                with gr.Column():
                    category_select = gr.Dropdown(
                        choices=list(CATEGORY_PRESETS.keys()),
                        value="System Audit & Compliance",
                        label="Production Category Preset"
                    )
                    prompt_input = gr.Textbox(
                        label="Image Prompt", 
                        value="A realistic character standing in a dimly lit hallway, cinematic lighting, highly detailed face",
                        lines=4
                    )
                    neg_prompt_input = gr.Textbox(
                        label="Negative Prompt", 
                        value=default_neg_prompt,
                        lines=3
                    )
                    dialogue_input = gr.Textbox(
                        label="Voice Dialogue Track", 
                        value="System audit initialized. All neural cores are online and functioning at peak capacity.",
                        lines=3
                    )
                    seed_input = gr.Number(value=42, label="Seed", precision=0)

                    generate_btn = gr.Button("🚀 Generate Video Scene", variant="primary")

                with gr.Column():
                    video_output = gr.Video(label="Rendered Video Output")

        with gr.Tab("Master Video Vault"):
            gr.Markdown("### 📜 Master Render Registry")
            registry_list = gr.Dropdown(
                choices=get_registered_videos(),
                label="Saved Video Archives"
            )
            refresh_btn = gr.Button("🔄 Refresh Database Log")

    generate_btn.click(
        fn=run_pipeline,
        inputs=[category_select, prompt_input, neg_prompt_input, dialogue_input, seed_input],
        outputs=[video_output, registry_list]
    )

    refresh_btn.click(
        fn=lambda: gr.update(choices=get_registered_videos()),
        outputs=[registry_list]
    )

if __name__ == "__main__":
    output_abs = os.path.abspath("./outputs")
    os.makedirs(output_abs, exist_ok=True)
    
    # Ensure audio length calculation module is installed
    try:
        import mutagen
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "mutagen"], check=True)

    demo.queue().launch(
        inbrowser=True,
        allowed_paths=[output_abs]
    )