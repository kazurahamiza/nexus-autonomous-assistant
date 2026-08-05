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
    print("[*] MASTER PIPELINE BUILD & ANALYTICS COLLECTOR DEPLOYMENT")
    print("==================================================")

    print("[*] Upgrading core Python packages...")
    run_command("pip install --upgrade pyinstaller psutil deep-translator yt-dlp gradio opencv-python diffusers edge-tts mutagen flask requests numpy")

    # Run Module Diagnostics with --test flags for servers & CLI tools
    test_modules = [
        ("post_publish_analytics_collector.py", "python post_publish_analytics_collector.py --test"),
        ("video_super_resolution_engine.py", "python video_super_resolution_engine.py --test"),
        ("viral_trend_analyzer.py", "python viral_trend_analyzer.py --test"),
        ("multilingual_voice_cloner.py", "python multilingual_voice_cloner.py --test"),
        ("cinematic_color_grader.py", "python cinematic_color_grader.py --test"),
        ("visual_quality_inspector.py", "python visual_quality_inspector.py --test"),
        ("ab_thumbnail_generator.py", "python ab_thumbnail_generator.py --test"),
        ("audio_atmosphere_synthesizer.py", "python audio_atmosphere_synthesizer.py --test"),
        ("video_watermark_branding.py", "python video_watermark_branding.py --test"),
        "auto_caption_generator.py",
        "copyright_compliance_auditor.py",
        "lora_auto_trainer.py",
        "ci_system_diagnostics.py",
        "model_quantizer_profiler.py",
        "alert_notification_bot.py",
        ("cloud_webhook_gateway.py", "python cloud_webhook_gateway.py --test"),
        "database_ha_replicator.py",
        "cyber_integrity_monitor.py",
        "system_self_healer.py",
        ("distributed_cluster_node.py", "python distributed_cluster_node.py --test"),
        ("mission_control_dashboard.py", "python mission_control_dashboard.py --test"),
        ("engine_coordinator.py", "python engine_coordinator.py --test"),
        "ai_self_learning_loop.py",
        "social_auto_publisher.py",
        "automated_video_editor.py",
        "semantic_vector_search.py",
        "live_stream_ingest.py",
        "motion_upscale_pipeline.py",
        "distributed_task_queue.py",
        "dataset_auto_annotator.py",
        "multi_agent_pipeline.py",
        "model_and_workflow_manager.py"
    ]

    for item in test_modules:
        if isinstance(item, tuple):
            script, cmd = item
            if os.path.exists(script):
                print(f"[*] Testing {script}...")
                run_command(cmd, check=False)
        else:
            if os.path.exists(item):
                print(f"[*] Testing {item}...")
                run_command(f"python {item}", check=False)

    # Configure .gitignore
    gitignore_path = ".gitignore"
    ignore_entries = [
        "build/\n", "dist/\n", "*.spec\n", "*.db\n", "outputs/\n",
        "videos/\n", "input_videos/\n", "vector_index.json\n",
        "published_analytics.json\n", "cluster_nodes.json\n",
        "system_integrity_manifest.json\n", "ci_test_report.json\n",
        "compliance_audit_log.json\n", "watermark.png\n",
        "quality_inspection_log.json\n", "viral_trends_cache.json\n",
        "auto_update_daemon.log\n", "database_backups/\n",
        "self_learning_brutal_ai/dataset/\n",
        "self_learning_brutal_ai/optimized_rules.json\n",
        "ComfyUI/output/\n", "ComfyUI/input/\n", "ComfyUI/models/\n",
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

    # Compile Application
    print("[*] Compiling app.py into ApexAIVideoStudio executable...")
    pyinstaller_cmd = (
        "pyinstaller --noconfirm --onedir --console "
        "--name ApexAIVideoStudio "
        "--clean "
        "app.py"
    )
    run_command(pyinstaller_cmd)

    # Git Commit and Push
    print("[*] Staging source code for Git repository...")
    run_command("git add app.py engine_coordinator.py multi_agent_pipeline.py model_and_workflow_manager.py system_self_healer.py dataset_auto_annotator.py distributed_task_queue.py motion_upscale_pipeline.py live_stream_ingest.py semantic_vector_search.py automated_video_editor.py social_auto_publisher.py ai_self_learning_loop.py mission_control_dashboard.py master_system_orchestrator.py distributed_cluster_node.py cyber_integrity_monitor.py database_ha_replicator.py cloud_webhook_gateway.py alert_notification_bot.py model_quantizer_profiler.py ci_system_diagnostics.py lora_auto_trainer.py copyright_compliance_auditor.py auto_caption_generator.py video_watermark_branding.py audio_atmosphere_synthesizer.py ab_thumbnail_generator.py visual_quality_inspector.py cinematic_color_grader.py multilingual_voice_cloner.py viral_trend_analyzer.py video_super_resolution_engine.py post_publish_analytics_collector.py auto_update_daemon.py run_daemon_hidden.vbs update_comfy.py build_and_push.py autostart_daemon.py system_benchmark.py run_autostart.bat .gitignore")
    
    commit_msg = '"Post-publish analytics collector integration, closed-loop feedback telemetry & Git push deployment"'
    print(f"[*] Committing changes: {commit_msg}")
    run_command(f'git commit -m {commit_msg}', check=False)

    print("[*] Pushing updates to GitHub remote...")
    run_command("git push origin main")

    print("[+] Full compile, post-publish analytics collector integration, and Git push sequence complete.")

if __name__ == "__main__":
    main()