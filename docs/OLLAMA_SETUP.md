# Ollama Setup Guide for Ouroboros AI

## Overview
Ouroboros AI uses Ollama for running local LLM models. This guide will help you set up Ollama and load the required models.

## Installation

### 1. Install Ollama
Ollama is already installed at `/usr/local/bin/ollama`.

Verify installation:
```bash
ollama --version
```

### 2. Start Ollama Service
```bash
# Start Ollama (runs as background service)
ollama serve
```

Ollama will start on `http://localhost:11434`.

## Model Setup

### Required Models (Total ~7.2 GB)

#### 1. RED Agent - Qwen2.5-Coder 3B (~2.4 GB)
```bash
ollama pull qwen2.5-coder:3b
```

#### 2. BLUE Agent - DeepSeek-Coder 1.3B (~2.2 GB)
```bash
ollama pull deepseek-coder:1.3b
```

#### 3. Support Agents - Phi-3 Mini (~2.6 GB)
```bash
ollama pull phi3:mini
```

### Verify Models
```bash
ollama list
```

Expected output:
```
NAME                        ID              SIZE     MODIFIED
qwen2.5-coder:3b           abc123          2.4 GB   X minutes ago
deepseek-coder:1.3b        def456          2.2 GB   X minutes ago
phi3:mini                  ghi789          2.6 GB   X minutes ago
```

## Testing Models

### Quick Test
```bash
# Test RED agent model
ollama run qwen2.5-coder:3b "Write a simple Python function"

# Test BLUE agent model
ollama run deepseek-coder:1.3b "Fix this code: def foo() return 1"

# Test support model
ollama run phi3:mini "Summarize: This is a security vulnerability report"
```

### Python Test
```bash
# Activate venv and install dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run model test script
python3 scripts/test_models.py
```

## Configuration

The Ollama model mappings are defined in `src/models/model_loader.py`:

```python
model_name_mapping = {
    "Qwen2.5-Coder-3B": "qwen2.5-coder:3b",
    "DeepSeek-Coder-1.3B": "deepseek-coder:1.3b",
    "Phi-3-mini-4k": "phi3:mini"
}
```

## Troubleshooting

### Ollama Not Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model Not Found
```bash
# List available models
ollama list

# Pull missing model
ollama pull <model-name>
```

### GPU Issues
Ollama automatically uses GPU if available. Check GPU usage:
```bash
# In another terminal while running models
nvidia-smi  # For NVIDIA GPUs
```

## Next Steps

Once models are pulled:
1. Run `python3 scripts/test_models.py` to verify
2. Start the FastAPI server: `uvicorn src.api.main:app --reload`
3. Submit a test scan via `/api/scan`
