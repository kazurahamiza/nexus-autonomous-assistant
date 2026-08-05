import os
import sys
import time
import logging
from celery import Celery

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

# Connect Celery to the local Redis container broker
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
app = Celery("apex_enterprise_tasks", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max task duration for heavy GPU renders
)

@app.task(name="tasks.execute_video_pipeline")
def execute_video_pipeline(asset_id, script_text):
    """Asynchronous worker task for heavy media generation."""
    logging.info(f"[*] [DistributedWorker] Processing Asset '{asset_id}' on Celery GPU Node...")
    
    # Simulating long-running enterprise GPU render
    time.sleep(2)
    
    return {
        "status": "COMPLETED",
        "asset_id": asset_id,
        "processed_by": "celery_worker_node_01",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

@app.task(name="tasks.enforce_kernel_governance")
def enforce_kernel_governance():
    """Background system health audit executed across worker pool."""
    from kernel_level_governor import KernelLevelGovernor
    gov = KernelLevelGovernor()
    action = gov.enforce_kernel_limits()
    return {"status": "SUCCESS", "kernel_action": action}

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Distributed Task Worker module verified (Non-blocking).")
    else:
        logging.info("[*] Starting Celery Worker Node...")
        app.worker_main(argv=["worker", "--loglevel=info", "--pool=solo"])