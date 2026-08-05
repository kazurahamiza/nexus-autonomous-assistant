import os
import sys
import time
import gc
import torch
import psutil
import logging
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

app = Flask(__name__)

# ==============================================================================
# HARDWARE DIAGNOSTICS & MEMORY FLUSHING ENGINE
# ==============================================================================
def clear_system_vram():
    """Forces PyTorch to release unreferenced VRAM and calls garbage collector."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
        logging.info("[+] VRAM and PyTorch IPC cache successfully flushed.")
    return True

def get_system_telemetry():
    """Extracts real-time CPU, System RAM, and GPU VRAM statistics."""
    cpu_usage = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    
    gpu_data = {
        "cuda_available": torch.cuda.is_available(),
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "vram_allocated_mb": round(torch.cuda.memory_allocated(0) / (1024 ** 2), 2) if torch.cuda.is_available() else 0,
        "vram_reserved_mb": round(torch.cuda.memory_reserved(0) / (1024 ** 2), 2) if torch.cuda.is_available() else 0
    }

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_usage_percent": cpu_usage,
        "ram_used_gb": round(ram.used / (1024 ** 3), 2),
        "ram_total_gb": round(ram.total / (1024 ** 3), 2),
        "gpu": gpu_data
    }

# ==============================================================================
# REST API ENDPOINTS FOR REAL-TIME MONITORING
# ==============================================================================
@app.route("/telemetry", methods=["GET"])
def telemetry_endpoint():
    return jsonify(get_system_telemetry())

@app.route("/flush", methods=["POST", "GET"])
def flush_endpoint():
    clear_system_vram()
    return jsonify({"status": "success", "message": "VRAM flushed successfully."})

if __name__ == "__main__":
    logging.info("[*] Launching Engine Coordinator REST Server on http://127.0.0.1:8080")
    app.run(host="127.0.0.1", port=8080, debug=False)