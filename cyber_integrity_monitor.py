import os
import sys
import time
import json
import hashlib
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
INTEGRITY_MANIFEST = os.path.join(BASE_DIR, "system_integrity_manifest.json")

CORE_SCRIPTS = [
    "app.py",
    "build_and_push.py",
    "engine_coordinator.py",
    "master_system_orchestrator.py",
    "system_self_healer.py",
    "multi_agent_pipeline.py",
    "model_and_workflow_manager.py",
    "dataset_auto_annotator.py",
    "distributed_task_queue.py",
    "motion_upscale_pipeline.py",
    "live_stream_ingest.py",
    "semantic_vector_search.py",
    "automated_video_editor.py",
    "social_auto_publisher.py",
    "ai_self_learning_loop.py",
    "mission_control_dashboard.py",
    "distributed_cluster_node.py"
]

class SystemIntegrityMonitor:
    """Calculates SHA-256 hashes for core scripts and detects file tampering or unauthorized modifications."""

    def __init__(self):
        self._init_integrity_db()

    def _init_integrity_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_integrity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                filename TEXT,
                sha256_hash TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def calculate_file_hash(filepath):
        """Generates SHA-256 hash string for a file."""
        if not os.path.exists(filepath):
            return None
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logging.error(f"[!] Error hashing file {filepath}: {e}")
            return None

    def scan_and_verify_integrity(self):
        """Scans all registered Python core files and flags modified or corrupted scripts."""
        manifest = {}
        if os.path.exists(INTEGRITY_MANIFEST):
            try:
                with open(INTEGRITY_MANIFEST, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
            except Exception:
                manifest = {}

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        updated_manifest = {}
        anomalies_detected = 0

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for script in CORE_SCRIPTS:
            full_path = os.path.join(BASE_DIR, script)
            if not os.path.exists(full_path):
                continue

            current_hash = self.calculate_file_hash(full_path)
            previous_hash = manifest.get(script)

            status = "VERIFIED"
            if previous_hash and previous_hash != current_hash:
                status = "MODIFIED_DETECTED"
                logging.warning(f"[!] INTEGRITY ALERT: File '{script}' has been modified since last audit!")
                anomalies_detected += 1

            updated_manifest[script] = current_hash

            cursor.execute('''
                INSERT INTO system_integrity_log (timestamp, filename, sha256_hash, status)
                VALUES (?, ?, ?, ?)
            ''', (now_str, script, current_hash, status))

        conn.commit()
        conn.close()

        with open(INTEGRITY_MANIFEST, "w", encoding="utf-8") as f:
            json.dump(updated_manifest, f, indent=4)

        logging.info(f"[+] [IntegrityMonitor] Audit complete. Files Scanned: {len(updated_manifest)} | Anomalies: {anomalies_detected}")
        return anomalies_detected

if __name__ == "__main__":
    logging.info("[*] Launching System Integrity & Security Audit Engine...")
    monitor = SystemIntegrityMonitor()
    monitor.scan_and_verify_integrity()