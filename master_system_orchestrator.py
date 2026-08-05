import os
import sys
import time
import subprocess
import logging
import threading

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Microservice Registry & Command Configurations
SERVICES = {
    "engine_coordinator": {
        "cmd": [sys.executable, "engine_coordinator.py"],
        "port": 8080,
        "proc": None
    },
    "mission_control": {
        "cmd": [sys.executable, "mission_control_dashboard.py"],
        "port": 8090,
        "proc": None
    },
    "app_gradio": {
        "cmd": [sys.executable, "app.py"],
        "port": 7860,
        "proc": None
    }
}

class SystemOrchestrator:
    """Master supervisor managing process lifecycles and background auto-healing across all services."""

    def __init__(self):
        self.is_running = True

    def start_service(self, name):
        svc = SERVICES.get(name)
        if not svc:
            return

        script_path = svc["cmd"][1]
        if os.path.exists(script_path):
            logging.info(f"[*] [Orchestrator] Launching service: '{name}' ({script_path})...")
            proc = subprocess.Popen(svc["cmd"], cwd=BASE_DIR)
            svc["proc"] = proc
            logging.info(f"[+] [Orchestrator] Service '{name}' active under PID: {proc.pid}")
        else:
            logging.warning(f"[!] Cannot start service '{name}'. File missing: {script_path}")

    def monitor_and_heal(self):
        """Monitors all registered microservices and restarts them if they crash or exit."""
        while self.is_running:
            for name, svc in SERVICES.items():
                proc = svc["proc"]
                if proc is None:
                    self.start_service(name)
                elif proc.poll() is not None:
                    logging.warning(f"[!] [Orchestrator] Service '{name}' stopped unexpectedly. Auto-healing restart triggered...")
                    self.start_service(name)
            time.sleep(10)

    def run_all_services(self):
        logging.info("==================================================")
        logging.info("[*] LAUNCHING APEX MASTER SYSTEM ORCHESTRATOR")
        logging.info("==================================================")

        for name in SERVICES.keys():
            self.start_service(name)

        monitor_thread = threading.Thread(target=self.monitor_and_heal, daemon=True)
        monitor_thread.start()

        logging.info("[+] All system microservices successfully launched and under master supervision.")

if __name__ == "__main__":
    orchestrator = SystemOrchestrator()
    orchestrator.run_all_services()

    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        logging.info("[*] Master Orchestrator shut down by user.")