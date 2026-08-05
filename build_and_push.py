import os
import sys
import py_compile
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s"
)

TARGET_FILE = "app.py"

def check_syntax(file_path):
    """Compiles the target Python script to ensure there are no syntax errors."""
    logging.info(f"Checking syntax and compiling {file_path}...")
    try:
        py_compile.compile(file_path, doraise=True)
        logging.info("SUCCESS: Syntax check passed cleanly. No compilation errors detected.")
        return True
    except py_compile.PyCompileError as e:
        logging.error(f"FAIL: Syntax compilation error found in {file_path}:\n{e}")
        return False
    except Exception as e:
        logging.error(f"FAIL: Unexpected error during compilation: {e}")
        return False

def run_git_command(cmd_list):
    """Executes a git shell command safely."""
    try:
        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout.strip():
            logging.info(f"[Git Output]\n{result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {' '.join(cmd_list)}")
        logging.error(f"[Git Error Output]\n{e.stderr.strip()}")
        return False

def push_to_git(commit_message="Update app.py with auto-learning engine & pipeline updates"):
    """Stages, commits, and pushes changes to the active remote repository branch."""
    if not os.path.exists(".git"):
        logging.error("No .git repository initialized in this folder. Run 'git init' first.")
        return False

    logging.info("Staging target files...")
    if not run_git_command(["git", "add", TARGET_FILE, "build_and_push.py"]):
        return False

    logging.info(f"Committing changes: '{commit_message}'...")
    # Allow commit to succeed even if there are no new changes staged
    run_git_command(["git", "commit", "-m", commit_message])

    logging.info("Pushing to remote Git repository...")
    if run_git_command(["git", "push"]):
        logging.info("SUCCESS: Successfully pushed to Git remote!")
        return True
    else:
        logging.error("FAIL: Push to Git failed. Please check remote upstream settings or credentials.")
        return False

def main():
    if not os.path.exists(TARGET_FILE):
        logging.error(f"Target script '{TARGET_FILE}' not found in current directory: {os.getcwd()}")
        sys.exit(1)

    # 1. Compile & Check Syntax
    syntax_ok = check_syntax(TARGET_FILE)
    if not syntax_ok:
        logging.error("ABORTING: Fix syntax errors in app.py before pushing to Git.")
        sys.exit(1)

    # 2. Stage, Commit, and Push
    commit_msg = input("Enter custom commit message (Press Enter for default): ").strip()
    if not commit_msg:
        commit_msg = "Automated Build: Add complete app.py auto-learning pipeline"

    push_ok = push_to_git(commit_msg)
    if push_ok:
        logging.info("--- BUILD AND PUSH COMPLETE ---")
    else:
        logging.error("--- BUILD SUCCEEDED BUT GIT PUSH FAILED ---")

if __name__ == "__main__":
    main()