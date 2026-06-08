"""
Ouroboros AI - Model Loader
Loads and manages GGUF models using llama-cpp-python
"""

import logging
from pathlib import Path
from typing import Optional, Dict
from langchain_community.llms import LlamaCpp
from config.model_configs import ModelConfig, MODEL_REGISTRY
from config.settings import settings

logger = logging.getLogger(__name__)


class ModelLoader:
    """Loads and caches GGUF models"""
    
    def __init__(self):
        self.loaded_models: Dict[str, LlamaCpp] = {}
        self.models_dir = settings.models_dir
        
    def load_model(self, agent_type: str) -> LlamaCpp:
        """
        Load a model for a specific agent type
        
        Args:
            agent_type: One of 'red', 'blue', 'governance', 'documentation', 'audit'
            
        Returns:
            Loaded LlamaCpp model instance
        """
        # Return cached model if already loaded
        if agent_type in self.loaded_models:
            logger.info(f"Using cached model for {agent_type} agent")
            return self.loaded_models[agent_type]
        
        # Get model configuration
        if agent_type not in MODEL_REGISTRY:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        config = MODEL_REGISTRY[agent_type]
        model_path = self.models_dir / config.model_path
        
        # Verify model file exists
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Expected location: {model_path.absolute()}"
            )
        
        logger.info(f"Loading {config.name} model from {model_path}")
        logger.info(f"Temperature: {config.temperature}, Max tokens: {config.max_tokens}")
        
        try:
            # Load model with llama-cpp-python
            model = LlamaCpp(
                model_path=str(model_path),
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                n_ctx=config.n_ctx,
                top_p=config.top_p,
                n_gpu_layers=config.n_gpu_layers,
                repeat_penalty=config.repeat_penalty,
                stop=config.stop_sequences,
                verbose=settings.debug,
                n_threads=settings.n_threads,
                # Performance optimizations
                use_mmap=True,  # Memory-map model file
                use_mlock=True,  # Lock model in RAM
                # Batch size for prompt processing
                n_batch=512,
            )
            
            logger.info(f"Successfully loaded {config.name}")
            
            # Cache the model
            self.loaded_models[agent_type] = model
            
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model for {agent_type}: {e}")
            raise
    
    def load_all_models(self) -> Dict[str, LlamaCpp]:
        """
        Load all models for all agents
        
        Returns:
            Dictionary mapping agent types to loaded models
        """
        logger.info("Loading all models...")
        
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
        """Unload all models to free memory"""
        self.loaded_models.clear()
        logger.info("Unloaded all models")


# Global model loader instance
model_loader = ModelLoader()


def get_model(agent_type: str) -> LlamaCpp:
    """
    Convenience function to get a loaded model
    
    Args:
        agent_type: One of 'red', 'blue', 'governance', 'documentation', 'audit'
        
    Returns:
        Loaded LlamaCpp model instance
    """
    return model_loader.load_model(agent_type)
