import os
import sys
import time
import json
import sqlite3
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
DATASET_DIR = os.path.join(BASE_DIR, "self_learning_brutal_ai", "dataset")
LORA_OUTPUT_DIR = os.path.join(BASE_DIR, "ComfyUI", "models", "loras")

os.makedirs(LORA_OUTPUT_DIR, exist_ok=True)

class LoRAAutoTrainer:
    """Monitors dataset expansion and triggers automated LoRA fine-tuning tasks."""

    def __init__(self, min_samples_threshold=20):
        self.min_samples_threshold = min_samples_threshold

    def inspect_dataset_readiness(self):
        """Counts annotated frame and caption pairs in dataset folder."""
        if not os.path.exists(DATASET_DIR):
            return 0

        png_files = [f for f in os.listdir(DATASET_DIR) if f.endswith(".png")]
        txt_files = [f for f in os.listdir(DATASET_DIR) if f.endswith(".txt")]
        
        valid_pairs = min(len(png_files), len(txt_files))
        logging.info(f"[*] [LoRATrainer] Dataset Inspection: {valid_pairs} valid image/caption pairs found.")
        return valid_pairs

    def trigger_training_run(self, lora_name=None):
        """Executes background fine-tuning pipeline when dataset threshold is met."""
        samples = self.inspect_dataset_readiness()
        if samples < self.min_samples_threshold:
            logging.info(f"[*] Dataset samples ({samples}) below threshold ({self.min_samples_threshold}). Training deferred.")
            return False

        if not lora_name:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            lora_name = f"auto_style_lora_{timestamp_str}.safetensors"

        output_path = os.path.join(LORA_OUTPUT_DIR, lora_name)
        logging.info(f"[*] [LoRATrainer] Launching fine-tuning run -> Output Target: '{lora_name}'...")

        # Mock/Integration training command hook
        time.sleep(2)  # Simulates training initialization phase

        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lora_training_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                lora_filename TEXT,
                sample_count INTEGER,
                status TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO lora_training_history (timestamp, lora_filename, sample_count, status)
            VALUES (?, ?, ?, ?)
        ''', (now_str, lora_name, samples, "STAGED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [LoRATrainer] Fine-tuning job registered successfully for '{lora_name}'.")
        return True

if __name__ == "__main__":
    logging.info("[*] Testing Automated LoRA Training Scheduler...")
    trainer = LoRAAutoTrainer(min_samples_threshold=1)
    trainer.trigger_training_run()