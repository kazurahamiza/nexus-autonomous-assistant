import os
import sys
import time
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO, 
    format="[%(asctime)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("autostart_system.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_cmd(cmd, cwd=None):
    logging.info(f"[*] Executing Command: {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info(f"[+] Output: {result.stdout.strip()[:200]}")
        else:
            logging.warning(f"[!] Warning/Error: {result.stderr.strip()[:200]}")
        return result.returncode
    except Exception as e:
        logging.error(f"[!] Execution exception: {e}")
        return -1

def force_system_auto_update():
    logging.info("==================================================")
    logging.info("[*] INITIALIZING SYSTEM AUTO-UPDATE SEQUENCE")
    logging.info("==================================================")

    # 1. Pull Root Repository
    logging.info("[*] Pulling latest repository commits...")
    run_cmd("git fetch --all", cwd=BASE_DIR)
    run_cmd("git reset --hard origin/main", cwd=BASE_DIR)
    run_cmd("git pull origin main", cwd=BASE_DIR)

    # 2. Execute ComfyUI Engine Update
    update_comfy_script = os.path.join(BASE_DIR, "update_comfy.py")
    if os.path.exists(update_comfy_script):
        logging.info("[*] Upgrading ComfyUI & Custom Nodes...")
        run_cmd("python update_comfy.py", cwd=BASE_DIR)

    # 3. Upgrade Core Dependencies
    logging.info("[*] Upgrading core runtime packages...")
    run_cmd("pip install --upgrade yt-dlp deep-translator gradio diffusers torch torchvision edge-tts mutagen psutil", cwd=BASE_DIR)

def start_app_engine():
    app_script = os.path.join(BASE_DIR, "app.py")
    logging.info(f"[*] Launching Master Application Engine: {app_script}")
    
    proc = subprocess.Popen([sys.executable, app_script], cwd=BASE_DIR)
    logging.info(f"[+] app.py active under PID: {proc.pid}")
    return proc

if __name__ == "__main__":
    force_system_auto_update()
    app_process = start_app_engine()
    
    try:
        while True:
            time.sleep(30)
            if app_process.poll() is not None:
                logging.warning("[!] app.py exited unexpectedly. Restarting engine instantly...")
                force_system_auto_update()
                app_process = start_app_engine()
    except KeyboardInterrupt:
        logging.info("[*] Daemon stopped by user.")