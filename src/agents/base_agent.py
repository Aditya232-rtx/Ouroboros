"""
Ouroboros AI - Base Agent
Abstract base class for all agents (RED, BLUE, DOCUMENTATION, GOVERNANCE, AUDIT)
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError, ConfigDict
from langchain_community.llms import LlamaCpp

logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """Base input validation schema"""
    model_config = ConfigDict(extra='ignore')


class AgentOutput(BaseModel):
    """Base output schema"""
    agent_id: str
    timestamp: str
    status: str
    errors: list[str] = []


class BaseAgent(ABC):
    """
    Abstract base class for all Ouroboros agents
    
    Each agent must implement:
    - validate_input(): Pydantic validation
    - execute(): Core logic
    - format_output(): JSON output formatting
    """
    
    def __init__(self, model: LlamaCpp, agent_id: str):
        """
        Initialize agent with its LLM model
        
        Args:
            model: Loaded LlamaCpp model instance
            agent_id: Unique identifier for this agent
        """
        self.model = model
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        self.logger.info(f"Initialized {self.agent_id} agent")
    
    @abstractmethod
    def validate_input(self, input_data: Dict[str, Any]) -> AgentInput:
        """
        Validate input data using Pydantic
        
        Args:
            input_data: Raw input dictionary
            
        Returns:
            Validated input model
            
        Raises:
            ValidationError: If input is invalid
        """
        pass
    
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's core logic
        
        Args:
            input_data: Validated input data
            
        Returns:
            Raw execution results
        """
        pass
    
    @abstractmethod
    def format_output(self, result: Dict[str, Any]) -> AgentOutput:
        """
        Format output as JSON
        
        Args:
            result: Raw execution results
            
        Returns:
            Formatted output model
        """
        pass
    
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point - coordinates validation, execution, formatting
        
        Args:
            input_data: Raw input dictionary
            
        Returns:
            Formatted output as dictionary
        """
        try:
            # Step 1: Validate input
            self.logger.info(f"{self.agent_id}: Validating input")
            validated_input = self.validate_input(input_data)
            
            # Step 2: Execute core logic
            self.logger.info(f"{self.agent_id}: Executing")
            result = await self.execute(validated_input.model_dump())
            
            # Step 3: Format output
            self.logger.info(f"{self.agent_id}: Formatting output")
            output = self.format_output(result)
            
            self.logger.info(f"{self.agent_id}: Completed successfully")
            return output.model_dump()
            
        except ValidationError as e:
            self.logger.error(f"{self.agent_id}: Input validation error: {e}")
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "errors": [str(err) for err in e.errors()]
            }
        except Exception as e:
            self.logger.error(f"{self.agent_id}: Execution error: {e}", exc_info=True)
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "errors": [str(e)]
            }
    
    def _call_llm(self, prompt: str, **kwargs) -> str:
        """
        Call the LLM with a prompt
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters for the model
            
        Returns:
            Model response as string
        """
        try:
            self.logger.debug(f"{self.agent_id}: Calling LLM")
            response = self.model.invoke(prompt, **kwargs)
            self.logger.debug(f"{self.agent_id}: LLM response received")
            return response
        except Exception as e:
            self.logger.error(f"{self.agent_id}: LLM call failed: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response with robustness for common LLM errors (trailing commas)
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Extract JSON from markdown code blocks if present
            text = response.strip()
            if "```json" in text:
                json_start = text.find("```json") + 7
                json_end = text.find("```", json_start)
                text = text[json_start:json_end].strip()
            elif "```" in text:
                json_start = text.find("```") + 3
                json_end = text.find("```", json_start)
                text = text[json_start:json_end].strip()
            
            # Simple cleanups
            text = text.lstrip("`") # Remove leading backticks if any
            
            # Try standard load
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                # Common Error 1: Trailing commas
                # Regex: Find comma followed by optional whitespace and closing brace/bracket
                import re 
                text = re.sub(r',(\s*[}\]])', r'\1', text)
                
                # Common Error 2: Missing quotes on keys (simple heuristic, not full parser)
                # This is hard to fix reliably with regex, but we can try simple cases
                
                return json.loads(text)
                
        except json.JSONDecodeError as e:
            # Common Error 3: Truncated JSON from small LLMs
            # Try to salvage by closing open brackets/braces
            try:
                salvaged = self._salvage_truncated_json(text)
                if salvaged is not None:
                    self.logger.warning(f"{self.agent_id}: Salvaged truncated JSON response")
                    return salvaged
            except Exception:
                pass
            self.logger.error(f"{self.agent_id}: Failed to parse JSON: {e}")
            self.logger.error(f"Raw response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

    def _salvage_truncated_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to recover a truncated JSON response from a small LLM.
        
        Strategy: find the last complete object in a vulnerabilities array,
        then close the array and outer object.
        """
        import re

        # Find the last complete JSON object boundary (closing brace)
        # Walk backwards to find a valid cut point
        last_brace = text.rfind("}")
        if last_brace < 0:
            return None

        # Try progressively shorter substrings ending at each '}'
        pos = last_brace
        while pos > 0:
            candidate = text[:pos + 1]
            # Count open vs close braces/brackets
            open_braces = candidate.count("{") - candidate.count("}")
            open_brackets = candidate.count("[") - candidate.count("]")
            # Close any remaining open brackets/braces
            suffix = "]" * open_brackets + "}" * open_braces
            try:
                result = json.loads(candidate + suffix)
                return result
            except json.JSONDecodeError:
                pass
            # Try the previous '}'
            pos = text.rfind("}", 0, pos)

        return None
