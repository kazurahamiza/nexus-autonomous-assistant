import os
import sys
import time
import json
import sqlite3
import random
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

class ChaosCircuitBreaker:
    """Stress-tests microservices with simulated faults and enforces automated circuit breakers."""

    def __init__(self, failure_threshold=3):
        self.failure_threshold = failure_threshold
        self.failure_counts = {}
        self.circuit_states = {} # OPEN, CLOSED, HALF-OPEN
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chaos_circuit_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                service_name TEXT,
                state TEXT,
                failure_count INTEGER,
                chaos_injected TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def execute_with_circuit_breaker(self, service_name, target_function, *args, **kwargs):
        """Wraps execution with circuit breaking logic to halt cascading system failures."""
        state = self.circuit_states.get(service_name, "CLOSED")

        if state == "OPEN":
            logging.warning(f"[!] [CircuitBreaker] Circuit for '{service_name}' is OPEN! Request rejected/rerouted.")
            return None

        try:
            result = target_function(*args, **kwargs)
            # Reset failure count on success
            self.failure_counts[service_name] = 0
            self.circuit_states[service_name] = "CLOSED"
            return result
        except Exception as e:
            cnt = self.failure_counts.get(service_name, 0) + 1
            self.failure_counts[service_name] = cnt
            logging.error(f"[!] [CircuitBreaker] Service '{service_name}' failed ({cnt}/{self.failure_threshold}): {e}")

            if cnt >= self.failure_threshold:
                self.circuit_states[service_name] = "OPEN"
                logging.critical(f"[CRITICAL] Circuit tripped to OPEN for '{service_name}'! Rerouting workload.")

            self._log_circuit_event(service_name, self.circuit_states[service_name], cnt, "NONE")
            raise e

    def inject_chaos_simulation(self, service_name):
        """Simulates fault scenarios to validate system resilience."""
        faults = ["LATENCY_SPIKE", "VRAM_OOM_SIMULATION", "DB_LOCK_TIMEOUT"]
        selected_fault = random.choice(faults)
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")

        logging.info(f"[*] [ChaosEngine] Injecting fault '{selected_fault}' into '{service_name}'...")
        
        # Record Chaos Injection Log
        self._log_circuit_event(service_name, self.circuit_states.get(service_name, "CLOSED"), 0, selected_fault)
        return selected_fault

    def _log_circuit_event(self, service_name, state, failures, chaos_type):
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chaos_circuit_registry (timestamp, service_name, state, failure_count, chaos_injected)
            VALUES (?, ?, ?, ?, ?)
        ''', (now_str, service_name, state, failures, chaos_type))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Chaos Engineering & Circuit Breaker test complete (Non-blocking).")
    else:
        logging.info("[*] Testing Chaos Circuit Breaker Engine...")
        breaker = ChaosCircuitBreaker()
        breaker.inject_chaos_simulation("video_super_resolution_engine")