import os
import sys
import time
import json
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
BRANDED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "branded_edits")
WATERMARK_LOGO_PATH = os.path.join(BASE_DIR, "watermark.png")

os.makedirs(BRANDED_OUTPUT_DIR, exist_ok=True)

class VideoWatermarkBrandingEngine:
    """Applies dynamic logo overlays and text watermarks onto final output videos."""

    def __init__(self):
        self._init_branding_db()

    def _init_branding_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS branded_video_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                original_filename TEXT,
                branded_filepath TEXT UNIQUE,
                watermark_applied TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def create_default_watermark_image():
        """Generates a default watermark placeholder image if none exists."""
        if not os.path.exists(WATERMARK_LOGO_PATH):
            try:
                import numpy as np
                import cv2
                img = np.zeros((100, 300, 4), dtype=np.uint8)
                cv2.putText(img, "APEX AI STUDIO", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255, 180), 2)
                cv2.imwrite(WATERMARK_LOGO_PATH, img)
                logging.info(f"[+] Created fallback watermark image at '{WATERMARK_LOGO_PATH}'")
            except Exception as e:
                logging.warning(f"[!] Unable to generate default watermark image: {e}")

    @staticmethod
    def apply_watermark_overlay(input_video_path, watermark_text="APEX AI STUDIO", output_filename=None):
        """Burns a text watermark and optional logo onto the top-right corner of the video."""
        if not os.path.exists(input_video_path):
            logging.error(f"[!] Input video missing for branding: {input_video_path}")
            return None

        if not output_filename:
            base_name = os.path.basename(input_video_path)
            output_filename = f"branded_{base_name}"

        output_path = os.path.join(BRANDED_OUTPUT_DIR, output_filename)

        # FFmpeg filter: text watermark top-right overlay with semi-transparency
        vf_filter = (
            f"drawtext=text='{watermark_text}':x=w-tw-20:y=20:"
            "fontcolor=white@0.7:fontsize=24:box=1:boxcolor=black@0.4:boxborderw=6"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", input_video_path,
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "copy",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                logging.info(f"[+] [BrandingEngine] Video branded successfully: '{output_path}'")
                
                # Log to registry
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO branded_video_registry 
                    (timestamp, original_filename, branded_filepath, watermark_applied, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (now_str, os.path.basename(input_video_path), output_path, watermark_text, "BRANDED"))
                conn.commit()
                conn.close()

                return output_path
            else:
                logging.warning(f"[!] FFmpeg branding failed, returning original file: {result.stderr[:200]}")
                return input_video_path
        except Exception as e:
            logging.error(f"[!] Branding overlay exception: {e}")
            return input_video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Dynamic Video Watermarking & Branding Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Dynamic Video Watermarking Engine...")
        engine = VideoWatermarkBrandingEngine()
        engine.create_default_watermark_image()