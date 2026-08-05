# Enterprise PyTorch GPU Base Image
FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (FFmpeg for video processing & OpenCV support)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository source code
COPY . /app

EXPOSE 8000 8080 8090

CMD ["python", "master_pipeline_orchestrator.py"]
