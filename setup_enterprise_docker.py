import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

files_to_create = {
    # 1. Dockerfile
    "Dockerfile": """# Enterprise PyTorch GPU Base Image
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (FFmpeg for video processing & OpenCV support)
RUN apt-get update && apt-get install -y \\
    ffmpeg \\
    git \\
    libgl1-mesa-glx \\
    libglib2.0-0 \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository source code
COPY . /app

EXPOSE 8000 8080 8090

CMD ["python", "master_pipeline_orchestrator.py"]
""",

    # 2. .dockerignore
    ".dockerignore": """build/
dist/
*.spec
*.db
outputs/
videos/
input_videos/
vector_index.json
published_analytics.json
cluster_nodes.json
system_integrity_manifest.json
ci_test_report.json
compliance_audit_log.json
quality_inspection_log.json
viral_trends_cache.json
auto_update_daemon.log
database_backups/
self_learning_brutal_ai/
ComfyUI/
autostart_system.log
.git
.venv
__pycache__
*.pyc
""",

    # 3. requirements.txt
    "requirements.txt": """psutil
deep-translator
yt-dlp
gradio
opencv-python
diffusers
edge-tts
mutagen
flask
requests
numpy
torch
celery
redis
psycopg2-binary
qdrant-client
""",

    # 4. docker-compose.yml
    "docker-compose.yml": """version: '3.8'

services:
  postgres_db:
    image: postgres:16-alpine
    container_name: apex_postgres
    environment:
      POSTGRES_DB: apex_enterprise_registry
      POSTGRES_USER: master_admin
      POSTGRES_PASSWORD: MasterSecurePassword123!
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis_broker:
    image: redis:7-alpine
    container_name: apex_redis
    ports:
      - "6379:6379"

  qdrant_vector_db:
    image: qdrant/qdrant
    container_name: apex_qdrant
    ports:
      - "6333:6333"

volumes:
  postgres_data:
"""
}

def build_files():
    print("==================================================")
    print("[*] GENERATING ENTERPRISE DOCKER CONFIGURATIONS")
    print("==================================================")
    for filename, content in files_to_create.items():
        file_path = os.path.join(BASE_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")
        print(f"[+] Created: {file_path}")
    print("==================================================")
    print("[+] Enterprise Docker configuration files ready.")

if __name__ == "__main__":
    build_files()