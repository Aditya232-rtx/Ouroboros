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
# Qwen2.5-Coder 3B for testing (~2.4 GB)
RED_AGENT_CONFIG = ModelConfig(
    name="Qwen2.5-Coder-3B",
    model_path="models/Qwen2.5-Coder-3B-Instruct-abliterated-Q4_K_M.gguf",
    temperature=0.7,  # Creative exploit generation
    max_tokens=2048,
    n_ctx=4096,  # Reduced context for smaller model
    top_p=0.9,
    n_gpu_layers=25,  # Reduced for smaller model
    repeat_penalty=1.1,
    stop_sequences=["```", "END_OF_POC"]
)

# BLUE Agent Model Configuration
# DeepSeek-Coder 1.3B for testing (~2.2 GB)
BLUE_AGENT_CONFIG = ModelConfig(
    name="DeepSeek-Coder-1.3B",
    model_path="models/deepseek-coder-1.3b-instruct.Q6_K.gguf",
    temperature=0.2,  # Deterministic fix generation
    max_tokens=2048,  # Reduced for smaller model
    n_ctx=4096,  # Reduced context
    top_p=0.85,
    n_gpu_layers=25,  # Reduced for smaller model
    repeat_penalty=1.05,
    stop_sequences=["</think>", "END_OF_FIX"]
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

# Model registry
MODEL_REGISTRY = {
    "red": RED_AGENT_CONFIG,
    "blue": BLUE_AGENT_CONFIG,
    "governance": SUPPORT_AGENT_CONFIG,
    "documentation": SUPPORT_AGENT_CONFIG,
    "audit": SUPPORT_AGENT_CONFIG
}
