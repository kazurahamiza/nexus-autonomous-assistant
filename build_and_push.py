import os
import subprocess
import sys

def run_command(cmd, check=True):
    print(f"[*] Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"[!] Command failed: {cmd}")
        sys.exit(result.returncode)

def main():
    # 1. Execute ComfyUI Brutal Engine Update
    if os.path.exists("update_comfy.py"):
        print("[*] Launching ComfyUI engine upgrade...")
        run_command("python update_comfy.py", check=False)

    # 2. Install Core System Requirements
    run_command("pip install pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers")

    # 3. Secure .gitignore to prevent Git large payload locks
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
        "ComfyUI/models/\n"
    ]

    existing_content = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            existing_content = f.read()

    with open(gitignore_path, "a") as f:
        for entry in ignore_entries:
            if entry not in existing_content:
                f.write(entry)

    print("[+] .gitignore configured.")

    # 4. Compile Standalone Application
    print("[*] Compiling app.py into ApexAIVideoStudio.exe...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    # 5. Commit and Push to Git Remote
    print("[*] Staging source code changes for Git...")
    run_command("git add app.py update_comfy.py build_and_push.py .gitignore")
    
    commit_msg = '"Master system update & ComfyUI peak engine upgrade"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f"git commit -m {commit_msg}", check=False)

    print("[*] Pushing source code to remote GitHub repository...")
    run_command("git push origin main")

    print("[+] Master build, ComfyUI update, and Git push sequence complete.")

if __name__ == "__main__":
    main()