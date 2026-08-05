import os
import sys
import json
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
LEARNING_RULES_FILE = os.path.join(BASE_DIR, "self_learning_brutal_ai", "optimized_rules.json")

os.makedirs(os.path.dirname(LEARNING_RULES_FILE), exist_ok=True)

class AISelfLearningLoop:
    """Analyzes post performance and continuously optimizes prompt weighting parameters."""

    def __init__(self):
        self._init_rules_storage()

    def _init_rules_storage(self):
        if not os.path.exists(LEARNING_RULES_FILE):
            default_rules = {
                "top_performing_categories": ["System Audit & Compliance", "3D Animation & CGI Render"],
                "boost_keywords": ["hyper-realistic", "cinematic lighting", "8k resolution", "master rendering"],
                "penalty_keywords": ["blurry", "low quality", "distorted"],
                "optimal_duration_sec": 30,
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(LEARNING_RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(default_rules, f, indent=4)

    def analyze_performance_and_adapt(self):
        """Queries analytics metrics and updates the prompt optimization rule set."""
        if not os.path.exists(DB_PATH):
            logging.warning("[!] Database not found. Skipping self-learning analysis.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Query top-performing categories based on views
        try:
            cursor.execute('''
                SELECT category, COUNT(*), SUM(duration_sec) 
                FROM learned_dataset 
                GROUP BY category 
                ORDER BY COUNT(*) DESC
            ''')
            records = cursor.fetchall()
        except Exception as e:
            logging.warning(f"[!] Analytics query fallback: {e}")
            records = []
        conn.close()

        logging.info("[*] [SelfLearningEngine] Analyzing asset performance metrics...")

        # Dynamically load and update learning rules
        with open(LEARNING_RULES_FILE, "r", encoding="utf-8") as f:
            rules = json.load(f)

        if records:
            top_cats = [r[0] for r in records[:3]]
            rules["top_performing_categories"] = top_cats

        rules["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        with open(LEARNING_RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(rules, f, indent=4)

        logging.info(f"[+] [SelfLearningEngine] Learning rules optimized successfully: {rules['top_performing_categories']}")
        return rules

    def get_optimized_prompt_prefix(self):
        """Returns the current highest-weighted prompt injection string."""
        if os.path.exists(LEARNING_RULES_FILE):
            with open(LEARNING_RULES_FILE, "r", encoding="utf-8") as f:
                rules = json.load(f)
            return ", ".join(rules.get("boost_keywords", []))
        return "hyper-realistic, cinematic lighting, 8k resolution"

if __name__ == "__main__":
    logging.info("[*] Testing AI Self-Learning Engine Loop...")
    engine = AISelfLearningLoop()
    updated_rules = engine.analyze_performance_and_adapt()
    prefix = engine.get_optimized_prompt_prefix()
    logging.info(f"[+] Active Optimized Prompt Prefix: '{prefix}'")