import os
import sys
import cv2
import json
import sqlite3
import logging
import datetime
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
DATASET_EXPORT_DIR = os.path.join(BASE_DIR, "self_learning_brutal_ai", "dataset")

os.makedirs(DATASET_EXPORT_DIR, exist_ok=True)

TARGET_LEARNING_DIRS = [
    os.path.abspath("./videos"),
    os.path.abspath("./input_videos"),
    os.path.abspath("./self_learning_brutal_ai/videos")
]

SUPPORTED_EXTENSIONS = ('.mp4', '.mkv', '.avi', '.mov', '.webm')

def translate_caption(text):
    """Ensures training tags and captions are structured in clear English."""
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated if translated else text
    except Exception:
        return text

class DatasetAnnotator:
    """Extracts keyframes from videos and generates matching .txt training tag files."""

    @staticmethod
    def extract_keyframes_and_annotate(video_path, max_frames=5):
        filename = os.path.basename(video_path)
        name_no_ext = os.path.splitext(filename)[0]
        english_title = translate_caption(name_no_ext)

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logging.warning(f"[!] Cannot open video file: {video_path}")
            return 0

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return 0

        step = max(1, total_frames // max_frames)
        saved_count = 0

        for i in range(0, total_frames, step):
            if saved_count >= max_frames:
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if ret:
                frame_filename = f"{name_no_ext}_frame_{saved_count:03d}.png"
                caption_filename = f"{name_no_ext}_frame_{saved_count:03d}.txt"

                frame_path = os.path.join(DATASET_EXPORT_DIR, frame_filename)
                caption_path = os.path.join(DATASET_EXPORT_DIR, caption_filename)

                # Save Frame Image
                cv2.imwrite(frame_path, frame)

                # Write Dataset Caption File
                tag_string = f"cinematic scene, {english_title}, high quality, master rendering, frame {saved_count}"
                with open(caption_path, "w", encoding="utf-8") as f:
                    f.write(tag_string)

                saved_count += 1

        cap.release()
        logging.info(f"[+] Extracted {saved_count} annotated training frames for: '{filename}'")
        return saved_count

    @staticmethod
    def process_all_linked_directories():
        total_extracted = 0
        for target_dir in TARGET_LEARNING_DIRS:
            if not os.path.exists(target_dir):
                continue
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if file.lower().endswith(SUPPORTED_EXTENSIONS):
                        full_path = os.path.abspath(os.path.join(root, file))
                        extracted = DatasetAnnotator.extract_keyframes_and_annotate(full_path, max_frames=3)
                        total_extracted += extracted

        logging.info(f"[+] Dataset Auto-Annotation Complete: {total_extracted} new keyframe pairs staged in dataset folder.")
        return total_extracted

if __name__ == "__main__":
    logging.info("[*] Launching Dataset Auto-Annotator Test...")
    DatasetAnnotator.process_all_linked_directories()