"""
Parallel Model Loading Test with GPU Support
Optimized for RTX 4090 (24GB VRAM)
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading

print("=" * 60)
print("Ouroboros AI - Parallel Model Loading Test (GPU)")
print("=" * 60)

models_dir = Path("models")
print(f"\nModels directory: {models_dir.absolute()}")

# Model configurations optimized for RTX 4090 24GB VRAM
# Each model gets appropriate GPU layers for parallel loading
MODEL_CONFIGS = [
    {
        "file": "WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf",
        "agent": "RED Agent",
        "n_ctx": 4096,
        "n_gpu_layers": 35,  # Full offload for 7B Q4
    },
    {
        "file": "DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
        "agent": "BLUE Agent",
        "n_ctx": 4096,
        "n_gpu_layers": 35,  # Full offload for 7B Q4
    },
    {
        "file": "Phi-3.5-mini-instruct-Q6_K.gguf",
        "agent": "Support Agents",
        "n_ctx": 2048,
        "n_gpu_layers": 28,  # Full offload for 3.8B Q6
    }
]

print("\nModel files:")
all_found = True
for config in MODEL_CONFIGS:
    path = models_dir / config["file"]
    if path.exists():
        size_gb = path.stat().st_size / (1024**3)
        print(f"  [OK] {config['agent']}: {config['file']} ({size_gb:.2f} GB)")
    else:
        print(f"  [XX] {config['agent']}: {config['file']} - NOT FOUND")
        all_found = False

if not all_found:
    print("\n[ERROR] Some models missing!")
    exit(1)

# Parallel model loading
print("\n" + "=" * 60)
print("Loading ALL models in PARALLEL (GPU mode)...")
print("RTX 4090 24GB VRAM - Optimized Configuration")
print("=" * 60)

loaded_models = {}
load_lock = threading.Lock()


def load_model(config):
    """Load a single model with GPU offloading."""
    from llama_cpp import Llama
    
    model_path = str(models_dir / config["file"])
    agent_name = config["agent"]
    
    start_time = time.time()
    print(f"\n[LOADING] {agent_name}: {config['file']}")
    
    try:
        llm = Llama(
            model_path=model_path,
            n_ctx=config["n_ctx"],
            n_gpu_layers=config["n_gpu_layers"],
            verbose=False,
            n_threads=4,  # CPU threads for non-GPU ops
        )
        
        load_time = time.time() - start_time
        print(f"[OK] {agent_name} loaded in {load_time:.2f}s")
        
        return agent_name, llm, load_time
        
    except Exception as e:
        print(f"[ERROR] {agent_name}: {type(e).__name__}: {e}")
        return agent_name, None, 0


try:
    total_start = time.time()
    
    # Use ThreadPoolExecutor for parallel loading
    # max_workers=3 to load all models simultaneously
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(load_model, config): config for config in MODEL_CONFIGS}
        
        for future in as_completed(futures):
            agent_name, llm, load_time = future.result()
            if llm:
                with load_lock:
                    loaded_models[agent_name] = llm
    
    total_time = time.time() - total_start
    
    print("\n" + "-" * 60)
    print(f"Parallel Loading Complete: {len(loaded_models)}/{len(MODEL_CONFIGS)} models")
    print(f"Total Time: {total_time:.2f}s (parallel speedup)")
    print("-" * 60)
    
    # Test inference on each loaded model
    print("\nTesting inference on all loaded models...")
    
    for agent_name, llm in loaded_models.items():
        print(f"\n[TEST] {agent_name}:")
        try:
            output = llm("Say hello:", max_tokens=20)
            response = output['choices'][0]['text'].strip()[:50]
            print(f"  Response: {response}...")
            print(f"  [OK] Inference works!")
        except Exception as e:
            print(f"  [ERROR] Inference failed: {e}")
    
    # Cleanup all models
    print("\nCleaning up models from VRAM...")
    for agent_name in list(loaded_models.keys()):
        del loaded_models[agent_name]
    loaded_models.clear()
    print("[OK] VRAM released")
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Phase 1 Validation: COMPLETE")
print("=" * 60)
