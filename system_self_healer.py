import os
import sys
import time
import gc
import sqlite3
import logging
import subprocess
import psutil
import torch

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
LOG_FILE = os.path.join(BASE_DIR, "autostart_system.log")

class SystemSelfHealer:
    """Monitors system runtime, resolves VRAM fragmentation, and unlocks databases."""
    
    @staticmethod
    def fix_database_locks():
        """Clears SQLite WAL journal locks and forces database checkpointing."""
        if not os.path.exists(DB_PATH):
            return
        logging.info("[*] [SelfHealer] Inspecting database for stale lock files...")
        try:
            conn = sqlite3.connect(DB_PATH, timeout=5)
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE);")
            conn.commit()
            conn.close()
            logging.info("[+] [SelfHealer] Database lock inspection and WAL cleanup complete.")
        except Exception as e:
            logging.warning(f"[!] [SelfHealer] Database recovery exception: {e}")

    @staticmethod
    def purge_vram_and_cache():
        """Forces deep PyTorch VRAM release, garbage collection, and IPC purging."""
        logging.info("[*] [SelfHealer] Initiating deep VRAM defragmentation...")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            vram_free = torch.cuda.mem_get_info()[0] / (1024 ** 3)
            logging.info(f"[+] [SelfHealer] VRAM purged. Free VRAM available: {vram_free:.2f} GB")

    @staticmethod
    def inspect_logs_and_heal():
        """Scans log file for critical runtime errors and executes matching hot-fixes."""
        if not os.path.exists(LOG_FILE):
            return

        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()[-50:]  # Read last 50 log lines
                
            log_text = "".join(lines).lower()

            if "out of memory" in log_text or "cuda error" in log_text:
                logging.warning("[!] [SelfHealer] Detected CUDA Out-of-Memory event in logs! Triggering emergency purge...")
                SystemSelfHealer.purge_vram_and_cache()

            if "database is locked" in log_text:
                logging.warning("[!] [SelfHealer] Detected SQLite Lock event in logs! Triggering DB lock recovery...")
                SystemSelfHealer.fix_database_locks()

        except Exception as e:
            logging.error(f"[!] [SelfHealer] Log inspection error: {e}")

if __name__ == "__main__":
    logging.info("[*] Launching System Self-Healer Daemon Test...")
    SystemSelfHealer.fix_database_locks()
    SystemSelfHealer.purge_vram_and_cache()
    SystemSelfHealer.inspect_logs_and_heal()
    logging.info("[+] System Self-Healer operational.")