import os
import subprocess
import sys

def run_command(cmd, check=True):
    """Executes system commands with real-time output stream."""
    print(f"[*] Running: {cmd}")
    result = subprocess.run(cmd, shell=True)
    if check and result.returncode != 0:
        print(f"[!] Command failed: {cmd}")
        sys.exit(result.returncode)

def main():
    # 1. Install Windows-compatible runtime dependencies
    run_command("pip install pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers")

    # 2. Configure .gitignore to ensure heavy build folders are NOT pushed
    gitignore_path = ".gitignore"
    ignore_entries = [
        "build/\n", 
        "dist/\n", 
        "*.spec\n", 
        "*.db\n", 
        "outputs/\n", 
        "videos/\n", 
        "input_videos/\n"
    ]

    existing_content = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            existing_content = f.read()

    with open(gitignore_path, "a") as f:
        for entry in ignore_entries:
            if entry not in existing_content:
                f.write(entry)

    print("[+] .gitignore configured to keep repository payload clean.")

    # 3. Build standalone executable
    print("[*] Compiling app.py into ApexAIVideoStudio.exe...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    print("[+] Executable created at: dist\\ApexAIVideoStudio\\ApexAIVideoStudio.exe")

    # 4. Git Stage, Commit, and Push Source Code
    print("[*] Staging source code changes for Git...")
    run_command("git add app.py build_and_push.py .gitignore")
    
    commit_msg = f'"Auto-update pipeline & app.py build"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f"git commit -m {commit_msg}", check=False)

    print("[*] Pushing source code to remote GitHub repository...")
    run_command("git push origin main")

    print("[+] Source code successfully pushed to Git repository.")

if __name__ == "__main__":
    main()