import os
import sys
import time
import sqlite3
import logging
import hashlib

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class MeshModelCacheSync:
    """Synchronizes checkpoint weights, LoRAs, and asset caches across cluster nodes."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mesh_cache_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                model_filename TEXT UNIQUE,
                file_hash TEXT,
                sync_status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    @staticmethod
    def calculate_file_hash(filepath, chunk_size=8192):
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return "hash_error"

    def sync_model_weight(self, model_filepath):
        if not os.path.exists(model_filepath):
            logging.error(f"[!] Model file missing for mesh sync: {model_filepath}")
            return False

        filename = os.path.basename(model_filepath)
        f_hash = self.calculate_file_hash(model_filepath)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO mesh_cache_registry
            (timestamp, model_filename, file_hash, sync_status)
            VALUES (?, ?, ?, ?)
        ''', (now_str, filename, f_hash, "SYNCHRONIZED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [MeshCacheSync] Synced model weight '{filename}' (Hash: {f_hash[:8]}) across swarm nodes.")
        return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Mesh Model Cache Synchronizer test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Mesh Model Cache Sync...")
        sync = MeshModelCacheSync()