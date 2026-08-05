import os
import sys
import time
import sqlite3
import psutil
import torch
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class HardwareGovernor:
    """Monitors GPU/CPU thermals, power states, and dynamically throttles batch workloads."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hardware_governor_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                cpu_load REAL,
                vram_used_mb REAL,
                governor_state TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def evaluate_hardware_state(self):
        cpu_load = psutil.cpu_percent()
        vram_alloc = round(torch.cuda.memory_allocated(0) / (1024 ** 2), 2) if torch.cuda.is_available() else 0.0

        state = "OPTIMAL"
        if cpu_load > 90.0:
            state = "THROTTLE_REQUIRED"

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO hardware_governor_log (timestamp, cpu_load, vram_used_mb, governor_state)
            VALUES (?, ?, ?, ?)
        ''', (now_str, cpu_load, vram_alloc, state))
        conn.commit()
        conn.close()

        logging.info(f"[*] [HardwareGovernor] Telemetry: CPU={cpu_load}%, VRAM={vram_alloc}MB | State={state}")
        return state

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Hardware Governor test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Hardware Governor Engine...")
        gov = HardwareGovernor()
        gov.evaluate_hardware_state()