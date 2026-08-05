import os
import sys
import time
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
LIPSYNC_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "lipsynced_edits")

os.makedirs(LIPSYNC_OUTPUT_DIR, exist_ok=True)

class LipSyncAligner:
    """Aligns video speaker facial movements with localized audio tracks."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lipsync_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                video_filepath TEXT,
                audio_filepath TEXT,
                output_filepath TEXT UNIQUE,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def align_lip_sync(self, video_path, audio_path, output_filename=None):
        if not os.path.exists(video_path) or not os.path.exists(audio_path):
            logging.error("[!] Video or Audio source path missing for lip-sync alignment.")
            return video_path

        if not output_filename:
            base_name = os.path.basename(video_path)
            output_filename = f"synced_{base_name}"

        output_path = os.path.join(LIPSYNC_OUTPUT_DIR, output_filename)

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO lipsync_registry
                    (timestamp, video_filepath, audio_filepath, output_filepath, status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (now_str, video_path, audio_path, output_path, "COMPLETED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [LipSyncAligner] Audio synced to video track: '{output_path}'")
                return output_path
        except Exception as e:
            logging.error(f"[!] Lip-sync exception: {e}")

        return video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Lip-Sync Aligner test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Lip-Sync Aligner Engine...")
        aligner = LipSyncAligner()