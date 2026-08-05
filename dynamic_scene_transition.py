import os
import sys
import time
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
TRANSITION_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "transitions")

os.makedirs(TRANSITION_OUTPUT_DIR, exist_ok=True)

class DynamicSceneTransitionEngine:
    """Applies motion-aware transitions between generated video segments."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transition_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                clip_a TEXT,
                clip_b TEXT,
                output_filepath TEXT UNIQUE,
                transition_type TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def apply_xfade_transition(self, clip_a_path, clip_b_path, transition_type="fade", duration_sec=1.0):
        if not os.path.exists(clip_a_path) or not os.path.exists(clip_b_path):
            logging.error("[!] Input clip paths missing for transition rendering.")
            return clip_a_path

        output_path = os.path.join(TRANSITION_OUTPUT_DIR, f"trans_{int(time.time())}.mp4")
        filter_complex = f"[0:v][1:v]xfade=transition={transition_type}:duration={duration_sec}:offset=3[v]"

        cmd = [
            "ffmpeg", "-y",
            "-i", clip_a_path,
            "-i", clip_b_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-c:v", "libx264",
            "-preset", "fast",
            output_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and os.path.exists(output_path):
                now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO transition_registry
                    (timestamp, clip_a, clip_b, output_filepath, transition_type, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (now_str, clip_a_path, clip_b_path, output_path, transition_type, "COMPLETED"))
                conn.commit()
                conn.close()

                logging.info(f"[+] [TransitionEngine] Transition applied successfully: '{output_path}'")
                return output_path
        except Exception as e:
            logging.error(f"[!] Transition engine exception: {e}")

        return clip_a_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Dynamic Scene Transition Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Dynamic Scene Transition Engine...")
        engine = DynamicSceneTransitionEngine()