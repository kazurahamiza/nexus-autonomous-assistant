import torch
import time

def run_benchmark():
    print("==================================================")
    print("[*] SYSTEM HARDWARE & CUDA PERFORMANCE BENCHMARK")
    print("==================================================")

    if not torch.cuda.is_available():
        print("[!] CUDA is NOT available. System running on CPU fallback.")
        return

    device_name = torch.cuda.get_device_name(0)
    vram_total = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    
    print(f"[+] GPU Detected: {device_name}")
    print(f"[+] Total Dedicated VRAM: {vram_total:.2f} GB")

    # Tensor Compute Test
    size = 8000
    print(f"[*] Allocating {size}x{size} FP32 matrices on GPU...")
    x = torch.randn(size, size, device="cuda")
    y = torch.randn(size, size, device="cuda")

    start_time = time.time()
    for _ in range(10):
        z = torch.matmul(x, y)
    torch.cuda.synchronize()
    elapsed = time.time() - start_time

    print(f"[+] Compute Matrix Multiply Test Completed in: {elapsed:.4f} seconds.")
    print("[+] GPU Acceleration fully operational.")

if __name__ == "__main__":
    run_benchmark()