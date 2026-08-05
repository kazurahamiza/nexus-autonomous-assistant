import os
import sys
import time
import json
import queue
import threading
import subprocess
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class WorkerTask:
    def __init__(self, task_id, task_type, payload, priority=1):
        self.task_id = task_id
        self.task_type = task_type
        self.payload = payload
        self.priority = priority
        self.status = "QUEUED"
        self.created_at = time.time()

class DistributedTaskQueue:
    """Multi-worker parallel queue manager for background render tasks."""
    
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.task_queue = queue.PriorityQueue()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.active_tasks = {}
        self.is_running = True
        self._init_queue_db()

    def _init_queue_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_queue_log (
                task_id TEXT PRIMARY KEY,
                task_type TEXT,
                status TEXT,
                priority INTEGER,
                created_at REAL,
                completed_at REAL
            )
        ''')
        conn.commit()
        conn.close()

    def add_task(self, task_id, task_type, payload, priority=1):
        task = WorkerTask(task_id, task_type, payload, priority)
        self.active_tasks[task_id] = task
        self.task_queue.put((priority, task_id, task))
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO task_queue_log (task_id, task_type, status, priority, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (task_id, task_type, "QUEUED", priority, task.created_at, 0))
        conn.commit()
        conn.close()

        logging.info(f"[+] Task '{task_id}' [{task_type}] added to queue. (Priority: {priority})")

    def _execute_task(self, task):
        logging.info(f"[*] Processing Task '{task.task_id}' [{task.task_type}]...")
        task.status = "PROCESSING"
        
        try:
            if task.task_type == "RENDER_SCENE":
                time.sleep(2)  # Process pipeline placeholder
            elif task.task_type == "ANNOTATE_DATASET":
                if os.path.exists("dataset_auto_annotator.py"):
                    subprocess.run("python dataset_auto_annotator.py", shell=True)
            elif task.task_type == "VRAM_PURGE":
                if os.path.exists("system_self_healer.py"):
                    subprocess.run("python system_self_healer.py", shell=True)
            
            task.status = "COMPLETED"
            completed_time = time.time()

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_queue_log SET status = ?, completed_at = ? WHERE task_id = ?
            ''', ("COMPLETED", completed_time, task.task_id))
            conn.commit()
            conn.close()
            logging.info(f"[+] Task '{task.task_id}' finished successfully.")

        except Exception as e:
            task.status = "FAILED"
            logging.error(f"[!] Task '{task.task_id}' failed: {e}")

    def start_worker_loop(self):
        def loop():
            while self.is_running:
                try:
                    priority, task_id, task = self.task_queue.get(timeout=3)
                    self.executor.submit(self._execute_task, task)
                    self.task_queue.task_done()
                except queue.Empty:
                    continue

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        logging.info(f"[*] Distributed Task Queue active with {self.max_workers} parallel workers.")

if __name__ == "__main__":
    queue_engine = DistributedTaskQueue(max_workers=4)
    queue_engine.start_worker_loop()
    
    # Test Enqueue
    queue_engine.add_task("task_001", "VRAM_PURGE", {}, priority=1)
    queue_engine.add_task("task_002", "ANNOTATE_DATASET", {}, priority=2)
    
    time.sleep(5)