import os
import sys
import time
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("auto_update_daemon.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_SCRIPT = os.path.join(BASE_DIR, "build_and_push.py")
INTERVAL_SECONDS = 86400  # Run every 24 hours (86400s)

def run_build_and_push():
    """Executes build_and_push.py non-blockingly."""
    logging.info("==================================================")
    logging.info("[*] DAEMON: Triggering automated Build & Push...")
    logging.info("==================================================")
    
    if not os.path.exists(BUILD_SCRIPT):
        logging.error(f"[!] Target script missing: {BUILD_SCRIPT}")
        return

    try:
        # Executes build_and_push.py using current Python runtime
        result = subprocess.run([sys.executable, BUILD_SCRIPT], cwd=BASE_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("[+] DAEMON: Build and Push completed successfully.")
        else:
            logging.error(f"[!] DAEMON: Build and Push failed with code {result.returncode}:\n{result.stderr[:500]}")
    except Exception as e:
        logging.error(f"[!] DAEMON: Exception during execution: {e}")

def main():
    logging.info("[*] Apex AI Auto-Update Daemon online.")
    
    # 1. Run immediately on daemon launch (startup)
    run_build_and_push()

    # 2. Continuous background loop
    while True:
        logging.info(f"[*] DAEMON: Sleeping for {INTERVAL_SECONDS // 3600} hours until next build cycle...")
        time.sleep(INTERVAL_SECONDS)
        run_build_and_push()

if __name__ == "__main__":
    main()