import os
import sys
import cv2
import json
import time
import torch
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
PROCESSED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "upscaled")

os.makedirs(PROCESSED_OUTPUT_DIR, exist_ok=True)

class MotionAndUpscaleEngine:
    """Post-processing pipeline for 60FPS frame interpolation & resolution scaling."""

    @staticmethod
    def inspect_video_stream(video_path):
        """Extracts stream parameters via OpenCV."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        return {"fps": fps, "width": width, "height": height, "frame_count": frame_count}

    @staticmethod
    def process_video_enhancement(input_path, target_fps=60, scale_factor=2):
        """Enhances input video frame rate and resolution using FFmpeg filters."""
        if not os.path.exists(input_path):
            logging.error(f"[!] Input video file does not exist: {input_path}")
            return None

        filename = os.path.basename(input_path)
        name_no_ext, ext = os.path.splitext(filename)
        output_filename = f"{name_no_ext}_enhanced_60fps{ext}"
        output_path = os.path.join(PROCESSED_OUTPUT_DIR, output_filename)

        meta = MotionAndUpscaleEngine.inspect_video_stream(input_path)
        if not meta:
            return None

        target_width = meta["width"] * scale_factor
        target_height = meta["height"] * scale_factor

        logging.info(f"[*] [MotionEngine] Enhancing '{filename}' -> Target: {target_width}x{target_height} @ {target_fps} FPS...")

        # FFmpeg filter pipeline: Interpolate motion & upscale bicubic
        filter_str = f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir,scale={target_width}:{target_height}:flags=lanczos"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", filter_str,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-c:a", "copy",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                logging.info(f"[+] [MotionEngine] Enhancement complete: '{output_path}'")
                
                # Log enhanced output to master database
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO assets (filename, filepath, category, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (output_filename, output_path, "Enhanced AI Render", now_str))
                conn.commit()
                conn.close()

                return output_path
            else:
                logging.warning(f"[!] FFmpeg motion processing fallback: {result.stderr[:200]}")
                return input_path
        except Exception as e:
            logging.error(f"[!] Processing exception: {e}")
            return input_path

if __name__ == "__main__":
    logging.info("[*] Launching Motion Interpolation & Upscale Engine Test...")
    # Test pipeline initialization
    test_video = os.path.join(BASE_DIR, "videos", "sample.mp4")
    if os.path.exists(test_video):
        MotionAndUpscaleEngine.process_video_enhancement(test_video)
    else:
        logging.info("[+] Engine initialized and awaiting video render inputs.")