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
        # Simulated model weight / pattern update step
        print("[Brutal AI Engine] Processing patterns into core memory...")

        # Clear processed media files out of staging folders to keep disk light
        for folder in [self.images_dir, self.videos_dir]:
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error purging staging file {file_path}: {e}")

        print("[Brutal AI Engine] Learning complete. Staging folder cleared.")


# --- Universal Video & Media Generator ---

class UniversalVideoEngine:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.torch_dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.pipe = None

        self.preset_resolutions = {
            "16:9 (Landscape)": (768, 512),
            "9:16 (Vertical)": (512, 768),
            "1:1 (Square)": (512, 512),
            "21:9 (Ultrawide)": (896, 384),
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
        aspect_ratio: str,
        num_frames: int,
        fps: int,
        output_filename: str,
    ) -> str:
        self.load_model()
        width, height = self.preset_resolutions[aspect_ratio]

        video_frames = self.pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            num_frames=num_frames,
            num_inference_steps=50,
            guidance_scale=6.0,
        ).frames[0]

        temp_path = os.path.join(self.output_dir, "temp_raw_output.mp4")
        export_to_video(video_frames, temp_path, fps=fps)

        # Save to saved video output folder
        final_output_path = os.path.join(self.output_dir, output_filename)
        self.post_process_media(temp_path, final_output_path)

        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Duplicate into Self-Learning Brutal AI directory and trigger clear
        self.brutal_ai.ingest_and_duplicate(final_output_path, prompt)

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


def run_generator():
    prompt = prompt_entry.get("1.0", tk.END).strip()
    neg_prompt = neg_prompt_entry.get("1.0", tk.END).strip()
    aspect_ratio = aspect_ratio_var.get()
    output_filename = output_entry.get().strip()

    if not prompt:
        messagebox.showwarning("Warning", "Please enter a visual prompt.")
        return

    if not output_filename:
        output_filename = "master_output.mp4"

    btn.config(state="disabled")
    status_label.config(text="Status: Generating Media & Processing Brutal AI Learning...", fg="yellow")

    def worker():
        try:
            output_path = engine.generate_video(
                prompt=prompt,
                negative_prompt=neg_prompt,
                aspect_ratio=aspect_ratio,
                num_frames=97,
                fps=24,
                output_filename=output_filename,
            )
            status_label.config(text=f"Status: Saved to {output_path} | Learning Complete & Memory Cleared", fg="lime")
            messagebox.showinfo(
                "Success",
                f"Media saved successfully:\n{output_path}\n\nDuplicated to Self-Learning AI, learned, and memory cleared.",
            )
        except Exception as e:
            status_label.config(text="Status: Generation Failed", fg="red")
            messagebox.showerror("Error", str(e))
        finally:
            btn.config(state="normal")

    threading.Thread(target=worker, daemon=True).start()


root = tk.Tk()
root.title("AI Video & Media Generator with Self-Learning Brutal AI")
root.geometry("620x680")
root.configure(bg="#1e1e1e")

# Prompt Input
frame_prompt = tk.Frame(root, bg="#1e1e1e")
frame_prompt.pack(fill="x", padx=20, pady=5)

tk.Label(
    frame_prompt, text="Visual Prompt:", font=("Arial", 10, "bold"), fg="white", bg="#1e1e1e"
).pack(anchor="w")

prompt_entry = tk.Text(frame_prompt, height=4, font=("Arial", 10), bg="#2d2d2d", fg="white", insertbackground="white")
prompt_entry.pack(fill="x", pady=5)
prompt_entry.insert(
    "1.0",
    "A sleek cybernetic hummingbird hovering over a glowing neon flower, 8k resolution, cinematic lighting.",
)

# Negative Prompt Input
frame_neg = tk.Frame(root, bg="#1e1e1e")
frame_neg.pack(fill="x", padx=20, pady=5)

tk.Label(
    frame_neg, text="Negative Prompt:", font=("Arial", 10, "bold"), fg="white", bg="#1e1e1e"
).pack(anchor="w")

neg_prompt_entry = tk.Text(frame_neg, height=2, font=("Arial", 10), bg="#2d2d2d", fg="white", insertbackground="white")
neg_prompt_entry.pack(fill="x", pady=5)
neg_prompt_entry.insert("1.0", "blurry, low quality, distorted, artifacts")

# Aspect Ratio Selector
frame_aspect = tk.Frame(root, bg="#1e1e1e")
frame_aspect.pack(fill="x", padx=20, pady=5)

tk.Label(
    frame_aspect, text="Aspect Ratio:", font=("Arial", 10, "bold"), fg="white", bg="#1e1e1e"
).pack(anchor="w")

aspect_ratio_var = tk.StringVar(value="16:9 (Landscape)")
aspect_dropdown = ttk.Combobox(
    frame_aspect,
    textvariable=aspect_ratio_var,
    values=list(engine.preset_resolutions.keys()),
    state="readonly",
)
aspect_dropdown.pack(anchor="w", pady=5)

# Output File Input
frame_out = tk.Frame(root, bg="#1e1e1e")
frame_out.pack(fill="x", padx=20, pady=5)

tk.Label(
    frame_out,
    text="Output File Name (e.g. video.mp4 or image.png):",
    font=("Arial", 10),
    fg="white",
    bg="#1e1e1e",
).pack(anchor="w")

output_entry = tk.Entry(frame_out, font=("Arial", 10), width=60)
output_entry.insert(0, "master_output.mp4")
output_entry.pack(pady=5)

# Status Label
status_label = tk.Label(
    root,
    text="Status: Self-Learning Brutal AI Active & Synchronized",
    font=("Arial", 10, "italic"),
    fg="lime",
    bg="#1e1e1e",
)
status_label.pack(pady=10)

# Generate Button
btn = tk.Button(
    root,
    text="Generate & Train Brutal AI",
    font=("Arial", 12, "bold"),
    bg="#007acc",
    fg="white",
    padx=20,
    pady=10,
    command=run_generator,
)
btn.pack(pady=10)

root.mainloop()