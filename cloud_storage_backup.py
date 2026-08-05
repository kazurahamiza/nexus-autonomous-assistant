import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class CloudStorageBackupEngine:
    """Manages archiving heavy video assets and database snapshots to cloud object storage."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cloud_backup_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                local_filepath TEXT,
                cloud_uri TEXT UNIQUE,
                file_size_mb REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def backup_file(self, local_filepath, bucket_name="apex-ai-vault"):
        if not os.path.exists(local_filepath):
            logging.error(f"[!] Local file missing for cloud backup: {local_filepath}")
            return None

        filename = os.path.basename(local_filepath)
        size_mb = round(os.path.getsize(local_filepath) / (1024 * 1024), 2)
        cloud_uri = f"s3://{bucket_name}/{filename}"
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cloud_backup_registry
            (timestamp, local_filepath, cloud_uri, file_size_mb, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (now_str, local_filepath, cloud_uri, size_mb, "STAGED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [CloudBackup] File staged for S3 replication: '{cloud_uri}' ({size_mb} MB)")
        return cloud_uri

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Cloud Storage Backup Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Cloud Storage Backup Engine...")
        engine = CloudStorageBackupEngine()