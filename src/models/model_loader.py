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
        self.model_name_mapping = {
            # Map our config model names to Ollama model names
            "WhiteRabbitNeo-7B": "whiterabbitneo",
            "Qwen2.5-Coder-3B": "ouroboros-red",
            "Qwen2.5-Coder-3B-Blue": "ouroboros-blue",
            "DeepSeek-Coder-1.3B": "ouroboros-blue",
            "Phi-3-mini-4k": "ouroboros-support"
        }
        
    def _get_ollama_model_name(self, config_name: str) -> str:
        """Convert config model name to Ollama model name"""
        return self.model_name_mapping.get(config_name, config_name.lower())
    
    def load_model(self, agent_type: str) -> RawOllamaClient:
        """
        Load a model for a specific agent type using Ollama
        
        Args:
            agent_type: One of 'red', 'blue', 'governance', 'documentation', 'audit'
            
        Returns:
            Loaded Ollama model instance
        """
        # Return cached model if already loaded
        if agent_type in self.loaded_models:
            logger.info(f"Using cached model for {agent_type} agent")
            return self.loaded_models[agent_type]
        
        # Get model configuration
        if agent_type not in MODEL_REGISTRY:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        config = MODEL_REGISTRY[agent_type]
        ollama_model_name = self._get_ollama_model_name(config.name)
        
        logger.info(f"Loading {config.name} via Ollama (model: {ollama_model_name})")
        logger.info(f"Temperature: {config.temperature}, Max tokens: {config.max_tokens}")
        
        try:
            # Create Raw Ollama client
            model = RawOllamaClient(
                base_url=self.ollama_base_url,
                model=ollama_model_name,
                temperature=config.temperature,
                num_predict=config.max_tokens,
                top_p=config.top_p,
                repeat_penalty=config.repeat_penalty,
                stop_sequences=config.stop_sequences,
                num_ctx=config.n_ctx
            )
            
            logger.info(f"Successfully loaded {config.name} via Ollama")
            
            # Cache the model
            self.loaded_models[agent_type] = model
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model for {agent_type}: {e}")
            logger.error(f"Make sure Ollama is running and model '{ollama_model_name}' is pulled")
            raise
    
    def load_all_models(self) -> Dict[str, RawOllamaClient]:
        """
        Load all models for all agents
        
        Returns:
            Dictionary mapping agent types to loaded models
        """
        logger.info("Loading all models via Ollama...")
        
        for agent_type in MODEL_REGISTRY.keys():
            try:
                self.load_model(agent_type)
            except Exception as e:
                logger.error(f"Failed to load {agent_type} model: {e}")
                raise
        
        logger.info(f"Successfully loaded {len(self.loaded_models)} models")
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


def get_model(agent_type: str) -> Ollama:
    """
    Convenience function to get a loaded model
    
    Args:
        agent_type: One of 'red', 'blue', 'governance', 'documentation', 'audit'
        
    Returns:
        Loaded Ollama model instance
    """
    return model_loader.load_model(agent_type)
