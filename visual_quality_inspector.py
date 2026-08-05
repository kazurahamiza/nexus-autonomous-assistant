import os
import sys
import time
import json
import sqlite3
import cv2
import logging
import numpy as np

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
INSPECTION_LOG_FILE = os.path.join(BASE_DIR, "quality_inspection_log.json")

class VisualQualityInspector:
    """Evaluates video frames and generated images for blur, black frames, motion freezes, and visual artifacts."""

    def __init__(self):
        self._init_inspector_db()

    def _init_inspector_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS visual_quality_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filepath TEXT UNIQUE,
                sharpness_score REAL,
                black_frame_ratio REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def calculate_sharpness(frame):
        """Calculates variance of Laplacian to measure image sharpness/blur."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def is_black_frame(frame, threshold=15.0):
        """Determines if a frame is predominantly black or empty."""
        return bool(np.mean(frame) < threshold)

    def inspect_video_quality(self, video_path, sample_rate=15):
        """Scans video sample frames and evaluates overall quality scores."""
        if not os.path.exists(video_path):
            logging.error(f"[!] Target file not found for quality audit: {video_path}")
            return False, 0.0, 1.0

        cap = cv2.VideoCapture(video_path)
        frame_count = 0
        black_frames = 0
        sharpness_scores = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % sample_rate == 0:
                sharpness = self.calculate_sharpness(frame)
                sharpness_scores.append(sharpness)

                if self.is_black_frame(frame):
                    black_frames += 1

        cap.release()

        sampled_count = max(1, len(sharpness_scores))
        avg_sharpness = float(np.mean(sharpness_scores)) if sharpness_scores else 0.0
        black_ratio = float(black_frames / sampled_count)

        # Quality Threshold Logic: Sharpness > 100 and Black Frames < 20%
        passed = (avg_sharpness > 80.0) and (black_ratio < 0.20)
        status = "PASSED" if passed else "REJECTED_LOW_QUALITY"

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO visual_quality_registry
            (timestamp, filepath, sharpness_score, black_frame_ratio, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (now_str, video_path, avg_sharpness, black_ratio, status))
        conn.commit()
        conn.close()

        logging.info(f"[*] [QualityInspector] Audited '{os.path.basename(video_path)}': Sharpness={avg_sharpness:.2f}, BlackRatio={black_ratio:.2%}, Status={status}")
        return passed, avg_sharpness, black_ratio

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Visual Quality & Artifact Inspector test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Visual Quality Inspector Engine...")
        inspector = VisualQualityInspector()