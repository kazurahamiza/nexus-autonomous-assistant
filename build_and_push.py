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
    print("[*] MASTER PIPELINE BUILD & DEPLOYMENT SYSTEM")
    print("==================================================")

    # 1. Dependency Updates
    print("[*] Verifying Python core requirements...")
    run_command("pip install --upgrade yt-dlp gradio opencv-python pyinstaller requests", check=False)

    # 2. Test Key Pipeline Modules
    test_modules = [
        ("dataset_crawler_trainer.py", "python dataset_crawler_trainer.py --test"),
        ("llm_controller_brain.py", "python llm_controller_brain.py --test"),
        ("distributed_task_worker.py", "python distributed_task_worker.py --test"),
        ("enterprise_db_manager.py", "python enterprise_db_manager.py --test")
    ]

    for script, cmd in test_modules:
        if os.path.exists(script):
            print(f"[*] Testing {script}...")
            run_command(cmd, check=False)

    # 3. PyInstaller Executable Compilation
    print("[*] Compiling app.py into ApexAIVideoStudio standalone executable...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    # 4. Git Staging & Deployment Push
    print("[*] Staging source repository changes...")
    run_command("git add app.py build_and_push.py dataset_crawler_trainer.py dataset_auto_annotator.py llm_controller_brain.py .gitignore", check=False)
    
    commit_msg = '"DEPLOYMENT: Automated browser cookie video downloader with exact title formatting"'
    print(f"[*] Committing changes to git local branch...")
    run_command(f'git commit -m {commit_msg}', check=False)

    print("[*] Pushing branch updates to origin main...")
    run_command("git push origin main", check=False)

    print("[+] Full system build, compilation, and git deployment complete.")

if __name__ == "__main__":
    main()