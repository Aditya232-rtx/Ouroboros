"""
Ouroboros AI - Model Configurations
Model loading settings for all agents
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelConfig:
    """Configuration for a single model"""
    name: str
    model_path: str
    temperature: float
    max_tokens: int
    n_ctx: int
    top_p: float
    n_gpu_layers: int
    repeat_penalty: float = 1.0
    stop_sequences: Optional[list[str]] = None


# RED Agent Model Configuration
# Qwen2.5.1-Coder 7B Instruct (Q4_K_L)
RED_AGENT_CONFIG = ModelConfig(
    name="Qwen2.5.1-Coder-7B",
    model_path="/Users/adityajadhav/Downloads/Qwen2.5.1-Coder-7B-Instruct-Q4_K_L.gguf",
    temperature=0.7,  # Creative exploit generation
    max_tokens=2048,
    n_ctx=8192,
    top_p=0.9,
    n_gpu_layers=35,
    repeat_penalty=1.1,
    stop_sequences=["```", "END_OF_POC"]
)

# BLUE Agent Model Configuration
# Qwen2.5.1-Coder-7B-Instruct
BLUE_AGENT_CONFIG = ModelConfig(
    name="Qwen2.5.1-Coder-7B-Blue",
    model_path="/Users/adityajadhav/Downloads/Qwen2.5.1-Coder-7B-Instruct-Q4_K_L.gguf",
    temperature=0.7,  # Creative yet focused fix generation
    max_tokens=2048,
    n_ctx=8192,
    top_p=0.85,
    n_gpu_layers=35,
    repeat_penalty=1.05,
    stop_sequences=["<|im_end|>", "</s>", "END_OF_FIX"]
)

# SUPPORT AGENTS (Governance, Documentation, Audit)
# Phi-3 Mini 3.8B (~2.6 GB)
SUPPORT_AGENT_CONFIG = ModelConfig(
    name="Phi-3-mini-4k",
    model_path="models/Phi-3-mini-4k-instruct-q4.gguf",
    temperature=0.1,  # Very deterministic
    max_tokens=1500,
    n_ctx=4096,
    top_p=0.95,
    n_gpu_layers=22,
    repeat_penalty=1.05
)

# RESEARCH AGENT CONFIG
# Uses same robust model as other support agents
RESEARCH_AGENT_CONFIG = SUPPORT_AGENT_CONFIG

# Model registry
MODEL_REGISTRY = {
    "red": RED_AGENT_CONFIG,
    "blue": BLUE_AGENT_CONFIG,
    "governance": SUPPORT_AGENT_CONFIG,
    "documentation": SUPPORT_AGENT_CONFIG,
    "audit": SUPPORT_AGENT_CONFIG,
    "research": RESEARCH_AGENT_CONFIG
}
