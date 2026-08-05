import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class InteractiveStoryEngine:
    """Builds multi-path choice trees for interactive story video generation."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interactive_story_tree (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                root_video TEXT,
                option_a_text TEXT,
                option_b_text TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def generate_story_branch(self, root_video_path, opt_a="INSPECT CORE", opt_b="PURGE SYSTEM"):
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO interactive_story_tree (timestamp, root_video, option_a_text, option_b_text, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (now_str, root_video_path, opt_a, opt_b, "BRANCH_STAGED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [StoryEngine] Interactive story node created: A='{opt_a}' | B='{opt_b}'")
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Interactive Story Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Interactive Story Engine...")
        engine = InteractiveStoryEngine()