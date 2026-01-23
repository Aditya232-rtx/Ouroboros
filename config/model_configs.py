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
# TEMPORARY: Qwen2.5-Coder 3B for testing (~2.4 GB)
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

# PRODUCTION: WhiteRabbitNeo-7B (commented out)
# RED_AGENT_CONFIG = ModelConfig(
#     name="WhiteRabbitNeo-7B",
#     model_path="models/WhiteRabbitNeo-7B-v1.5a-Q4_K_M.gguf",
#     temperature=0.7,
#     max_tokens=2048,
#     n_ctx=8192,
#     top_p=0.9,
#     n_gpu_layers=35,
#     repeat_penalty=1.1,
#     stop_sequences=["```", "END_OF_POC"]
# )

# BLUE Agent Model Configuration
# TEMPORARY: DeepSeek-Coder 1.3B for testing (~2.2 GB)
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

# PRODUCTION: DeepSeek-R1-Distill-Qwen-7B (commented out)
# BLUE_AGENT_CONFIG = ModelConfig(
#     name="DeepSeek-R1-Distill-Qwen-7B",
#     model_path="models/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf",
#     temperature=0.2,
#     max_tokens=4000,
#     n_ctx=8192,
#     top_p=0.85,
#     n_gpu_layers=35,
#     repeat_penalty=1.05,
#     stop_sequences=["</think>", "END_OF_FIX"]
# )

# GOVERNANCE Agent Model Configuration
# TEMPORARY: Phi-3 Mini 3.8B for testing (~2.6 GB)
GOVERNANCE_AGENT_CONFIG = ModelConfig(
    name="Phi-3-mini-4k",
    model_path="models/Phi-3-mini-4k-instruct-q4.gguf",
    temperature=0.1,  # Very deterministic
    max_tokens=1500,
    n_ctx=4096,
    top_p=0.95,
    n_gpu_layers=22,  # Reduced for smaller model
    repeat_penalty=1.05
)

# PRODUCTION: Phi-3.5-mini (commented out)
# GOVERNANCE_AGENT_CONFIG = ModelConfig(
#     name="Phi-3.5-mini-instruct",
#     model_path="models/Phi-3.5-mini-instruct-Q6_K.gguf",
#     temperature=0.1,
#     max_tokens=1500,
#     n_ctx=4096,
#     top_p=0.95,
#     n_gpu_layers=28,
#     repeat_penalty=1.05
# )

# DOCUMENTATION Agent Model Configuration
# TEMPORARY: Sharing Phi-3 Mini with GOVERNANCE/AUDIT
DOCUMENTATION_AGENT_CONFIG = ModelConfig(
    name="Phi-3-mini-4k",
    model_path="models/Phi-3-mini-4k-instruct-q4.gguf",
    temperature=0.15,  # Consistent documentation
    max_tokens=2048,  # Reduced for smaller model
    n_ctx=4096,
    top_p=0.9,
    n_gpu_layers=22,
    repeat_penalty=1.05
)

# AUDIT Agent Model Configuration
# TEMPORARY: Sharing Phi-3 Mini with GOVERNANCE/DOCUMENTATION
AUDIT_AGENT_CONFIG = ModelConfig(
    name="Phi-3-mini-4k",
    model_path="models/Phi-3-mini-4k-instruct-q4.gguf",
    temperature=0.05,  # Fully deterministic
    max_tokens=1000,
    n_ctx=4096,
    top_p=0.99,
    n_gpu_layers=22,
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
