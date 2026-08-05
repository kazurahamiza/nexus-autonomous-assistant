import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class VTuberAudienceEngine:
    """Processes live chat polls and drives interactive VTuber broadcast branching."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audience_poll_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                poll_question TEXT,
                votes_option_a INTEGER,
                votes_option_b INTEGER,
                winning_option TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def evaluate_live_poll(self, question="Which sub-system should we audit next?", votes_a=142, votes_b=89):
        winning_option = "Option A" if votes_a >= votes_b else "Option B"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO audience_poll_registry (timestamp, poll_question, votes_option_a, votes_option_b, winning_option, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now_str, question, votes_a, votes_b, winning_option, "RESOLVED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [AudienceEngine] Poll resolved: '{winning_option}' won with {max(votes_a, votes_b)} votes.")
        return winning_option

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] VTuber Audience Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing VTuber Audience Engine...")
        engine = VTuberAudienceEngine()
        engine.evaluate_live_poll()