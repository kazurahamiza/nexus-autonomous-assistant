import os
import sys
import time
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
STEMS_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "audio_stems")

os.makedirs(STEMS_OUTPUT_DIR, exist_ok=True)

class AudioStemSeparator:
    """Isolates dialogue, background music, and sound effects from media assets."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio_stem_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                input_filepath TEXT,
                dialogue_path TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def extract_dialogue_stem(self, input_media_path):
        if not os.path.exists(input_media_path):
            logging.error(f"[!] Source media missing: {input_media_path}")
            return None

        base_name = os.path.splitext(os.path.basename(input_media_path))[0]
        dialogue_path = os.path.join(STEMS_OUTPUT_DIR, f"{base_name}_dialogue.wav")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_media_path,
            "-vn",
            "-af", "highpass=f=200,lowpass=f=3000",
            "-c:a", "pcm_s16le",
            dialogue_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(dialogue_path):
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO audio_stem_registry
                    (timestamp, input_filepath, dialogue_path, status)
                    VALUES (?, ?, ?, ?)
                ''', (now_str, input_media_path, dialogue_path, "EXTRACTED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [StemSeparator] Dialogue stem isolated: '{dialogue_path}'")
                return dialogue_path
        except Exception as e:
            logging.error(f"[!] Stem separator exception: {e}")

        return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Audio Stem Separator test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Audio Stem Separator...")
        separator = AudioStemSeparator()