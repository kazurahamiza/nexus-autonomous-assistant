import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

POSSIBLE_COMFY_PATHS = [
    os.path.join(BASE_DIR, "ComfyUI"),
    os.path.join(BASE_DIR, "comfyui"),
    "D:\\repo\\ComfyUI",
    "C:\\ComfyUI_windows_portable\\ComfyUI"
]

COMFY_DIR = None
for p in POSSIBLE_COMFY_PATHS:
    if os.path.exists(p) and os.path.exists(os.path.join(p, "main.py")):
        COMFY_DIR = p
        break

def run_cmd(cmd, cwd=None):
    print(f"[*] Executing: {cmd} (Directory: {cwd or os.getcwd()})")
    result = subprocess.run(cmd, shell=True, cwd=cwd)
    if result.returncode != 0:
        logging.warning(f"[!] Command exited with code {result.returncode}: {cmd}")

def update_comfyui_system():
    if not COMFY_DIR:
        logging.info("[*] ComfyUI directory not found in local paths. Cloning fresh instance...")
        target_dir = os.path.join(BASE_DIR, 'ComfyUI')
        run_cmd(f'git clone https://github.com/comfyanonymous/ComfyUI.git "{target_dir}"')
    else:
        target_dir = COMFY_DIR

    logging.info(f"[+] Found ComfyUI Core at: {target_dir}")

    # 1. Force Pull Latest Core Updates
    logging.info("[*] Force updating ComfyUI core repo...")
    run_cmd("git fetch --all", cwd=target_dir)
    run_cmd("git reset --hard origin/master", cwd=target_dir)
    run_cmd("git pull origin master", cwd=target_dir)

    # 2. Force Update All Custom Nodes
    custom_nodes_path = os.path.join(target_dir, "custom_nodes")
    if os.path.exists(custom_nodes_path):
        logging.info("[*] Scanning and updating all installed Custom Nodes...")
        for node in os.listdir(custom_nodes_path):
            node_full_path = os.path.join(custom_nodes_path, node)
            if os.path.isdir(node_full_path) and os.path.exists(os.path.join(node_full_path, ".git")):
                logging.info(f"[*] Updating node: {node}")
                run_cmd("git fetch --all", cwd=node_full_path)
                run_cmd("git pull", cwd=node_full_path)

                node_reqs = os.path.join(node_full_path, "requirements.txt")
                if os.path.exists(node_reqs):
                    run_cmd(f'pip install -r "{node_reqs}"')

    # 3. Upgrade Core Dependencies
    logging.info("[*] Upgrading PyTorch, XFormers, and Diffusers...")
    run_cmd("pip install --upgrade torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121")
    run_cmd("pip install --upgrade diffusers transformers xformers accelerate insightface ultralytics")

    logging.info("[+] ComfyUI Engine updated successfully.")

if __name__ == "__main__":
    update_comfyui_system()