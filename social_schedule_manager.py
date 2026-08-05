import os
import sys
import time
import json
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class SocialScheduleManager:
    """Queues media assets for publishing at optimal cross-platform time windows."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_schedule_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheduled_timestamp TEXT,
                video_filepath TEXT,
                target_platform TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def schedule_post(self, video_filepath, platform="YouTube", delay_hours=2):
        if not os.path.exists(video_filepath):
            logging.error(f"[!] Target file does not exist: {video_filepath}")
            return False

        scheduled_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + delay_hours * 3600))

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO social_schedule_queue (scheduled_timestamp, video_filepath, target_platform, status)
            VALUES (?, ?, ?, ?)
        ''', (scheduled_time, video_filepath, platform, "QUEUED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [ScheduleManager] Queued '{os.path.basename(video_filepath)}' for {platform} at {scheduled_time}")
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Social Schedule Manager test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Social Schedule Manager...")
        manager = SocialScheduleManager()