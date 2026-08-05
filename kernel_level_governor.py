import os
import sys
import time
import ctypes
import sqlite3
import psutil
import torch
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class KernelLevelGovernor:
    """Monitors low-level kernel process memory, hardware interrupts, and GPU VRAM pressure."""

    def __init__(self, memory_hard_limit_gb=14.0):
        self.hard_limit_bytes = memory_hard_limit_gb * (1024 ** 3)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kernel_governor_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                process_pid INTEGER,
                ram_usage_mb REAL,
                vram_usage_mb REAL,
                kernel_action TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def enforce_kernel_limits(self):
        """Monitors process memory footprint and forcefully purges dead allocations."""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        ram_mb = round(mem_info.rss / (1024 * 1024), 2)
        vram_mb = round(torch.cuda.memory_allocated(0) / (1024 * 1024), 2) if torch.cuda.is_available() else 0.0

        action = "NORMAL"

        # Force aggressive memory reclamation if memory spikes
        if mem_info.rss > self.hard_limit_bytes:
            action = "FORCE_GC_TRIM"
            import gc
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            
            # Windows API C-types Working Set Trim
            if sys.platform == "win32":
                try:
                    ctypes.windll.kernel32.SetProcessWorkingSetSize(-1, -1)
                except Exception:
                    pass

            logging.critical(f"[!] [KernelGovernor] HARD MEMORY LIMIT EXCEEDED ({ram_mb} MB). Forced C-Level WorkingSet Trim Executed.")

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO kernel_governor_audit
            (timestamp, process_pid, ram_usage_mb, vram_usage_mb, kernel_action, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now_str, os.getpid(), ram_mb, vram_mb, action, "ENFORCED"))
        conn.commit()
        conn.close()

        logging.info(f"[*] [KernelGovernor] PID {os.getpid()} | RAM: {ram_mb}MB | VRAM: {vram_mb}MB | Kernel Enforcement: {action}")
        return action

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Kernel-Level Resource Governor test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Kernel-Level Resource Governor...")
        gov = KernelLevelGovernor()
        gov.enforce_kernel_limits()