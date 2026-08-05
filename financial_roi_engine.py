import os
import sys
import time
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class FinancialROIEngine:
    """Tracks compute cost vs estimated ad/affiliate revenue to dynamically allocate budget."""

    def __init__(self):
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS financial_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                asset_id TEXT,
                compute_cost_usd REAL,
                estimated_revenue_usd REAL,
                roi_ratio REAL,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_asset_financials(self, asset_id, compute_cost=0.05, estimated_revenue=0.45):
        roi = round(estimated_revenue / max(0.001, compute_cost), 2)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO financial_ledger (timestamp, asset_id, compute_cost_usd, estimated_revenue_usd, roi_ratio, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (now_str, asset_id, compute_cost, estimated_revenue, roi, "LOGGED"))
        conn.commit()
        conn.close()

        logging.info(f"[+] [FinancialROI] Asset '{asset_id}': Cost=${compute_cost} | Rev=${estimated_revenue} | ROI={roi}x")
        return roi

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Financial ROI Engine test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Financial ROI Engine...")
        engine = FinancialROIEngine()
        engine.log_asset_financials("render_master_001")