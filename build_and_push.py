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
    print("[*] MASTER PIPELINE BUILD & LLM BRAIN DEPLOYMENT")
    print("==================================================")

    if os.path.exists("setup_enterprise_docker.py"):
        print("[*] Verifying Enterprise Docker configurations...")
        run_command("python setup_enterprise_docker.py")

    print("[*] Upgrading core Python dependencies...")
    run_command("pip install --upgrade pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers edge-tts mutagen flask requests numpy celery redis psycopg2-binary qdrant-client")

    test_modules = [
        ("llm_controller_brain.py", "python llm_controller_brain.py --test"),
        ("distributed_task_worker.py", "python distributed_task_worker.py --test"),
        ("enterprise_db_manager.py", "python enterprise_db_manager.py --test"),
        ("kernel_level_governor.py", "python kernel_level_governor.py --test"),
        ("chaos_circuit_breaker.py", "python chaos_circuit_breaker.py --test"),
        ("financial_roi_engine.py", "python financial_roi_engine.py --test"),
        ("multimodal_realtime_director.py", "python multimodal_realtime_director.py --test"),
        ("vtuber_audience_engine.py", "python vtuber_audience_engine.py --test"),
        ("self_evolving_code_engine.py", "python self_evolving_code_engine.py --test"),
        ("swarm_mesh_node.py", "python swarm_mesh_node.py --test"),
        ("mesh_model_cache_sync.py", "python mesh_model_cache_sync.py --test"),
        ("master_pipeline_orchestrator.py", "python master_pipeline_orchestrator.py --test"),
        ("ci_system_diagnostics.py", "python ci_system_diagnostics.py")
    ]

    for script, cmd in test_modules:
        if os.path.exists(script):
            print(f"[*] Testing {script}...")
            run_command(cmd, check=False)

    print("[*] Compiling app.py into ApexAIVideoStudio executable...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    print("[*] Staging source code and infrastructure definitions for Git repository...")
    run_command("git add Dockerfile .dockerignore docker-compose.yml setup_enterprise_docker.py requirements.txt app.py build_and_push.py master_pipeline_orchestrator.py swarm_mesh_node.py mesh_model_cache_sync.py financial_roi_engine.py multimodal_realtime_director.py vtuber_audience_engine.py self_evolving_code_engine.py chaos_circuit_breaker.py kernel_level_governor.py distributed_task_worker.py enterprise_db_manager.py llm_controller_brain.py .gitignore")
    
    commit_msg = '"LLM CONTROLLER BRAIN DEPLOYMENT: Cognitive JSON generation, automated task dispatch & Git push"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f'git commit -m {commit_msg}', check=False)

    print("[*] Pushing updates to GitHub remote...")
    run_command("git push origin main")

    print("[+] LLM Brain controller integration, full compile, and Git push sequence complete.")

if __name__ == "__main__":
    main()