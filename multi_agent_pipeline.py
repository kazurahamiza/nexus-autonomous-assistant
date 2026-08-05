import os
import sys
import json
import time
import logging
import sqlite3
import datetime

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class ScriptWriterAgent:
    """Agent 1: Expands raw visual concepts into detailed cinematic scripts."""
    def process(self, topic, category):
        logging.info(f"[*] [ScriptWriterAgent] Generating script for topic: '{topic}' [{category}]")
        script = f"System analysis for {topic}. Executing deep evaluation sequence across all neural vectors. Operational state nominal."
        return script

class PromptArchitectAgent:
    """Agent 2: Converts cinematic scripts into high-fidelity image/video prompts and negative prompts."""
    def process(self, script, category):
        logging.info(f"[*] [PromptArchitectAgent] Constructing optimized render prompts...")
        prompt = f"Hyper-realistic, cinematic lighting, 8k resolution, master quality scene depicting: {script}, high contrast, intricate detail"
        neg_prompt = "(deformed, distorted, disfigured:1.3), poorly drawn face, poorly drawn hands, low resolution, blurry, noise"
        return prompt, neg_prompt

class ExecutionOrchestrator:
    """Agent 3: Coordinates multi-agent output and stages payload for app.py & ComfyUI."""
    def __init__(self):
        self.writer = ScriptWriterAgent()
        self.architect = PromptArchitectAgent()

    def run_pipeline(self, topic, category="System Audit & Compliance", duration_mins=5):
        script = self.writer.process(topic, category)
        prompt, neg_prompt = self.architect.process(script, category)

        payload = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topic": topic,
            "category": category,
            "duration_minutes": duration_mins,
            "script": script,
            "prompt": prompt,
            "negative_prompt": neg_prompt,
            "seed": int(time.time()) % 1000000
        }

        # Log payload to local database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                topic TEXT,
                category TEXT,
                prompt TEXT,
                script TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO agent_tasks (timestamp, topic, category, prompt, script)
            VALUES (?, ?, ?, ?, ?)
        ''', (payload["timestamp"], topic, category, prompt, script))
        conn.commit()
        conn.close()

        logging.info("[+] [ExecutionOrchestrator] Task successfully generated and staged in master database.")
        return payload

if __name__ == "__main__":
    orchestrator = ExecutionOrchestrator()
    result = orchestrator.run_pipeline("Automated Quantum Data Audit", "System Audit & Compliance", 5)
    print(json.dumps(result, indent=4))