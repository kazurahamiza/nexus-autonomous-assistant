import os
import shutil
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from PIL import Image
import torch
from diffusers import LTXPipeline
from diffusers.utils import export_to_video

# Compatible import across MoviePy v1.x and v2.x
try:
    from moviepy import VideoFileClip
except ImportError:
    from moviepy.editor import VideoFileClip


# --- Self-Learning Brutal AI Engine ---

class SelfLearningBrutalAI:
    def __init__(self, memory_dir: str = "self_learning_brutal_ai"):
        """Initializes the memory storage and folder matrix for learning."""
        self.memory_dir = memory_dir
        self.images_dir = os.path.join(self.memory_dir, "images")
        self.videos_dir = os.path.join(self.memory_dir, "videos")
        self.dataset_dir = os.path.join(self.memory_dir, "dataset")

        # Create memory directories
        for path in [self.memory_dir, self.images_dir, self.videos_dir, self.dataset_dir]:
            os.makedirs(path, exist_ok=True)

    def ingest_and_duplicate(self, file_path: str, prompt_data: str = "") -> str:
        """Duplicates generated media across all formats into the brutal AI learning database."""
        if not os.path.exists(file_path):
            return ""

        filename = os.path.basename(file_path)
        ext = os.path.splitext(filename)[1].lower()

        # Categorize pictures vs videos
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp"]:
            target_folder = self.images_dir
        elif ext in [".mp4", ".mkv", ".avi", ".mov", ".gif"]:
            target_folder = self.videos_dir
        else:
            target_folder = self.dataset_dir

        dest_path = os.path.join(target_folder, filename)
        shutil.copy2(file_path, dest_path)

        # Record generation metadata into learning dataset
        meta_file = os.path.join(self.dataset_dir, "learning_history.txt")
        with open(meta_file, "a", encoding="utf-8") as f:
            f.write(f"FILE: {filename} | TYPE: {ext} | PROMPT: {prompt_data}\n")

        # Execute learning routine and purge staging memory
        self.process_and_clear_learning_staging()

        return dest_path

    def process_and_clear_learning_staging(self):
        """Processes training logic and clears staging media files once learning is complete."""
        print("[Brutal AI Engine] Ingesting parameters and updating neural memory...")
        for folder in [self.images_dir, self.videos_dir]:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error clearing staging file {file_path}: {e}")
        print("[Brutal AI Engine] Learning complete. Staging folder cleared.")


# --- Universal Video & Media Generator ---

class UniversalVideoEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.pipe = None

        self.preset_resolutions = {
            "16:9 (Landscape)": (768, 512),
            "9:16 (Vertical Reel)": (512, 768),
            "1:1 (Square Social)": (512, 512),
            "21:9 (Ultrawide Movie)": (896, 384),
        }

        # Universal Category Matrix
        self.categories = {
            "Cinematic Realism": {
                "suffix": ", shot on 35mm lens, 8k resolution, cinematic volumetric lighting, photorealistic, continuous smooth motion, 24fps film look",
                "default_aspect": "16:9 (Landscape)"
            },
            "Audit & Corporate Compliance": {
                "suffix": ", clean professional corporate aesthetic, ultra-sharp detail, balanced neutral studio lighting, static camera placement, high-definition presentation style",
                "default_aspect": "16:9 (Landscape)"
            },
            "Technical & Security Analysis": {
                "suffix": ", high-contrast monitoring feed, detailed forensic clarity, precise focal tracking, sharp edges, uncompressed surveillance analysis style",
                "default_aspect": "16:9 (Landscape)"
            },
            "TikTok / Shorts / Reels": {
                "suffix": ", trending vertical smartphone camera style, high dynamic contrast, sharp focus, energetic motion, crisp bright lighting",
                "default_aspect": "9:16 (Vertical Reel)"
            },
            "Anime & 2D Stylized": {
                "suffix": ", vivid anime art style, makoto shinkai aesthetic, smooth animation keyframes, crisp cel shading, clean linework",
                "default_aspect": "16:9 (Landscape)"
            },
            "3D Animation & CGI": {
                "suffix": ", octaneweb render, pixar cinematic quality, raytraced subsurface scattering, vibrant color grading, smooth 3d motion",
                "default_aspect": "16:9 (Landscape)"
            },
            "Commercial Product Showcase": {
                "suffix": ", studio macro shot, elegant turntable slow rotation, softbox diffuse lighting, 8k photorealism, pristine surface details",
                "default_aspect": "1:1 (Square Social)"
            },
            "Cyberpunk & Sci-Fi": {
                "suffix": ", neon-lit dystopian cyber aesthetic, volumetric fog, anamorphic lens flares, chrome reflections, dark futuristic tones",
                "default_aspect": "21:9 (Ultrawide Movie)"
            },
            "Documentary & Archival": {
                "suffix": ", natural ambient lighting, handheld realistic camera tracking, organic film grain, authentic color tones, documentary film look",
                "default_aspect": "16:9 (Landscape)"
            },
            "Abstract & Surrealism": {
                "suffix": ", dreamlike atmosphere, fluid morphing textures, surreal color grading, ethereal lighting effects, slow-motion fluid physics",
                "default_aspect": "16:9 (Landscape)"
            }
        }

        self.output_dir = "generated_outputs"
        os.makedirs(self.output_dir, exist_ok=True)
        self.brutal_ai = SelfLearningBrutalAI()

    def load_model(self, model_id: str = "Lightricks/LTX-Video"):
        if self.pipe is None:
            self.pipe = LTXPipeline.from_pretrained(
                model_id, torch_dtype=self.torch_dtype
            ).to(self.device)

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str,
        category: str,
        aspect_ratio: str,
        num_frames: int,
        fps: int,
        output_filename: str,
    ) -> str:
        self.load_model()

        # Apply selected category style suffix
        category_data = self.categories.get(category, {})
        full_prompt = prompt + category_data.get("suffix", "")

        width, height = self.preset_resolutions[aspect_ratio]

        video_frames = self.pipe(
            prompt=full_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            num_inference_steps=50,
            guidance_scale=6.0,
        ).frames[0]

        temp_path = os.path.join(self.output_dir, "temp_raw_output.mp4")
        export_to_video(video_frames, temp_path, fps=fps)

        # Save to output folder
        final_output_path = os.path.join(self.output_dir, output_filename)
        self.post_process_media(temp_path, final_output_path)

        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Duplicate into Self-Learning Brutal AI directory
        self.brutal_ai.ingest_and_duplicate(final_output_path, full_prompt)

        return final_output_path

    @staticmethod
    def post_process_media(input_path: str, output_path: str) -> str:
        ext = os.path.splitext(output_path)[1].lower()

        if ext in [".jpg", ".png", ".webp", ".bmp"]:
            clip = VideoFileClip(input_path)
            frame = clip.get_frame(0)
            img = Image.fromarray(frame)
            img.save(output_path)
            clip.close()
        else:
            clip = VideoFileClip(input_path)
            clip.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                pixel_format="yuv420p",
                verbose=False,
                logger=None,
            )
            clip.close()

        return output_path


# --- Graphical Interface ---

engine = UniversalVideoEngine()


def on_category_change(event):
    selected_cat = category_dropdown.get()
    default_aspect = engine.categories[selected_cat]["default_aspect"]
    aspect_ratio_var.set(default_aspect)


def run_generator():
    prompt = prompt_entry.get("1.0", tk.END).strip()
    neg_prompt = neg_prompt_entry.get("1.0", tk.END).strip()
    category = category_var.get()
    aspect_ratio = aspect_ratio_var.get()
    output_filename = output_entry.get().strip()

    if not prompt:
        messagebox.showwarning("Warning", "Please enter a visual prompt.")
        return

    if not output_filename:
        output_filename = "master_output.mp4"

    btn.config(state="disabled")
    status_label.config(text=f"Status: Generating [{category}] & Syncing Brutal AI...", fg="yellow")

    def worker():
        try:
            output_path = engine.generate_video(
                prompt=prompt,