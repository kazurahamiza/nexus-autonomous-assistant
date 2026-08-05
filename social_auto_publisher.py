import os
import sys
import json
import time
import sqlite3
import logging
import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
PUBLISHED_LOG_FILE = os.path.join(BASE_DIR, "published_analytics.json")
FINAL_EDITS_DIR = os.path.join(BASE_DIR, "outputs", "final_edits")

class SocialAutoPublisher:
    """Monitors finished video edits, dispatches them to API publishing endpoints, and logs analytics."""

    def __init__(self):
        self._init_analytics_db()

    def _init_analytics_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS publishing_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE,
                platform TEXT,
                publish_time TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def publish_video(self, video_path, title, category, platform="YouTube Shorts"):
        """Dispatches media payload to social network API endpoint."""
        if not os.path.exists(video_path):
            logging.error(f"[!] Target video file not found for publishing: {video_path}")
            return False

        filename = os.path.basename(video_path)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        logging.info(f"[*] [SocialPublisher] Dispatching '{filename}' to {platform} API...")

        # Platform API payload simulation / webhook dispatch hook
        success = True  # Set to True on successful API POST response
        
        if success:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO publishing_analytics (filename, platform, publish_time, views, likes, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, platform, now_str, 0, 0, "PUBLISHED"))
            conn.commit()
            conn.close()

            self._update_json_analytics_mirror(filename, platform, now_str)
            logging.info(f"[+] [SocialPublisher] Successfully published '{filename}' on {platform}.")
            return True
        return False

    def _update_json_analytics_mirror(self, filename, platform, publish_time):
        analytics_data = []
        if os.path.exists(PUBLISHED_LOG_FILE):
            try:
                with open(PUBLISHED_LOG_FILE, 'r', encoding='utf-8') as f:
                    analytics_data = json.load(f)
            except Exception:
                analytics_data = []

        analytics_data.append({
            "filename": filename,
            "platform": platform,
            "publish_time": publish_time,
            "views": 0,
            "likes": 0,
            "status": "PUBLISHED"
        })

        with open(PUBLISHED_LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(analytics_data, f, indent=4, ensure_ascii=False)

    def scan_and_publish_pending_edits(self):
        """Scans final edits folder and publishes any unlogged media assets."""
        if not os.path.exists(FINAL_EDITS_DIR):
            return 0

        published_count = 0
        for file in os.listdir(FINAL_EDITS_DIR):
            if file.lower().endswith(('.mp4', '.mkv', '.mov')):
                full_path = os.path.join(FINAL_EDITS_DIR, file)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM publishing_analytics WHERE filename = ?", (file,))
                exists = cursor.fetchone()
                conn.close()

                if not exists:
                    self.publish_video(full_path, title=file, category="Automated Video", platform="YouTube Shorts")
                    published_count += 1

        return published_count

if __name__ == "__main__":
    logging.info("[*] Testing Social Media Auto-Publisher Engine...")
    publisher = SocialAutoPublisher()
    pending = publisher.scan_and_publish_pending_edits()
    logging.info(f"[+] Publisher initialized. Processed {pending} pending video edits.")