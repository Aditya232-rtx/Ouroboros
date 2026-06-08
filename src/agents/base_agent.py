"""
Ouroboros AI - Base Agent
Abstract base class for all agents (RED, BLUE, DOCUMENTATION, GOVERNANCE, AUDIT)
"""

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, ValidationError
from langchain_community.llms import LlamaCpp

logger = logging.getLogger(__name__)


class AgentInput(BaseModel):
    """Base input validation schema"""
    pass


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
            response = self.model(prompt, **kwargs)
            self.logger.debug(f"{self.agent_id}: LLM response received")
            return response
        except Exception as e:
            self.logger.error(f"{self.agent_id}: LLM call failed: {e}")
            raise
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM JSON response
        
        Args:
            response: Raw LLM response
            
        Returns:
            Parsed JSON dictionary
        """
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.error(f"{self.agent_id}: Failed to parse JSON: {e}")
            self.logger.debug(f"Raw response: {response[:500]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")
