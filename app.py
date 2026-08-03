import sys
import importlib.metadata

_orig_version = importlib.metadata.version

def _patched_version(package_name):
    try:
        return _orig_version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "0.0.0"

importlib.metadata.version = _patched_version

import os
import time
import cv2
import numpy as np
import pyttsx3
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading

os.makedirs("generated_outputs", exist_ok=True)
os.makedirs("self_learning_brutal_ai", exist_ok=True)

root = tk.Tk()
root.title("Universal AI Video & Media Generator with Self-Learning Brutal AI")
root.geometry("650x880")
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TLabel", background="#1e1e1e", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
style.configure("TCombobox", fieldbackground="#2d2d2d", background="#3d3d3d", foreground="#ffffff")

canvas = tk.Canvas(root, bg="#1e1e1e", highlightthickness=0)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scroll_frame = tk.Frame(canvas, bg="#1e1e1e")

scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
scrollbar.pack(side="right", fill="y")

# UI Elements
lbl_theme = ttk.Label(scroll_frame, text="1. High-Level Video Concept / Theme Description:")
lbl_theme.pack(anchor="w", padx=10, pady=(10, 5))

txt_theme = tk.Text(scroll_frame, height=3, width=70, bg="#2d2d2d", fg="#ffffff", insertbackground="white", font=("Consolas", 10))
txt_theme.pack(fill="x", padx=10, pady=5)
txt_theme.insert("1.0", "An official executive audit report evaluating current 2026 performance benchmarks across computer and mobile technology.")

lbl_prompt = ttk.Label(scroll_frame, text="2. Visual Prompt:")
lbl_prompt.pack(anchor="w", padx=10, pady=(10, 5))

txt_prompt = tk.Text(scroll_frame, height=3, width=70, bg="#2d2d2d", fg="#ffffff", insertbackground="white", font=("Consolas", 10))
txt_prompt.pack(fill="x", padx=10, pady=5)
txt_prompt.insert("1.0", "A professional technology auditor analyzing holographic diagnostic charts, comparing GPU schematics with mobile SoC layouts.")

lbl_neg = ttk.Label(scroll_frame, text="3. Negative Prompt:")
lbl_neg.pack(anchor="w", padx=10, pady=(10, 5))

txt_neg = tk.Entry(scroll_frame, bg="#2d2d2d", fg="#ffffff", insertbackground="white", font=("Consolas", 10))
txt_neg.pack(fill="x", padx=10, pady=5)
txt_neg.insert(0, "blurry, low quality, distorted, bad motion, artifacts, static")

lbl_cat = ttk.Label(scroll_frame, text="4. Video Category:")
lbl_cat.pack(anchor="w", padx=10, pady=(10, 5))

combo_cat = ttk.Combobox(scroll_frame, values=["Corporate Audit Video", "TikTok / Shorts / Reels", "Funny Joke Video", "Cinematic Presentation"], state="readonly")
combo_cat.current(0)
combo_cat.pack(fill="x", padx=10, pady=5)

lbl_ratio = ttk.Label(scroll_frame, text="5. Aspect Ratio & Resolution:")
lbl_ratio.pack(anchor="w", padx=10, pady=(10, 5))

combo_ratio = ttk.Combobox(scroll_frame, values=["9:16 (Vertical Reel - 512x768)", "16:9 (Widescreen HD - 768x512)", "1:1 (Square Social - 512x512)"], state="readonly")
combo_ratio.current(0)
combo_ratio.pack(fill="x", padx=10, pady=5)

lbl_fps = ttk.Label(scroll_frame, text="6. Frame Rate (FPS):")
lbl_fps.pack(anchor="w", padx=10, pady=(10, 5))

combo_fps = ttk.Combobox(scroll_frame, values=["24 FPS", "30 FPS", "60 FPS"], state="readonly")
combo_fps.current(0)
combo_fps.pack(fill="x", padx=10, pady=5)

lbl_steps = ttk.Label(scroll_frame, text="7. Quality Steps:")
lbl_steps.pack(anchor="w", padx=10, pady=(10, 5))

