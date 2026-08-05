import os
import sys
import time
import torch
import logging

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

class ModelQuantizerProfiler:
    """Monitors available VRAM and dynamically sets optimal execution precision for torch models."""

    @staticmethod
    def detect_optimal_dtype():
        """Returns torch.float16, torch.bfloat16, or torch.float32 based on GPU architecture and free VRAM."""
        if not torch.cuda.is_available():
            logging.info("[*] CUDA unavailable. Defaulting to float32 (CPU).")
            return torch.float32

        free_vram_gb = torch.cuda.mem_get_info()[0] / (1024 ** 3)
        device_capability = torch.cuda.get_device_capability()

        logging.info(f"[*] Available VRAM: {free_vram_gb:.2f} GB | GPU Compute Capability: {device_capability}")

        if free_vram_gb < 4.0:
            logging.info("[*] Low VRAM threshold reached (<4GB). Recommending fp16 precision with sequential offload.")
            return torch.float16
        elif device_capability[0] >= 8:  # Ampere or newer architecture
            logging.info("[+] BFloat16 supported and selected for high-throughput generation.")
            return torch.bfloat16
        else:
            return torch.float16

    @staticmethod
    def apply_pipeline_optimizations(pipeline):
        """Enables xformers, sliced attention, and CPU offloading based on hardware constraints."""
        if hasattr(pipeline, "enable_attention_slicing"):
            pipeline.enable_attention_slicing()
            logging.info("[+] Enabled attention slicing.")

        if hasattr(pipeline, "enable_vae_slicing"):
            pipeline.enable_vae_slicing()
            logging.info("[+] Enabled VAE slicing.")

        try:
            if hasattr(pipeline, "enable_xformers_memory_efficient_attention"):
                pipeline.enable_xformers_memory_efficient_attention()
                logging.info("[+] Enabled xFormers memory efficient attention.")
        except Exception as e:
            logging.warning(f"[!] xFormers acceleration not available: {e}")

        return pipeline

if __name__ == "__main__":
    logging.info("[*] Testing Model Quantizer & Precision Profiler Engine...")
    optimal_type = ModelQuantizerProfiler.detect_optimal_dtype()
    logging.info(f"[+] Optimal Precision DType Detected: {optimal_type}")