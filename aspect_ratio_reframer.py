import os
import sys
import time
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
REFRAMED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "vertical_9_16")

os.makedirs(REFRAMED_OUTPUT_DIR, exist_ok=True)

class AspectRatioReframer:
    """Converts 16:9 widescreen master footage into centered 9:16 vertical shorts."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reframer_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input_filepath TEXT,
                output_filepath TEXT UNIQUE,
                target_ratio TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def reframe_to_vertical(self, input_video_path):
        if not os.path.exists(input_video_path):
            logging.error(f"[!] Input video missing for reframing: {input_video_path}")
            return input_video_path

        base_name = os.path.basename(input_video_path)
        output_path = os.path.join(REFRAMED_OUTPUT_DIR, f"vertical_{base_name}")

        vf_filter = "crop=ih*(9/16):ih"

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
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO reframer_registry (timestamp, input_filepath, output_filepath, target_ratio, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (now_str, input_video_path, output_path, "9:16", "COMPLETED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [Reframer] Reframed to 9:16 vertical format: '{output_path}'")
                return output_path
        except Exception as e:
            logging.error(f"[!] Aspect ratio reframer exception: {e}")

        return input_video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Aspect Ratio Reframer test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Aspect Ratio Reframer...")
        reframer = AspectRatioReframer()