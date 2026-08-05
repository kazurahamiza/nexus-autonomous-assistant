import os
import sys
import json
import time
import cv2
import sqlite3
import logging
import subprocess
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
FINAL_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "final_edits")

os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

class AutomatedVideoEditor:
    """Combines voice tracks, visual video clips, and dataset keyframes with audio-synced cuts."""

    @staticmethod
    def get_audio_duration_ffmpeg(audio_path):
        """Extracts exact audio duration using FFprobe."""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception as e:
            logging.error(f"[!] FFprobe audio duration extraction error: {e}")
        return 5.0

    @staticmethod
    def composite_video_and_audio(video_path, audio_path, output_name=None):
        """Muxes video and audio, trimming or looping video to match exact audio length."""
        if not os.path.exists(video_path) or not os.path.exists(audio_path):
            logging.error("[!] Input video or audio file missing for composite build.")
            return None

        if not output_name:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            output_name = f"final_montage_{timestamp_str}.mp4"

        output_path = os.path.join(FINAL_OUTPUT_DIR, output_name)
        audio_duration = AutomatedVideoEditor.get_audio_duration_ffmpeg(audio_path)

        logging.info(f"[*] [VideoEditor] Muxing '{os.path.basename(video_path)}' with audio track ({audio_duration:.2f}s)...")

        # FFmpeg pipeline: Stream loop video to match audio duration, encode AAC audio
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", video_path,
            "-i", audio_path,
            "-t", str(audio_duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "19",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                logging.info(f"[+] [VideoEditor] Final Montage Created: '{output_path}'")

                # Log Composite Output to Master Database
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO assets (filename, filepath, category, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (output_name, output_path, "Final Edited Montage", now_str))
                conn.commit()
                conn.close()

                return output_path
            else:
                logging.warning(f"[!] FFmpeg compositing failed: {result.stderr[:200]}")
                return None
        except Exception as e:
            logging.error(f"[!] Compositing exception: {e}")
            return None

if __name__ == "__main__":
    logging.info("[*] Testing Automated Video Editor & Montage Engine...")
    test_vid = os.path.join(BASE_DIR, "videos", "sample.mp4")
    test_aud = os.path.join(BASE_DIR, "outputs", "speech_test.mp3")
    
    if os.path.exists(test_vid) and os.path.exists(test_aud):
        AutomatedVideoEditor.composite_video_and_audio(test_vid, test_aud)
    else:
        logging.info("[+] Video Editor initialized and ready for production rendering pipeline inputs.")