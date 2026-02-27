#!/usr/bin/env python3
"""
Evasion Tools - Blue Team Analysis for Stealth
Uses NeuroSploit's Blue Team persona to critique and improve Red Team plans.
"""

import logging
from typing import Dict, Any
from pathlib import Path
from src.models import get_model

logger = logging.getLogger(__name__)

class EvasionTools:
    """Blue Team / Evasion capabilities"""
    
    def __init__(self, llm_client: Any = None):
        self.llm = llm_client # Reuse the existing LLM client if passed
        self.system_prompt = self._load_blue_team_prompt()
        
    def _load_blue_team_prompt(self) -> str:
        try:
            # Try to load the harvested prompt
            path = Path("src/resources/agents/red_agent/prompts/blue_team_agent.md")
            if path.exists():
                return path.read_text()
        except OSError: pass
        return "You are an expert Blue Team analyst. detection logic and SIEM rules."

    async def check_stealth(self, plan: Dict, llm_callable) -> Dict:
        """
        Ask the Blue Team persona to critique the attack plan for stealth.
        """
        logger.info("Requesting Stealth Check from Blue Team persona...")
        
        prompt = f"""{self.system_prompt}

CRITICAL TASK: Analyze this Red Team attack plan for detection risks.

ATTACK PLAN:
{plan}

Provide a JSON response with:
1. "detected": true/false (Will this trigger standard SIEM alerts?)
2. "risk_score": 1-10 (10 = Noisy/Guaranteed detection)
3. "improvements": List of flags/changes to make it stealthier (e.g. "Use -T2", "Fragment packets")
"""
        try:
            # We assume llm_callable is a function that takes string -> string
            response = llm_callable(prompt)
            return response # Should be parsed JSON ideally, but raw string fine for now
        except Exception as e:
            logger.error(f"Stealth check failed: {e}")
            return {"error": str(e)}

    def apply_evasion(self, command: str, technique: str) -> str:
        """Apply simple evasion techniques to strings/commands"""
        if technique == "base64":
            import base64
            return base64.b64encode(command.encode()).decode()
        return command
