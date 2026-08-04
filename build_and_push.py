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
    run_command("pip install pyinstaller psutil")

    # 2. Build standalone executable
    print("[*] Compiling app.py into ApexAIVideoStudio.exe...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    print("[+] Executable created at: dist\\ApexAIVideoStudio\\ApexAIVideoStudio.exe")

    # 3. Configure .gitignore to prevent pushing 10GB+ build folders
    gitignore_path = ".gitignore"
    ignore_entries = ["build/\n", "dist/\n", "*.spec\n"]
    
    existing_content = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r") as f:
            existing_content = f.read()

    with open(gitignore_path, "a") as f:
        for entry in ignore_entries:
            if entry.strip() not in existing_content:
                f.write(entry)

    # 4. Commit and push source code changes
    run_command("git add app.py .gitignore build_and_push.py")
    run_command('git commit -m "feat(core): full 24-hour video studio engine and build script"')
    run_command("git push origin main")

if __name__ == "__main__":
    main()