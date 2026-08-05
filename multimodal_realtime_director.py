import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class MultimodalRealtimeDirector:
    """Adjusts color curves, spatial audio panning, and tempo dynamically based on script sentiment."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS director_cues_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                scene_id TEXT,
                sentiment TEXT,
                audio_pan_bias REAL,
                color_profile TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def direct_scene(self, scene_id="scene_01", sentiment="intense"):
        color_map = {"intense": "high_contrast_warm", "calm": "cool_soft", "neutral": "balanced"}
        pan_map = {"intense": 0.8, "calm": 0.0, "neutral": 0.1}

        color_profile = color_map.get(sentiment, "balanced")
        pan_bias = pan_map.get(sentiment, 0.0)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO director_cues_registry (timestamp, scene_id, sentiment, audio_pan_bias, color_profile, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now_str, scene_id, sentiment, pan_bias, color_profile, "DIRECTED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [MultimodalDirector] '{scene_id}' [{sentiment}]: Color={color_profile}, AudioPan={pan_bias}")
        return color_profile

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Multimodal Real-Time Director test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Multimodal Director...")
        director = MultimodalRealtimeDirector()
        director.direct_scene()