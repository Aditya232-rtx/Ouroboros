from llama_cpp import Llama
import os
import logging
from typing import Dict, Any, Optional
from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class ModelLoader:
    """
    Centralized loader for GGUF models.
    Manages singleton instances to save memory (though V1 runs agents sequentially mostly).
    """

    _instances: Dict[str, Llama] = {}

    @classmethod
    def load_model(cls, model_name: str, config: Dict[str, Any]) -> Optional[Llama]:
        """
        Load a GGUF model if not already loaded.
        
        Args:
            model_name: Filename of the model (e.g. 'whiterabbitneo...gguf')
            config: Configuration dict (gpu_layers, context_window, etc.)
        """
        # Full path construction
        model_path = os.path.join(settings.MODEL_DIR, model_name)
        
        # Check cache
        if model_path in cls._instances:
            return cls._instances[model_path]

        # Verify existence
        if not os.path.exists(model_path):
            logger.error(f"Model file {model_path} does not exist. Cannot load.")
            # In V1 setup, we might return None and let Agent handle it (e.g. fail or mock)
            return None

        try:
            logger.info(f"Loading model: {model_name}...")
            llm = Llama(
                model_path=model_path,
                n_gpu_layers=config.get("n_gpu_layers", 0),
                n_ctx=config.get("context_window", 4096),
                verbose=True
            )
            cls._instances[model_path] = llm
            logger.info(f"Model {model_name} loaded successfully.")
            return llm
        except Exception as e:
            logger.critical(f"Failed to load VLLM model {model_name}: {e}")
            raise e

    @classmethod
    def unload_model(cls, model_name: str):
        """
        Unload a model to free VRAM (crucial for consumer hardware).
        """
        model_path = os.path.join(settings.MODEL_DIR, model_name)
        if model_path in cls._instances:
            del cls._instances[model_path]
            import gc
            gc.collect()
            logger.info(f"Unloaded model {model_name}")
