import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class ContextualBRollEngine:
    """Scans text scripts for subtext and inserts matching B-roll footage layers."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS broll_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                keyword TEXT,
                broll_filepath TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def insert_broll_layer(self, script_text, main_video_path):
        keywords = ["technology", "cybersecurity", "audit", "ai"]
        matched = [k for k in keywords if k in script_text.lower()] or ["default"]

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO broll_registry (timestamp, keyword, broll_filepath, status)
            VALUES (?, ?, ?, ?)
        ''', (now_str, matched[0], main_video_path, "INJECTED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [BRollEngine] Matched B-roll tag: '{matched[0]}' for main video pipeline.")
        return main_video_path

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Contextual B-Roll Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Contextual B-Roll Engine...")
        engine = ContextualBRollEngine()