import os
import sys
import time
import shutil
import sqlite3
import logging
import threading

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
BACKUP_DIR = os.path.join(BASE_DIR, "database_backups")

os.makedirs(BACKUP_DIR, exist_ok=True)

class DatabaseHAReplicator:
    """Manages online hot-backups, journal integrity checks, and emergency failover recovery for SQLite databases."""

    def __init__(self, sync_interval_sec=60):
        self.sync_interval_sec = sync_interval_sec
        self.is_running = False

    @staticmethod
    def verify_database_integrity():
        """Executes PRAGMA integrity_check on master database."""
        if not os.path.exists(DB_PATH):
            logging.warning("[!] Master database file does not exist yet.")
            return False

        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == "ok":
                return True
            else:
                logging.error(f"[!] Database integrity check failed: {result}")
                return False
        except Exception as e:
            logging.error(f"[!] Integrity check exception: {e}")
            return False

    @staticmethod
    def create_hot_backup():
        """Uses SQLite backup API to safely stream a hot shadow copy without lock contention."""
        if not DatabaseHAReplicator.verify_database_integrity():
            logging.error("[!] Skipping backup due to failed integrity check.")
            return False

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"master_registry_backup_{timestamp_str}.db")

        try:
            src_conn = sqlite3.connect(DB_PATH, timeout=10)
            dst_conn = sqlite3.connect(backup_file)

            with dst_conn:
                src_conn.backup(dst_conn)

            dst_conn.close()
            src_conn.close()

            logging.info(f"[+] [HAReplicator] Hot-backup created: '{os.path.basename(backup_file)}'")
            
            # Prune old backups, keeping latest 10
            backups = sorted([os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".db")])
            if len(backups) > 10:
                for old_b in backups[:-10]:
                    os.remove(old_b)

            return True
        except Exception as e:
            logging.error(f"[!] Hot backup failed: {e}")
            return False

    def start_replication_loop(self):
        """Launches continuous background replication thread."""
        self.is_running = True

        def loop():
            while self.is_running:
                time.sleep(self.sync_interval_sec)
                DatabaseHAReplicator.create_hot_backup()

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        logging.info(f"[*] Database HA Replicator active (Interval: {self.sync_interval_sec}s).")

if __name__ == "__main__":
    logging.info("[*] Testing Database HA Replicator Engine...")
    replicator = DatabaseHAReplicator(sync_interval_sec=30)
    DatabaseHAReplicator.create_hot_backup()