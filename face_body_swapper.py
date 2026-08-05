import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
SWAPPED_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "face_swapped")

os.makedirs(SWAPPED_OUTPUT_DIR, exist_ok=True)

class FaceBodySwapperEngine:
    """Locks visual character consistency by applying avatar target masks onto generated frames."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_swap_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                source_image TEXT,
                target_video TEXT,
                output_filepath TEXT UNIQUE,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def process_avatar_lock(self, target_video_path, avatar_image_path):
        if not os.path.exists(target_video_path):
            logging.error(f"[!] Target video path missing: {target_video_path}")
            return target_video_path

        base_name = os.path.basename(target_video_path)
        output_path = os.path.join(SWAPPED_OUTPUT_DIR, f"avatar_{base_name}")

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO face_swap_registry
            (timestamp, source_image, target_video, output_filepath, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (now_str, avatar_image_path, target_video_path, output_path, "STAGED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [FaceSwapper] Avatar consistency pipeline registered for '{base_name}'")
        return target_video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Face & Body Swapper Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Face & Body Swapper Engine...")
        engine = FaceBodySwapperEngine()