import os
import subprocess
import sys

def run_command(cmd, check=True):
    print(f"[*] Executing Command: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"[!] Command failed with exit code {result.returncode}: {cmd}")
        sys.exit(result.returncode)

def main():
    print("==================================================")
    print("[*] FULL-SCALE SYSTEM BUILD, BENCHMARK & GIT PUSH")
    print("==================================================")

    # 1. Run Hardware Diagnostics
    if os.path.exists("system_benchmark.py"):
        print("[*] Running Hardware Diagnostics...")
        run_command("python system_benchmark.py", check=False)

    # 2. Self-generate update_comfy.py if missing
    if not os.path.exists("update_comfy.py"):
        print("[*] update_comfy.py missing. Auto-generating script...")
        comfy_code = """import os, sys, subprocess, logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POSSIBLE_COMFY_PATHS = [os.path.join(BASE_DIR, "ComfyUI"), os.path.join(BASE_DIR, "comfyui"), "D:\\\\repo\\\\ComfyUI", "C:\\\\ComfyUI_windows_portable\\\\ComfyUI"]
COMFY_DIR = None
for p in POSSIBLE_COMFY_PATHS:
    if os.path.exists(p) and os.path.exists(os.path.join(p, "main.py")):
        COMFY_DIR = p
        break
def run_cmd(cmd, cwd=None):
    print(f"[*] Executing: {cmd}")
    subprocess.run(cmd, shell=True, cwd=cwd)
def update_comfyui_system():
    target_dir = COMFY_DIR if COMFY_DIR else os.path.join(BASE_DIR, 'ComfyUI')
    if not COMFY_DIR: run_cmd(f'git clone https://github.com/comfyanonymous/ComfyUI.git "{target_dir}"')
    run_cmd("git fetch --all", cwd=target_dir)
    run_cmd("git pull origin master", cwd=target_dir)
if __name__ == "__main__": update_comfyui_system()
"""
        with open("update_comfy.py", "w", encoding="utf-8") as f:
            f.write(comfy_code)

    # 3. Upgrade ComfyUI Engine
    print("[*] Upgrading ComfyUI core & custom nodes...")
    run_command("python update_comfy.py", check=False)

    # 4. Upgrade Python Runtime Packages
    print("[*] Upgrading core Python dependencies...")
    run_command("pip install --upgrade pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers edge-tts mutagen")

    # 5. Configure .gitignore
    gitignore_path = ".gitignore"
    ignore_entries = [
        "build/\n", 
        "dist/\n", 
        "*.spec\n", 
        "*.db\n", 
        "outputs/\n", 
        "videos/\n", 
        "input_videos/\n",
        "ComfyUI/output/\n",
        "ComfyUI/input/\n",
        "ComfyUI/models/\n",
        "autostart_system.log\n"
    ]

    existing_content = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            existing_content = f.read()

    with open(gitignore_path, "a") as f:
        for entry in ignore_entries:
            if entry not in existing_content:
                f.write(entry)

    # 6. Compile Standalone Application via PyInstaller
    print("[*] Compiling app.py into ApexAIVideoStudio executable...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    # 7. Stage, Commit, and Push Changes to Git Remote
    print("[*] Staging source code for Git repository...")
    run_command("git add app.py update_comfy.py build_and_push.py autostart_daemon.py system_benchmark.py run_autostart.bat .gitignore")
    
    commit_msg = '"Full-scale pipeline upgrade, hardware benchmark integration & Git push deployment"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f"git commit -m {commit_msg}", check=False)

    print("[*] Pushing updates to GitHub remote...")
    run_command("git push origin main")

    print("[+] Full manual compile, benchmark, and Git push sequence complete.")

if __name__ == "__main__":
    main()