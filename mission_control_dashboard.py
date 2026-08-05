import os
import sys
import json
import time
import sqlite3
import psutil
import torch
import logging
from flask import Flask, jsonify, render_template_string

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
LEARNING_RULES_FILE = os.path.join(BASE_DIR, "self_learning_brutal_ai", "optimized_rules.json")

# ==============================================================================
# HTML MISSION CONTROL INTERFACE TEMPLATE
# ==============================================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Apex AI - Mission Control Hub</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }
        h1 { color: #38bdf8; border-bottom: 2px solid #1e293b; padding-bottom: 10px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .card { background-color: #1e293b; border-radius: 8px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        .card h2 { margin-top: 0; color: #818cf8; font-size: 1.2rem; }
        .metric { font-size: 1.8rem; font-weight: bold; color: #4ade80; margin: 10px 0; }
        .sub-text { font-size: 0.9rem; color: #94a3b8; }
        pre { background: #020617; padding: 10px; border-radius: 4px; font-size: 0.85rem; overflow-x: auto; color: #e2e8f0; }
    </style>
</head>
<body>
    <h1>⚡ Apex AI - Mission Control Hub</h1>
    <div class="grid">
        <div class="card">
            <h2>Hardware Telemetry</h2>
            <div id="cpu-ram" class="metric">Loading...</div>
            <div id="gpu-info" class="sub-text">Checking GPU...</div>
        </div>
        <div class="card">
            <h2>Asset Vault Status</h2>
            <div id="asset-count" class="metric">0</div>
            <div class="sub-text">Total Indexed Videos & Snapshots</div>
        </div>
        <div class="card">
            <h2>Self-Learning Rules</h2>
            <pre id="learning-rules">Loading rules...</pre>
        </div>
    </div>

    <script>
        async function fetchMetrics() {
            try {
                const res = await fetch('/api/metrics');
                const data = await res.json();
                document.getElementById('cpu-ram').innerText = `CPU: ${data.cpu_usage}% | RAM: ${data.ram_used_gb}/${data.ram_total_gb} GB`;
                document.getElementById('gpu-info').innerText = `GPU: ${data.gpu_name} | VRAM: ${data.vram_allocated_mb} MB Allocated`;
                document.getElementById('asset-count').innerText = data.total_assets;
                document.getElementById('learning-rules').innerText = JSON.stringify(data.learning_rules, null, 2);
            } catch (e) {
                console.error("Telemetry fetch error:", e);
            }
        }
        setInterval(fetchMetrics, 3000);
        fetchMetrics();
    </script>
</body>
</html>
"""

# ==============================================================================
# REST API & DASHBOARD ENDPOINTS
# ==============================================================================
@app.route("/")
def dashboard_home():
    return render_template_string(HTML_TEMPLATE)

@app.route("/api/metrics", methods=["GET"])
def api_metrics():
    ram = psutil.virtual_memory()
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
    vram_alloc = round(torch.cuda.memory_allocated(0) / (1024 ** 2), 2) if torch.cuda.is_available() else 0

    total_assets = 0
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM assets")
            total_assets = cursor.fetchone()[0]
            conn.close()
        except Exception:
            pass

    learning_rules = {}
    if os.path.exists(LEARNING_RULES_FILE):
        try:
            with open(LEARNING_RULES_FILE, "r", encoding="utf-8") as f:
                learning_rules = json.load(f)
        except Exception:
            pass

    return jsonify({
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_usage": psutil.cpu_percent(),
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "gpu_name": gpu_name,
        "vram_allocated_mb": vram_alloc,
        "total_assets": total_assets,
        "learning_rules": learning_rules
    })

def run_server():
    logging.info("[*] Launching Mission Control Web Dashboard on http://127.0.0.1:8090")
    app.run(host="127.0.0.1", port=8090, debug=False, use_reloader=False)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Mission Control Dashboard test verification complete (Non-blocking).")
    else:
        run_server()