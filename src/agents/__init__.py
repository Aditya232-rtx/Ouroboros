"""Agents package initialization"""

from .base_agent import BaseAgent, AgentInput, AgentOutput
from .red_agent import REDAgent
from .blue_agent import BLUEAgent
from .documentation_agent import DocumentationAgent
from .governance_agent import GovernanceAgent
from .audit_agent import AuditAgent
from .research_agent import research_app  # LangGraph compiled Research Agent graph

__all__ = [
    "BaseAgent", "AgentInput", "AgentOutput",
    "REDAgent", "BLUEAgent",
    "DocumentationAgent", "GovernanceAgent", "AuditAgent",
    "research_app"
]
