import os
import sys
import time
import json
import sqlite3
import torch
import logging
import requests

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
TEST_REPORT_FILE = os.path.join(BASE_DIR, "ci_test_report.json")

class CIDiagnosticsRunner:
    """Executes pre-flight integration tests and diagnostic validation across all core modules."""

    def __init__(self):
        self.results = {}

    def test_database_connection(self):
        """Validates SQLite database file presence and table accessibility."""
        if not os.path.exists(DB_PATH):
            self.results["database"] = {"status": "SKIPPED", "details": "Database file not found"}
            return False

        try:
            conn = sqlite3.connect(DB_PATH, timeout=3)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            self.results["database"] = {
                "status": "PASSED",
                "tables_found": tables
            }
            return True
        except Exception as e:
            self.results["database"] = {"status": "FAILED", "error": str(e)}
            return False

    def test_cuda_hardware_acceleration(self):
        """Verifies CUDA environment, device counts, and basic tensor allocation."""
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            vram_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024 ** 3), 2)
            self.results["cuda_hardware"] = {
                "status": "PASSED",
                "device_name": device_name,
                "vram_gb": vram_gb
            }
            return True
        else:
            self.results["cuda_hardware"] = {
                "status": "WARNING",
                "details": "Running on CPU mode; CUDA acceleration not detected"
            }
            return False

    def test_api_endpoints(self):
        """Probes local microservice REST endpoints if active."""
        endpoints = {
            "engine_coordinator": "http://127.0.0.1:8080/telemetry",
            "mission_control": "http://127.0.0.1:8090/api/metrics"
        }

        endpoint_status = {}
        for name, url in endpoints.items():
            try:
                res = requests.get(url, timeout=2)
                endpoint_status[name] = "ONLINE" if res.status_code == 200 else f"HTTP {res.status_code}"
            except Exception:
                endpoint_status[name] = "OFFLINE"

        self.results["api_endpoints"] = endpoint_status

    def run_all_diagnostics(self):
        logging.info("==================================================")
        logging.info("[*] EXECUTING CONTINUOUS INTEGRATION DIAGNOSTICS")
        logging.info("==================================================")

        self.test_database_connection()
        self.test_cuda_hardware_acceleration()
        self.test_api_endpoints()

        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "diagnostics": self.results
        }

        with open(TEST_REPORT_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4)

        logging.info(f"[+] Diagnostic suit complete. Test report saved to '{TEST_REPORT_FILE}'.")
        return report

if __name__ == "__main__":
    runner = CIDiagnosticsRunner()
    runner.run_all_diagnostics()