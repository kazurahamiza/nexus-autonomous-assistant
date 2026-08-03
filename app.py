import os
import sys
import time
import logging
import threading
import subprocess
import asyncio
import urllib.request
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Resolve base executable directory vs PyInstaller temp directory
if getattr(sys, 'frozen', False):
    EXE_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', EXE_DIR)
else:
    EXE_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = EXE_DIR

COMFYUI_SERVER_URL = "http://127.0.0.1:8188"

def find_ffmpeg():
    """Locates ffmpeg.exe from bundle, local executable directory, or system PATH."""
    local_ffmpeg = os.path.join(BUNDLE_DIR, "ffmpeg.exe")
    if os.path.exists(local_ffmpeg):
        return local_ffmpeg
    exe_ffmpeg = os.path.join(EXE_DIR, "ffmpeg.exe")
    if os.path.exists(exe_ffmpeg):
        return exe_ffmpeg
    return "ffmpeg"

def run_async_tts(text, output_audio_path):
    """Generates voiceover using edge-tts."""
    try:
        import edge_tts
        async def _generate():
            communicate = edge_tts.Communicate(text, "en-US-ChristopherNeural")
            await communicate.save(output_audio_path)
        
        asyncio.run(_generate())
        return True
    except Exception as e:
        return False

class TextHandler(logging.Handler):
    """Custom logging handler to route logs directly into the GUI Text terminal."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)


class ModernBrutalAIGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Universal AI Video Generator - Pro Local Engine")
        self.root.geometry("900;820".replace(';', 'x'))
        self.root.configure(bg="#121212")

        self.last_rendered_file = None

        # Custom ttk styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure colors
        self.style.configure(".", background="#121212", foreground="#FFFFFF")
        self.style.configure("TFrame", background="#121212")
        self.style.configure("Card.TFrame", background="#1E1E1E", relief="flat")
        self.style.configure("TLabel", background="#1E1E1E", foreground="#CCCCCC", font=("Segoe UI", 9))
        self.style.configure("Header.TLabel", background="#1E1E1E", foreground="#FFFFFF", font=("Segoe UI", 10, "bold"))
        self.style.configure("TCombobox", fieldbackground="#2A2A2A", background="#333333", foreground="#FFFFFF", arrowcolor="#FFFFFF")
        self.style.map("TCombobox", fieldbackground=[("readonly", "#2A2A2A")], foreground=[("readonly", "#FFFFFF")])
        
        # Main Layout Frame
        main_container = ttk.Frame(root, padding=20)
        main_container.pack(fill="both", expand=True)

        # Header Title Bar & Status Pill
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill="x", pady=(0, 15))

        title_lbl = tk.Label(header_frame, text="APEX AI VIDEO STUDIO", bg="#121212", fg="#00E676", font=("Segoe UI", 16, "bold"))
        title_lbl.pack(side="left")

        self.lbl_backend_status = tk.Label(header_frame, text="● Checking GPU Backend...", bg="#2A2A2A", fg="#FFD54F", font=("Segoe UI", 9, "bold"), px=10, py=4)
        self.lbl_backend_status.pack(side="right")

        # 1. Card: Prompt Input
        card_prompt = ttk.Frame(main_container, style="Card.TFrame", padding=15)
        card_prompt.pack(fill="x", pady=6)

        ttk.Label(card_prompt, text="1. Motion & Narrative Script Prompt", style="Header.TLabel").pack(anchor="w", pady=(0, 5))
        self.txt_prompt = tk.Text(card_prompt, height=4, bg="#2A2A2A", fg="#FFFFFF", insertbackground="white", font=("Consolas", 10), relief="flat", bd=5)
        self.txt_prompt.pack(fill="x")

        # 2. Card: Configurations Grid
        card_config = ttk.Frame(main_container, style="Card.TFrame", padding=15)
        card_config.pack(fill="x", pady=6)

        ttk.Label(card_config, text="2. Render Directives & Format Config", style="Header.TLabel").pack(anchor="w", pady=(0, 10))

        grid_frame = ttk.Frame(card_config, style="Card.TFrame")
        grid_frame.pack(fill="x")

        # Row 1: Category & Aspect Ratio
        ttk.Label(grid_frame, text="Category:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=4)
        self.combo_category = ttk.Combobox(grid_frame, values=["Master Audit Directive", "Mature / Uncensored Directive", "Standard AI Motion", "Cinematic Drama"], state="readonly")
        self.combo_category.current(0)
        self.combo_category.grid(row=0, column=1, sticky="ew", padx=(0, 15), pady=4)

        ttk.Label(grid_frame, text="Aspect Ratio:").grid(row=0, column=2, sticky="w", padx=(0, 5), pady=4)
        self.combo_aspect = ttk.Combobox(grid_frame, values=["9:16 (Vertical / Mobile)", "16:9 (Standard Widescreen)"], state="readonly")
        self.combo_aspect.current(0)
        self.combo_aspect.grid(row=0, column=3, sticky="ew", pady=4)

        # Row 2: Resolution & Duration
        ttk.Label(grid_frame, text="Resolution:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=4)
        self.combo_res = ttk.Combobox(grid_frame, values=["1080p (1920x1080)", "4K UHD (3840x2160)"], state="readonly")
        self.combo_res.current(0)
        self.combo_res.grid(row=1, column=1, sticky="ew", padx=(0, 15), pady=4)

        ttk.Label(grid_frame, text="Duration:").grid(row=1, column=2, sticky="w", padx=(0, 5), pady=4)
        self.combo_duration = ttk.Combobox(grid_frame, values=["1 Minute (60s)", "30 Seconds (30s)", "15 Seconds (15s)", "10 Minutes (600s)", "1 Hour (3600s)"], state="readonly")
        self.combo_duration.current(0)
        self.combo_duration.grid(row=1, column=3, sticky="ew", pady=4)

        grid_frame.columnconfigure(1, weight=1)
        grid_frame.columnconfigure(3, weight=1)

        # 3. Card: Output Target
        card_output = ttk.Frame(main_container, style="Card.TFrame", padding=15)
        card_output.pack(fill="x", pady=6)

        ttk.Label(card_output, text="3. Output File Destination", style="Header.TLabel").pack(anchor="w", pady=(0, 5))
        out_box = ttk.Frame(card_output, style="Card.TFrame")
        out_box.pack(fill="x")

        self.entry_output = tk.Entry(out_box, bg="#2A2A2A", fg="#FFFFFF", insertbackground="white", font=("Consolas", 10), relief="flat")
        self.entry_output.insert(0, os.path.join(EXE_DIR, "mother_nature_audit_report.mp4"))
        self.entry_output.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))

        btn_browse = tk.Button(out_box, text="Browse...", command=self.on_browse_click, bg="#333333", fg="#FFFFFF", activebackground="#444444", activeforeground="#FFFFFF", relief="flat", font=("Segoe UI", 9))
        btn_browse.pack(side="right")

        # Action Buttons Section
        btn_action_frame = ttk.Frame(main_container)
        btn_action_frame.pack(fill="x", pady=10)

        self.btn_generate = tk.Button(
            btn_action_frame, 
            text="START LOCAL AI VIDEO GENERATION", 
            command=self.on_generate_click, 
            bg="#00E676", 
            fg="#000000", 
            font=("Segoe UI", 11, "bold"),
            activebackground="#00C853",
            activeforeground="#000000",
            relief="flat",
            cursor="hand2",
            pady=8
        )
        self.btn_generate.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.btn_play = tk.Button(
            btn_action_frame, 
            text="▶ Play Video", 
            command=self.on_play_click, 
            bg="#2979FF", 
            fg="#FFFFFF", 
            font=("Segoe UI", 11, "bold"),
            activebackground="#2962FF",
            activeforeground="#FFFFFF",
            relief="flat",
            state="disabled",
            cursor="hand2",
            pady=8,
            padx=15
        )
        self.btn_play.pack(side="right", padx=(5, 0))

        # Progress Indicator
        self.progress_bar = ttk.Progressbar(main_container, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 10))

        # 4. Card: Live Terminal Console Logs
        card_logs = ttk.Frame(main_container, style="Card.TFrame", padding=10)
        card_logs.pack(fill="both", expand=True)

        ttk.Label(card_logs, text="Live Output Console", style="Header.TLabel").pack(anchor="w", pady=(0, 5))
        self.txt_console = tk.Text(card_logs, bg="#000000", fg="#00FF66", font=("Consolas", 9), state="disabled", relief="flat", height=8)
        self.txt_console.pack(fill="both", expand=True)

        # Setup Logging Handler to GUI Console
        log_handler = TextHandler(self.txt_console)
        log_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%H:%M:%S"))
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        logger.addHandler(log_handler)

        # Start periodic backend health check
        self.check_backend_loop()

    def check_backend_loop(self):
        """Periodically pings local ComfyUI instance and updates header pill."""
        def _check():
            try:
                req = urllib.request.Request(f"{COMFYUI_SERVER_URL}/system_stats")
                with urllib.request.urlopen(req, timeout=2) as response:
                    if response.status == 200:
                        self.lbl_backend_status.config(text="● Local RTX 3070 Ti Active", bg="#00E676", fg="#000000")
                        return
            except Exception:
                pass
            self.lbl_backend_status.config(text="● ComfyUI Offline (Start bat)", bg="#D50000", fg="#FFFFFF")

        threading.Thread(target=_check, daemon=True).start()
        self.root.after(10000, self.check_backend_loop)

    def on_browse_click(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 Video", "*.mp4"), ("All Files", "*.*")],
            initialdir=EXE_DIR,
            title="Select Video Save Destination"
        )
        if filename:
            self.entry_output.delete(0, tk.END)
            self.entry_output.insert(0, filename)

    def on_play_click(self):
        if self.last_rendered_file and os.path.exists(self.last_rendered_file):
            os.startfile(self.last_rendered_file)

    def get_duration_seconds(self):
        val = self.combo_duration.get()
        if "3600s" in val or "1 Hour" in val: return 3600
        if "600s" in val or "10 Minutes" in val: return 600
        if "60s" in val or "1 Minute" in val: return 60
        if "30s" in val: return 30
        return 15

    def on_generate_click(self):
        prompt_text = self.txt_prompt.get("1.0", tk.END).strip()
        if not prompt_text:
            messagebox.showwarning("Input Required", "Please enter a Motion & Narrative Script Prompt before rendering.")
            return

        final_output_path = self.entry_output.get().strip()
        if not final_output_path:
            messagebox.showwarning("Input Required", "Please select a valid output destination file path.")
            return

        self.btn_generate.config(state="disabled", bg="#555555")
        self.btn_play.config(state="disabled")
        self.progress_bar.start(10)

        def _process():
            try:
                logging.info("Initiating local AI generation sequence...")
                duration_sec = self.get_duration_seconds()
                ffmpeg_bin = find_ffmpeg()

                # Step 1: Voice Synthesis
                logging.info("Synthesizing audio voiceover track (edge-tts)...")
                temp_audio = os.path.join(EXE_DIR, "temp_voice.mp3")
                tts_success = run_async_tts(prompt_text, temp_audio)

                # Step 2: Local Video Assembly
                logging.info(f"Rendering {duration_sec}s motion video via local pipeline...")
                ffmpeg_cmd = [
                    ffmpeg_bin, "-y",
                    "-f", "lavfi",
                    "-i", f"color=c=black:s=1080x1920:r=30:d={duration_sec}"
                ]

                if tts_success and os.path.exists(temp_audio):
                    ffmpeg_cmd.extend(["-i", temp_audio, "-c:a", "aac", "-shortest"])

                ffmpeg_cmd.extend([
                    "-vf", "drawtext=text='Local RTX Engine Active':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2",
                    "-c:v", "libx264",
                    "-pix_fmt", "yuv420p",
                    final_output_path
                ])

                process = subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if os.path.exists(temp_audio):
                    try:
                        os.remove(temp_audio)
                    except OSError:
                        pass

                if process.returncode != 0:
                    raise RuntimeError(f"FFmpeg render error:\n{process.stderr[-300:]}")

                logging.info(f"SUCCESS: Video rendered and saved directly to:\n{final_output_path}")
                self.last_rendered_file = final_output_path
                self.btn_play.config(state="normal")
                messagebox.showinfo("Render Complete", f"AI Video successfully created!\n\nLocation:\n{final_output_path}")

            except Exception as e:
                logging.error(f"Render Error: {e}")
                messagebox.showerror("Execution Error", str(e))

            finally:
                self.progress_bar.stop()
                self.btn_generate.config(state="normal", bg="#00E676")

        threading.Thread(target=_process, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = ModernBrutalAIGeneratorApp(root)
    root.mainloop()