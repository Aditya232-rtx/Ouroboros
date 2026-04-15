"""
Ouroboros AI - Model Loader (Ollama)
Loads and manages models using Ollama API
"""

import logging
from typing import Optional, Dict, Any
from langchain_community.llms import Ollama
from config.model_configs import ModelConfig, MODEL_REGISTRY
from config.settings import settings

logger = logging.getLogger(__name__)


class RawOllamaClient:
    """Robust, dependency-free Ollama client"""
    def __init__(self, base_url: str, model: str, **kwargs):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.kwargs = kwargs
        import requests
        self.session = requests.Session()

    def invoke(self, prompt: str, **kwargs) -> str:
        """Invoke model with prompt"""
        import requests
        import json
        
        url = f"{self.base_url}/api/generate"
        
        # Merge defaults with run-time kwargs
        params = {**self.kwargs, **kwargs}
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": params.get("temperature", 0.7),
                "num_predict": params.get("num_predict", 2048),
                "top_p": params.get("top_p", 0.9),
                "repeat_penalty": params.get("repeat_penalty", 1.1),
                "num_ctx": params.get("num_ctx", 4096),
                "stop": params.get("stop", [])
            }
        }
        
        try:
            response = self.session.post(url, json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            logger.error(f"Ollama raw request failed: {e}")
            raise RuntimeError(f"Ollama failed: {e}")

    def __call__(self, prompt: str, **kwargs) -> str:
        return self.invoke(prompt, **kwargs)


class ModelLoader:
    """Loads and caches models via Ollama"""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.loaded_models: Dict[str, RawOllamaClient] = {}
        self.ollama_base_url = ollama_base_url
        
        # User requested strict SINGLETON model for all agents.
        # All agents scan use the exact same model name.
        # "ouroboros-blue" tag is now mapped to Qwen2.5.1-Coder-7B-Instruct-Q4_K_L.gguf
        self.shared_model_name = "ouroboros-blue" 
        
        self.model_name_mapping = {
            # ALL agents map to the SAME model as per user strict instruction
            "WhiteRabbitNeo-7B": self.shared_model_name,
            "Qwen2.5-Coder-3B": self.shared_model_name,
            "Qwen2.5-Coder-3B-Blue": self.shared_model_name,
            "Qwen2.5.1-Coder-7B": self.shared_model_name,
            "Qwen2.5.1-Coder-7B-Blue": self.shared_model_name,
            "DeepSeek-Coder-1.3B": self.shared_model_name,
            "Phi-3-mini-4k": self.shared_model_name,
            "red": self.shared_model_name,
            "blue": self.shared_model_name,
            "governance": self.shared_model_name,
            "audit": self.shared_model_name,
            "documentation": self.shared_model_name
        }
        
    def _get_ollama_model_name(self, config_name: str) -> str:
        """Convert config model name to Ollama model name - ALWAYS returns shared model"""
        return self.shared_model_name
    
    def load_model(self, agent_type: str) -> RawOllamaClient:
        """
        Load the shared model for any agent.
        Since we enforce a singleton, this returns the SAME instance for everyone.
        """
        # Return cached model if already loaded (keyed by 'shared')
        if "shared" in self.loaded_models:
            logger.info(f"Using cached SHARED model for {agent_type} agent")
            return self.loaded_models["shared"]
        
        # Determine model name (it's always the shared one)
        ollama_model_name = self.shared_model_name
        
        # Get config just for parameters (use Red as default baseline if unknown)
        if agent_type in MODEL_REGISTRY:
            config = MODEL_REGISTRY[agent_type]
        else:
            # Fallback for generic types
            config = MODEL_REGISTRY.get("red") 
            
        logger.info(f"Loading SHARED model {ollama_model_name} via Ollama for proper singleton behavior")
        logger.info(f"Initial params - Temp: {config.temperature}, Ctx: {config.n_ctx}")
        
        try:
            # Create Raw Ollama client with KEEP_ALIVE
            # We add keep_alive to the kwargs so it's sent with every generate request
            model = RawOllamaClient(
                base_url=self.ollama_base_url,
                model=ollama_model_name,
                temperature=config.temperature,
                num_predict=config.max_tokens,
                top_p=config.top_p,
                repeat_penalty=config.repeat_penalty,
                stop_sequences=config.stop_sequences,
                num_ctx=config.n_ctx,
                keep_alive=-1  # Infinite keep alive
            )
            
            # Explicitly set keep_alive in kwargs to ensure it persists
            model.kwargs["keep_alive"] = -1
            
            logger.info(f"Successfully loaded shared model {ollama_model_name}")
            
            # Cache under 'shared' key AND the agent specific key to be safe, 
            # but 'shared' is the source of truth
            self.loaded_models["shared"] = model
            self.loaded_models[agent_type] = model
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load shared model: {e}")
            raise
    
    def load_all_models(self) -> Dict[str, RawOllamaClient]:
        """
        Load the single shared model
        """
        logger.info("Loading shared model via Ollama...")
        self.load_model("red") # Loading one loads for all
        return self.loaded_models
    
    def unload_model(self, agent_type: str):
        """Unload a specific model to free memory"""
        if agent_type in self.loaded_models:
            del self.loaded_models[agent_type]
            logger.info(f"Unloaded {agent_type} model")
    
    def unload_all_models(self):
        """Unload all models"""
        self.loaded_models.clear()
        logger.info("Unloaded all models")


# Global model loader instance
model_loader = ModelLoader()


def get_model(agent_type: str, **runtime_params):
    """
    Convenience function to get a loaded model
    
    Args:
        agent_type: One of 'red', 'blue', 'governance', 'documentation', 'audit'
        **runtime_params: Optional parameters like temperature, top_p, repeat_penalty
        
    Returns:
        Loaded Ollama model instance
    """
    model = model_loader.load_model(agent_type)
    
    # Apply runtime parameters if provided
    if runtime_params:
        model.kwargs.update(runtime_params)
        logger.info(f"Applied runtime params to {agent_type}: {runtime_params}")
    
    return model
