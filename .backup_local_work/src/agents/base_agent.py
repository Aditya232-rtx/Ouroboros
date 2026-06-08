from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError
import logging
from llama_cpp import Llama  # type: ignore

# Setup logger
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """
    Abstract Base Class for all Ouroboros Agents.
    Enforces inputs validation, execution flow, and error handling.
    """
    
    def __init__(self, model_path: str, model_config: Dict[str, Any]):
        """
        Initialize the agent with a specific model.
        
        Args:
            model_path: Path to the GGUF model file.
            model_config: Dictionary containing model configuration (context_window, temperature, etc.)
        """
        self.model_path = model_path
        self.model_config = model_config
        self.llm: Optional[Llama] = None
        self._load_model()

    def _load_model(self):
        """
        Load the Llama GGUF model.
        """
        try:
            # Check if file exists to prevent crash
            import os
            if not os.path.exists(self.model_path):
                logger.warning(f"Model file not found at {self.model_path}. Agent initialized without LLM (Mock/Dry-run mode).")
                return

            self.llm = Llama(
                model_path=self.model_path,
                n_gpu_layers=self.model_config.get("n_gpu_layers", 0),
                n_ctx=self.model_config.get("context_window", 2048),
                verbose=False
            )
            logger.info(f"Loaded model from {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_path}: {str(e)}")
            raise e

    @abstractmethod
    def validate_input(self, input_data: Any) -> BaseModel:
        """
        Validate input data using a Pydantic model.
        MUST be implemented by subclasses.
        """
        pass

    @abstractmethod
    def execute(self, input_data: BaseModel) -> Dict[str, Any]:
        """
        Main execution logic for the agent.
        MUST be implemented by subclasses.
        """
        pass

    def run(self, input_data: Any) -> Dict[str, Any]:
        """
        Public interface to run the agent.
        Handles validation, execution, and error recovery.
        """
        try:
            # 1. Validate Input
            validated_input = self.validate_input(input_data)
            
            # 2. Execute Logic
            result = self.execute(validated_input)
            
            # 3. Format Output (Implicitly handled by return type, but can enforce schema here)
            return self.format_output(result)

        except ValidationError as e:
            logger.error(f"Input validation failed: {str(e)}")
            return self.handle_error(e)
        except Exception as e:
            logger.error(f"Agent execution failed: {str(e)}")
            return self.handle_error(e)

    def format_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure output is JSON serializable and follows contracts.
        Can be overridden.
        """
        return result

    def handle_error(self, exception: Exception) -> Dict[str, Any]:
        """
        Standard error handling. Return a structure indicating failure so workflow doesn't crash.
        """
        return {
            "error": True,
            "message": str(exception),
            "type": type(exception).__name__
        }
