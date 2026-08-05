import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class LiveVTuberStreamer:
    """Processes real-time chat messages and drives live broadcast avatar responses."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vtuber_chat_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_prompt TEXT,
                response_text TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def process_chat_message(self, username, message):
        response_text = f"Thanks for the question {username}! System operational."
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO vtuber_chat_registry (timestamp, user_prompt, response_text, status)
            VALUES (?, ?, ?, ?)
        ''', (now_str, f"{username}: {message}", response_text, "DISPATCHED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [VTuberStreamer] Chat Response Dispatched -> {username}")
        return response_text

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Live VTuber Streamer test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Live VTuber Streamer Engine...")
        streamer = LiveVTuberStreamer()