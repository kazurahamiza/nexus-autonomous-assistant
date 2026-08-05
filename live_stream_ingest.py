import os
import sys
import cv2
import time
import json
import sqlite3
import logging
import threading

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
CAPTURED_FRAMES_DIR = os.path.join(BASE_DIR, "input_videos", "live_captures")

os.makedirs(CAPTURED_FRAMES_DIR, exist_ok=True)

class LiveStreamIngestEngine:
    """Real-time RTSP/Webcam stream ingestion and frame capture module."""

    def __init__(self, stream_source=0, capture_interval_sec=5):
        self.stream_source = stream_source
        self.capture_interval_sec = capture_interval_sec
        self.is_running = False
        self.cap = None

    def start_ingest(self):
        """Starts background frame ingestion loop."""
        self.cap = cv2.VideoCapture(self.stream_source)
        if not self.cap.isOpened():
            logging.error(f"[!] Unable to open live stream source: {self.stream_source}")
            return False

        self.is_running = True
        logging.info(f"[+] Live Stream Engine active on source: {self.stream_source}")

        def ingest_loop():
            last_capture = time.time()
            frame_count = 0

            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    logging.warning("[!] Stream signal lost. Retrying frame capture...")
                    time.sleep(1)
                    continue

                current_time = time.time()
                if current_time - last_capture >= self.capture_interval_sec:
                    last_capture = current_time
                    frame_count += 1
                    
                    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
                    frame_filename = f"live_stream_frame_{timestamp_str}_{frame_count:04d}.png"
                    frame_path = os.path.join(CAPTURED_FRAMES_DIR, frame_filename)

                    # Save Frame Image
                    cv2.imwrite(frame_path, frame)
                    logging.info(f"[+] Captured Live Snapshot: {frame_filename}")

                    # Log Snapshot to Database
                    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO assets (filename, filepath, category, timestamp)
                        VALUES (?, ?, ?, ?)
                    ''', (frame_filename, frame_path, "Live Stream Capture", now_str))
                    conn.commit()
                    conn.close()

        t = threading.Thread(target=ingest_loop, daemon=True)
        t.start()
        return True

    def stop_ingest(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
        logging.info("[*] Live Stream Engine stopped.")

if __name__ == "__main__":
    logging.info("[*] Launching Live Stream & NDI Ingestion Engine Test...")
    engine = LiveStreamIngestEngine(stream_source=0, capture_interval_sec=3)
    # Test initialization check
    logging.info("[+] Engine ready for camera index or RTSP URL stream input.")