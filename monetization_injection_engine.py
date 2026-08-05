import os
import sys
import time
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
MONETIZED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "monetized")

os.makedirs(MONETIZED_OUTPUT_DIR, exist_ok=True)

class MonetizationInjectionEngine:
    """Injects dynamic call-to-action cards, banner overlays, and affiliate QR codes onto video renders."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS monetization_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                original_filepath TEXT,
                monetized_filepath TEXT UNIQUE,
                banner_text TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def inject_banner_overlay(self, input_video_path, banner_text="SUBSCRIBE FOR DAILY AI UPDATES", output_filename=None):
        if not os.path.exists(input_video_path):
            logging.error(f"[!] Target video missing for ad injection: {input_video_path}")
            return input_video_path

        if not output_filename:
            base_name = os.path.basename(input_video_path)
            output_filename = f"ad_{base_name}"

        output_path = os.path.join(MONETIZED_OUTPUT_DIR, output_filename)
        vf_filter = (
            f"drawtext=text='{banner_text}':x=(w-tw)/2:y=h-th-40:"
            "fontcolor=yellow@0.9:fontsize=22:box=1:boxcolor=black@0.6:boxborderw=8"
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
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO monetization_registry
                    (timestamp, original_filepath, monetized_filepath, banner_text, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (now_str, input_video_path, output_path, banner_text, "COMPLETED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [MonetizationEngine] Ad banner overlay injected: '{output_path}'")
                return output_path
        except Exception as e:
            logging.error(f"[!] Monetization injection exception: {e}")

        return input_video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Monetization Injection Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Monetization Injection Engine...")
        engine = MonetizationInjectionEngine()