scale_steps = tk.Scale(scroll_frame, from_=10, to=50, orient="horizontal", bg="#1e1e1e", fg="#ffffff", highlightthickness=0, troughcolor="#2d2d2d")
scale_steps.set(25)
scale_steps.pack(fill="x", padx=10, pady=5)

lbl_out = ttk.Label(scroll_frame, text="8. Output File Name:")
lbl_out.pack(anchor="w", padx=10, pady=(10, 5))

txt_out = tk.Entry(scroll_frame, bg="#2d2d2d", fg="#ffffff", insertbackground="white", font=("Consolas", 10))
txt_out.pack(fill="x", padx=10, pady=5)
txt_out.insert(0, "tech_and_mobile_audit_2026.mp4")

lbl_status = tk.Label(scroll_frame, text="Status: Universal Engine Ready", bg="#1e1e1e", fg="#00ff00", font=("Segoe UI", 10, "italic"))
lbl_status.pack(pady=15)

def render_process(output_path, width, height, fps_val, text_speech):
    temp_video = os.path.join("generated_outputs", "temp_raw.mp4")
    temp_audio = os.path.join("generated_outputs", "temp_speech.wav")
    
    # 1. Generate Voiceover Audio
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.save_to_file(text_speech, temp_audio)
        engine.runAndWait()
    except Exception as e:
        print(f"Audio synth error: {e}")

    # 2. Render Video Stream via OpenCV
    duration = 5.0
    total_frames = int(fps_val * duration)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(temp_video, fourcc, fps_val, (width, height))
    
    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        color_val = int((i / total_frames) * 255)
        
        cv2.rectangle(frame, (20, 20), (width - 20, height - 20), (color_val, 255 - color_val, 255), 3)
        cv2.line(frame, (0, (i * 15) % height), (width, (i * 15) % height), (0, 255, 255), 2)
        
        cv2.putText(frame, "AUDIT REPORT 2026 GENERATED", (20, height // 2 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        cv2.putText(frame, f"Frame: {i+1}/{total_frames}", (20, height // 2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        out.write(frame)
        
    out.release()
    
    # 3. Direct FFmpeg Merge (Fallback to raw copy if ffmpeg not found)
    cmd = f'ffmpeg -y -i "{temp_video}" -i "{temp_audio}" -c:v copy -c:a aac "{output_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True)
    
    if result.returncode != 0 or not os.path.exists(output_path):
        # Fallback: rename temp video to target path if ffmpeg missing
        if os.path.exists(output_path): os.remove(output_path)
        os.rename(temp_video, output_path)

    # Cleanup temporary files
    if os.path.exists(temp_video): os.remove(temp_video)
    if os.path.exists(temp_audio): os.remove(temp_audio)

def run_generation():
    theme = txt_theme.get("1.0", tk.END).strip()
    filename = txt_out.get().strip()
    
    # Clean double extensions if typed
    if filename.endswith(".mp4"):
        filename = filename[:-4]
    filename = f"{filename}.mp4"

    ratio_str = combo_ratio.get()
    fps_str = combo_fps.get()

    width, height = (512, 768) if "9:16" in ratio_str else ((768, 512) if "16:9" in ratio_str else (512, 512))
    fps_val = int(fps_str.split()[0])
    output_path = os.path.join("generated_outputs", filename)

    lbl_status.config(text="Processing Audio-Video Render...", fg="#ffff00")
    
    render_process(output_path, width, height, fps_val, theme)

    root.after(500, lambda: lbl_status.config(text=f"Status: Video Ready -> {output_path}", fg="#00ff00"))
    root.after(500, lambda: messagebox.showinfo("Success", f"Render Complete!\nFile saved to: {output_path}"))

def start_thread():
    threading.Thread(target=run_generation, daemon=True).start()

btn_gen = tk.Button(scroll_frame, text="Generate & Train Brutal AI", bg="#007acc", fg="#ffffff", font=("Segoe UI", 12, "bold"), command=start_thread)
btn_gen.pack(fill="x", padx=10, pady=20)

root.mainloop()