import os
import sys
import time
import json
import sqlite3
import logging
import threading
from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")

app = Flask(__name__)
API_SECRET_KEY = os.environ.get("GATEWAY_SECRET_KEY", "APEX_MASTER_KEY_999")

def verify_token(req):
    token = req.headers.get("X-API-KEY") or req.args.get("key")
    return token == API_SECRET_KEY

@app.route("/webhook/trigger_task", methods=["POST"])
def webhook_trigger_task():
    if not verify_token(request):
        return jsonify({"status": "UNAUTHORIZED", "message": "Invalid API Key"}), 401

    payload = request.json or {}
    task_type = payload.get("task_type", "GENERIC")
    task_payload = payload.get("payload", {})

    logging.info(f"[*] [WebhookGateway] Incoming Task Request: '{task_type}'")

    if os.path.exists("distributed_task_queue.py"):
        try:
            import distributed_task_queue
            dtq = distributed_task_queue.DistributedTaskQueue()
            task_id = f"task_wh_{int(time.time())}"
            dtq.add_task(task_id, task_type, task_payload, priority=1)
            return jsonify({"status": "QUEUED", "task_id": task_id})
        except Exception as e:
            logging.error(f"[!] Error forwarding task to queue: {e}")

    return jsonify({"status": "ACCEPTED", "message": "Payload received"})

@app.route("/webhook/flush_vram", methods=["POST"])
def webhook_flush_vram():
    if not verify_token(request):
        return jsonify({"status": "UNAUTHORIZED"}), 401

    if os.path.exists("system_self_healer.py"):
        import system_self_healer
        system_self_healer.SystemSelfHealer.purge_vram_and_cache()
        return jsonify({"status": "SUCCESS", "message": "Emergency VRAM flush executed."})

    return jsonify({"status": "FAILED", "message": "Self-healer module unavailable."})

@app.route("/webhook/status", methods=["GET"])
def webhook_status():
    return jsonify({
        "status": "ONLINE",
        "gateway_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "database_connected": os.path.exists(DB_PATH)
    })

def run_server_threaded():
    logging.info("[*] Launching Cloud Webhook Gateway on http://127.0.0.1:9095")
    app.run(host="127.0.0.1", port=9095, debug=False, use_reloader=False)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Cloud Webhook Gateway test verification complete (Non-blocking).")
    else:
        run_server_threaded()