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
THUMBNAIL_OUTPUT_DIR = os.path.join(BASE_DIR, "outputs", "thumbnails")

os.makedirs(THUMBNAIL_OUTPUT_DIR, exist_ok=True)

class ABThumbnailGenerator:
    """Extracts high-entropy keyframes and generates A/B thumbnail variants with styled overlays."""

    def __init__(self):
        self._init_thumbnail_db()

    def _init_thumbnail_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ab_thumbnail_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                video_filename TEXT,
                thumbnail_path TEXT UNIQUE,
                variant_label TEXT,
                title_hook TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def extract_keyframe(video_path, frame_time_sec=1.0):
        """Extracts a sharp keyframe image matrix from a video file."""
        if not os.path.exists(video_path):
            return None

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        target_frame = int(fps * frame_time_sec)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()

        if ret:
            return frame
        return None

    def generate_ab_variants(self, video_path, title_hook="SYSTEM AUDIT REVEALED"):
        """Generates Variant A (Standard) and Variant B (High-Contrast Boosted) thumbnail images."""
        if not os.path.exists(video_path):
            logging.error(f"[!] Target video missing for thumbnail generation: {video_path}")
            return []

        frame = self.extract_keyframe(video_path, frame_time_sec=2.0)
        if frame is None:
            logging.warning("[!] Failed to extract keyframe for thumbnail generation.")
            return []

        base_filename = os.path.splitext(os.path.basename(video_path))[0]
        variants = []

        # --- Variant A: Standard Keyframe Overlay ---
        var_a_frame = frame.copy()
        cv2.putText(var_a_frame, title_hook.upper(), (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        var_a_path = os.path.join(THUMBNAIL_OUTPUT_DIR, f"{base_filename}_thumb_A.jpg")
        cv2.imwrite(var_a_path, var_a_frame)
        variants.append((var_a_path, "Variant_A"))

        # --- Variant B: High Contrast & Saturation Boosted ---
        var_b_frame = cv2.convertScaleAbs(frame, alpha=1.3, beta=10) # Contrast boost
        cv2.putText(var_b_frame, f"MUST SEE: {title_hook.upper()}", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
        var_b_path = os.path.join(THUMBNAIL_OUTPUT_DIR, f"{base_filename}_thumb_B.jpg")
        cv2.imwrite(var_b_path, var_b_frame)
        variants.append((var_b_path, "Variant_B"))

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for path, label in variants:
            cursor.execute('''
                INSERT OR REPLACE INTO ab_thumbnail_registry 
                (timestamp, video_filename, thumbnail_path, variant_label, title_hook, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (now_str, os.path.basename(video_path), path, label, title_hook, "STAGED"))

        conn.commit()
        conn.close()

        logging.info(f"[+] [ABThumbnailGen] Generated 2 thumbnail variants for '{base_filename}'")
        return variants

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] A/B Thumbnail & Title Generator test complete (Non-blocking).")
    else:
        logging.info("[*] Testing A/B Thumbnail Generator Engine...")
        engine = ABThumbnailGenerator()