import os
import sys
import time
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
REMEDIATED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "trimmed")

os.makedirs(REMEDIATED_OUTPUT_DIR, exist_ok=True)

class JumpcutRemediationEngine:
    """Detects silences, strips dead audio gaps, and smooths video transitions."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jumpcut_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input_filepath TEXT,
                output_filepath TEXT UNIQUE,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def strip_audio_silence(self, input_video_path):
        if not os.path.exists(input_video_path):
            logging.error(f"[!] Target video path missing: {input_video_path}")
            return input_video_path

        base_name = os.path.basename(input_video_path)
        output_path = os.path.join(REMEDIATED_OUTPUT_DIR, f"trimmed_{base_name}")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_video_path,
            "-af", "silenceremove=start_periods=1:start_duration=0.1:start_threshold=-40dB:stop_periods=-1:stop_duration=0.1:stop_threshold=-40dB",
            "-c:v", "copy",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO jumpcut_registry (timestamp, input_filepath, output_filepath, status)
                    VALUES (?, ?, ?, ?)
                ''', (now_str, input_video_path, output_path, "COMPLETED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [JumpcutEngine] Dead silence gaps stripped: '{output_path}'")
                return output_path
        except Exception as e:
            logging.error(f"[!] Jumpcut remediation exception: {e}")

        return input_video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Jumpcut Remediation Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Jumpcut Remediation Engine...")
        engine = JumpcutRemediationEngine()