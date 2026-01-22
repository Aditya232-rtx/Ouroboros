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


# RED Agent Model Configuration (WhiteRabbitNeo)
RED_AGENT_CONFIG = ModelConfig(
    name="WhiteRabbitNeo-7B",
    model_path="models/WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf",
    temperature=0.7,  # Creative exploit generation
    max_tokens=2048,
    n_ctx=8192,
    top_p=0.9,
    n_gpu_layers=35,
    repeat_penalty=1.1,
    stop_sequences=["```", "END_OF_POC"]
)

# BLUE Agent Model Configuration (DeepSeek-R1)
BLUE_AGENT_CONFIG = ModelConfig(
    name="DeepSeek-R1-Distill-Qwen-7B",
    model_path="models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
    temperature=0.2,  # Deterministic fix generation
    max_tokens=4000,  # Larger for chain-of-thought
    n_ctx=8192,
    top_p=0.85,
    n_gpu_layers=35,
    repeat_penalty=1.05,
    stop_sequences=["</think>", "END_OF_FIX"]
)

# GOVERNANCE Agent Model Configuration (Phi-3.5)
GOVERNANCE_AGENT_CONFIG = ModelConfig(
    name="Phi-3.5-mini-instruct",
    model_path="models/Phi-3.5-mini-instruct-Q6_K.gguf",
    temperature=0.1,  # Very deterministic
    max_tokens=1500,
    n_ctx=4096,
    top_p=0.95,
    n_gpu_layers=28,
    repeat_penalty=1.05
)

# DOCUMENTATION Agent Model Configuration (Phi-3.5)
DOCUMENTATION_AGENT_CONFIG = ModelConfig(
    name="Phi-3.5-mini-instruct",
    model_path="models/Phi-3.5-mini-instruct-Q6_K.gguf",
    temperature=0.15,  # Consistent documentation
    max_tokens=4000,  # Longer reports
    n_ctx=4096,
    top_p=0.9,
    n_gpu_layers=28,
    repeat_penalty=1.05
)

# AUDIT Agent Model Configuration (Phi-3.5)
AUDIT_AGENT_CONFIG = ModelConfig(
    name="Phi-3.5-mini-instruct",
    model_path="models/Phi-3.5-mini-instruct-Q6_K.gguf",
    temperature=0.05,  # Fully deterministic
    max_tokens=1000,
    n_ctx=4096,
    top_p=0.99,
    n_gpu_layers=28,
    repeat_penalty=1.05
)


# Model registry
MODEL_REGISTRY = {
    "red": RED_AGENT_CONFIG,
    "blue": BLUE_AGENT_CONFIG,
    "governance": GOVERNANCE_AGENT_CONFIG,
    "documentation": DOCUMENTATION_AGENT_CONFIG,
    "audit": AUDIT_AGENT_CONFIG
}
