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
    print("[*] MASTER PIPELINE BUILD & AUDIT ENGINE DEPLOYMENT")
    print("==================================================")

    # 1. Upgrade Python Runtime Dependencies
    print("[*] Upgrading core Python packages...")
    run_command("pip install --upgrade pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers edge-tts mutagen flask requests numpy")

    # 2. Run Diagnostics & Pipeline Self-Tests
    if os.path.exists("copyright_compliance_auditor.py"):
        print("[*] Testing Copyright Compliance Auditor...")
        run_command("python copyright_compliance_auditor.py", check=False)

    if os.path.exists("lora_auto_trainer.py"):
        print("[*] Testing LoRA Auto-Trainer Scheduler...")
        run_command("python lora_auto_trainer.py", check=False)

    if os.path.exists("ci_system_diagnostics.py"):
        print("[*] Testing CI Diagnostics Runner...")
        run_command("python ci_system_diagnostics.py", check=False)

    if os.path.exists("model_quantizer_profiler.py"):
        print("[*] Testing Model Quantizer & Precision Profiler...")
        run_command("python model_quantizer_profiler.py", check=False)

    if os.path.exists("alert_notification_bot.py"):
        print("[*] Testing Alert Notification Engine...")
        run_command("python alert_notification_bot.py", check=False)

    if os.path.exists("cloud_webhook_gateway.py"):
        print("[*] Testing Cloud Webhook Gateway Engine...")
        run_command("python cloud_webhook_gateway.py", check=False)

    if os.path.exists("database_ha_replicator.py"):
        print("[*] Testing Database HA Replicator Engine...")
        run_command("python database_ha_replicator.py", check=False)

    if os.path.exists("cyber_integrity_monitor.py"):
        print("[*] Testing System Integrity Monitor...")
        run_command("python cyber_integrity_monitor.py", check=False)

    if os.path.exists("system_self_healer.py"):
        print("[*] Testing System Self-Healer...")
        run_command("python system_self_healer.py", check=False)

    if os.path.exists("distributed_cluster_node.py"):
        print("[*] Testing Distributed Cluster Node Engine...")
        run_command("python distributed_cluster_node.py", check=False)

    if os.path.exists("master_system_orchestrator.py"):
        print("[*] Testing Master System Orchestrator...")
        run_command("python master_system_orchestrator.py", check=False)

    if os.path.exists("mission_control_dashboard.py"):
        print("[*] Testing Mission Control Dashboard...")
        run_command("python mission_control_dashboard.py", check=False)

    if os.path.exists("ai_self_learning_loop.py"):
        print("[*] Testing AI Self-Learning Engine Loop...")
        run_command("python ai_self_learning_loop.py", check=False)

    if os.path.exists("social_auto_publisher.py"):
        print("[*] Testing Social Media Auto-Publisher...")
        run_command("python social_auto_publisher.py", check=False)

    if os.path.exists("automated_video_editor.py"):
        print("[*] Testing Automated Video Editor...")
        run_command("python automated_video_editor.py", check=False)

    if os.path.exists("semantic_vector_search.py"):
        print("[*] Testing Semantic Vector Search Engine...")
        run_command("python semantic_vector_search.py", check=False)

    if os.path.exists("live_stream_ingest.py"):
        print("[*] Testing Live Stream Engine...")
        run_command("python live_stream_ingest.py", check=False)

    if os.path.exists("motion_upscale_pipeline.py"):
        print("[*] Testing Motion Interpolation Engine...")
        run_command("python motion_upscale_pipeline.py", check=False)

    if os.path.exists("distributed_task_queue.py"):
        print("[*] Testing Distributed Task Queue...")
        run_command("python distributed_task_queue.py", check=False)

    if os.path.exists("dataset_auto_annotator.py"):
        print("[*] Testing Dataset Auto-Annotator...")
        run_command("python dataset_auto_annotator.py", check=False)

    if os.path.exists("multi_agent_pipeline.py"):
        print("[*] Testing Multi-Agent Pipeline...")
        run_command("python multi_agent_pipeline.py", check=False)

    if os.path.exists("model_and_workflow_manager.py"):
        print("[*] Testing Model & Workflow Manager...")
        run_command("python model_and_workflow_manager.py", check=False)

    # 3. Ensure update_comfy.py exists
    if not os.path.exists("update_comfy.py"):
        print("[*] Creating update_comfy.py...")
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

    # 4. Upgrade ComfyUI
    print("[*] Executing ComfyUI force upgrade...")
    run_command("python update_comfy.py", check=False)

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
        "vector_index.json\n",
        "published_analytics.json\n",
        "cluster_nodes.json\n",
        "system_integrity_manifest.json\n",
        "ci_test_report.json\n",
        "compliance_audit_log.json\n",
        "database_backups/\n",
        "self_learning_brutal_ai/dataset/\n",
        "self_learning_brutal_ai/optimized_rules.json\n",
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

    # 6. Compile Application via PyInstaller
    print("[*] Compiling app.py into ApexAIVideoStudio executable...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    # 7. Git Stage, Commit, and Push Source Code
    print("[*] Staging source code for Git repository...")
    run_command("git add app.py engine_coordinator.py multi_agent_pipeline.py model_and_workflow_manager.py system_self_healer.py dataset_auto_annotator.py distributed_task_queue.py motion_upscale_pipeline.py live_stream_ingest.py semantic_vector_search.py automated_video_editor.py social_auto_publisher.py ai_self_learning_loop.py mission_control_dashboard.py master_system_orchestrator.py distributed_cluster_node.py cyber_integrity_monitor.py database_ha_replicator.py cloud_webhook_gateway.py alert_notification_bot.py model_quantizer_profiler.py ci_system_diagnostics.py lora_auto_trainer.py copyright_compliance_auditor.py update_comfy.py build_and_push.py autostart_daemon.py system_benchmark.py run_autostart.bat .gitignore")
    
    commit_msg = '"Copyright compliance auditor integration, metadata verification & Git push deployment"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f"git commit -m {commit_msg}", check=False)

    print("[*] Pushing updates to GitHub remote...")
    run_command("git push origin main")

    print("[+] Full compile, copyright compliance auditor integration, and Git push sequence complete.")

if __name__ == "__main__":
    main()