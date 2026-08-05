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
    print("[*] MASTER PIPELINE BUILD & GIT PUSH DEPLOYMENT")
    print("==================================================")

    # 1. Install / Upgrade System Dependencies
    print("[*] Upgrading core Python runtime packages...")
    run_command("pip install --upgrade pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers edge-tts mutagen flask requests")

    # 2. Run Hardware Benchmark if present
    if os.path.exists("system_benchmark.py"):
        print("[*] Executing Hardware Diagnostics...")
        run_command("python system_benchmark.py", check=False)

    # 3. Configure .gitignore
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

    # 4. Compile Standalone Application via PyInstaller
    print("[*] Compiling app.py into ApexAIVideoStudio executable...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    # 5. Stage, Commit, and Push Changes to Git Remote
    print("[*] Staging source code for Git repository...")
    run_command("git add app.py engine_coordinator.py update_comfy.py build_and_push.py autostart_daemon.py system_benchmark.py run_autostart.bat .gitignore")
    
    commit_msg = '"Engine coordinator integration, API telemetry sync & Git push deployment"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f"git commit -m {commit_msg}", check=False)

    print("[*] Pushing updates to GitHub remote...")
    run_command("git push origin main")

    print("[+] Master build, API integration, and Git push sequence complete.")

if __name__ == "__main__":
    main()