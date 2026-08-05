import os
import sys
import json
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Standard ComfyUI Model Target Directories
COMFY_BASE = os.path.join(BASE_DIR, "ComfyUI")
CHECKPOINT_DIR = os.path.join(COMFY_BASE, "models", "checkpoints")
LORA_DIR = os.path.join(COMFY_BASE, "models", "loras")

os.makedirs(CHECKPOINT_DIR, exist_ok=True)
os.makedirs(LORA_DIR, exist_ok=True)

class ComfyAPIEngine:
    """Interfaces directly with ComfyUI's active REST Server."""
    def __init__(self, server_address="127.0.0.1:8188"):
        self.server_address = server_address

    def is_server_online(self):
        try:
            res = requests.get(f"http://{self.server_address}/system_stats", timeout=2)
            return res.status_code == 200
        except Exception:
            return False

    def queue_workflow(self, workflow_json):
        """Sends raw ComfyUI node graph JSON to execution queue."""
        if not self.is_server_online():
            logging.warning("[!] ComfyUI API server is offline. Check if main.py is running on port 8188.")
            return None

        p = {"prompt": workflow_json}
        data = json.dumps(p).encode('utf-8')
        try:
            req = requests.post(f"http://{self.server_address}/prompt", data=data)
            return req.json()
        except Exception as e:
            logging.error(f"[!] Error queuing workflow to ComfyUI: {e}")
            return None

def fetch_external_model(url, save_directory, filename):
    """Downloads model weights directly into designated ComfyUI folders."""
    target_path = os.path.join(save_directory, filename)
    if os.path.exists(target_path):
        logging.info(f"[+] Model weight '{filename}' already exists. Skipping download.")
        return target_path

    logging.info(f"[*] Downloading model weight from: {url}")
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            with open(target_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"[+] Successfully downloaded: {target_path}")
            return target_path
    except Exception as e:
        logging.error(f"[!] Download failed for {url}: {e}")
    return None

if __name__ == "__main__":
    engine = ComfyAPIEngine()
    online = engine.is_server_online()
    logging.info(f"[*] ComfyUI Engine Online Status: {online}")