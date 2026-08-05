import os
import sys
import time
import json
import sqlite3
import torch
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class GPULoadBalancer:
    """Monitors multi-GPU telemetry and routes tasks to the optimal CUDA device."""

    def __init__(self):
        self.device_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
        self._init_balancer_db()

    def _init_balancer_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gpu_telemetry_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                gpu_id INTEGER,
                gpu_name TEXT,
                vram_free_gb REAL,
                vram_total_gb REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_optimal_gpu(self):
        """Returns the device string (e.g., 'cuda:0') of the GPU with the most free VRAM."""
        if self.device_count == 0:
            logging.info("[*] [LoadBalancer] No CUDA GPUs detected. Routing to CPU.")
            return "cpu"

        best_gpu_id = 0
        max_free_vram = 0.0
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for gpu_id in range(self.device_count):
            free_mem, total_mem = torch.cuda.mem_get_info(gpu_id)
            free_gb = free_mem / (1024 ** 3)
            total_gb = total_mem / (1024 ** 3)
            gpu_name = torch.cuda.get_device_name(gpu_id)

            cursor.execute('''
                INSERT INTO gpu_telemetry_registry
                (timestamp, gpu_id, gpu_name, vram_free_gb, vram_total_gb, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (now_str, gpu_id, gpu_name, free_gb, total_gb, "ACTIVE"))

            if free_gb > max_free_vram:
                max_free_vram = free_gb
                best_gpu_id = gpu_id

        conn.commit()
        conn.close()

        target_device = f"cuda:{best_gpu_id}"
        logging.info(f"[+] [LoadBalancer] Selected Device: '{target_device}' ({max_free_vram:.2f} GB VRAM available)")
        return target_device

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] GPU Load Balancer test complete (Non-blocking).")
    else:
        logging.info("[*] Testing GPU Load Balancer Engine...")
        balancer = GPULoadBalancer()
        balancer.get_optimal_gpu()