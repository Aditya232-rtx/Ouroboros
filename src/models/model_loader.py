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


class ModelLoader:
    """Loads and caches models via Ollama"""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.loaded_models: Dict[str, Ollama] = {}
        self.ollama_base_url = ollama_base_url
        self.model_name_mapping = {
            # Map our config model names to Ollama model names
            "Qwen2.5-Coder-3B": "ouroboros-red",
            "DeepSeek-Coder-1.3B": "ouroboros-blue",
            "Phi-3-mini-4k": "ouroboros-support"
        }
        
    def _get_ollama_model_name(self, config_name: str) -> str:
        """Convert config model name to Ollama model name"""
        return self.model_name_mapping.get(config_name, config_name.lower())
    
    def load_model(self, agent_type: str) -> Ollama:
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
            # Create Ollama model instance
            model = Ollama(
                base_url=self.ollama_base_url,
                model=ollama_model_name,
                temperature=config.temperature,
                num_predict=config.max_tokens,
                top_p=config.top_p,
                repeat_penalty=config.repeat_penalty,
                stop=config.stop_sequences,
                # Ollama-specific parameters
                num_ctx=config.n_ctx,
                num_gpu=1,  # Use GPU if available
                verbose=settings.debug,
            )
            
            logger.info(f"Successfully loaded {config.name} via Ollama")
            
            # Cache the model
            self.loaded_models[agent_type] = model
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model for {agent_type}: {e}")
            logger.error(f"Make sure Ollama is running and model '{ollama_model_name}' is pulled")
            raise
    
    def load_all_models(self) -> Dict[str, Ollama]:
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
