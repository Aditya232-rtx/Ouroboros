from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import logging
import asyncio
import json
from datetime import datetime
import uuid

from src.agents.base_agent import BaseAgent
from config.settings import get_settings
from src.tools.pyrit_orchestrator import PyRITOrchestrator

settings = get_settings()
logger = logging.getLogger(__name__)

# --- Pydantic Models for Input/Output Contract ---

class RedAgentTarget(BaseModel):
    repo: str
    commit_sha: Optional[str] = None
    branch: str = "main"
    environment: str = "dev"
    scan_profile: str = "standard"

class RedAgentConfig(BaseModel):
    scanning_tools: List[str] = ["semgrep", "checkov"]
    severity_filter: str = "medium"

class RedAgentInput(BaseModel):
    target: RedAgentTarget
    config: Optional[RedAgentConfig] = Field(default_factory=RedAgentConfig)
    context: Optional[Dict[str, Any]] = None

    @validator("target")
    def validate_repo_url(cls, v):
        # Basic validation to ensure it looks like a repo path or URL
        if not v.repo or "github.com" not in v.repo:
            # Allow local paths for testing, but warn
            pass
        return v

class RedAgent(BaseAgent):
    """
    RED Agent: Offensive Security
    - Orchestrates scans via PyRIT
    - Generates PoCs using WhiteRabbitNeo
    """

    def __init__(self, model_path: str = None, model_config: Dict[str, Any] = None):
        # Use settings defaults if not provided
        model_path = model_path or settings.RED_AGENT_MODEL
        super().__init__(model_path=model_path, model_config=model_config or {})
        self.orchestrator = PyRITOrchestrator()

    def validate_input(self, input_data: Any) -> RedAgentInput:
        if isinstance(input_data, dict):
            return RedAgentInput(**input_data)
        if isinstance(input_data, RedAgentInput):
            return input_data
        raise ValueError("Input must be a dictionary or RedAgentInput object")

    def execute(self, input_data: RedAgentInput) -> Dict[str, Any]:
        """
        Synchronous wrapper for the async scan logic (BaseAgent.execute is sync).
        """
        return asyncio.run(self._execute_async(input_data))

    async def _execute_async(self, input_data: RedAgentInput) -> Dict[str, Any]:
        logger.info(f"Starting Red Agent Scan on {input_data.target.repo}")
        
        # 1. Run Scans (Discovery)
        # In a real scenario, we'd clone the repo first. 
        # For V1 MVP, we assume local path or pre-cloned path is passed in 'repo' for now,
        # or we handle cloning in a separate step before calling execute.
        # Let's assume input_data.target.repo is a local path to scanned code for this implementation step.
        target_path = input_data.target.repo
        
        findings = await self.orchestrator.run_scan(
            target_path=target_path,
            tools=input_data.config.scanning_tools
        )
        
        logger.info(f"Scan complete. Found {len(findings)} issues.")

        # 2. Analyze & Generate PoCs (LLM)
        vulnerabilities = []
        for index, finding in enumerate(findings):
            # Filtering based on severity
            # (Simple string check for MVP, standard would be numeric mapping)
            if input_data.config.severity_filter == "high" and finding["severity"].lower() not in ["high", "critical"]:
                continue

            # LLM Enrichment
            enriched_vuln = self._enrich_finding_with_llm(finding, index)
            vulnerabilities.append(enriched_vuln)

        # 3. Format Output
        return {
            "scan_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "vulnerabilities": vulnerabilities,
            "statistics": {
                "total_vulnerabilities": len(vulnerabilities),
                "tools_used": input_data.config.scanning_tools,
                "raw_findings_count": len(findings)
            },
            "errors": []
        }

    def _enrich_finding_with_llm(self, finding: Dict[str, Any], index: int) -> Dict[str, Any]:
        """
        Use WhiteRabbitNeo to generate PoC and better descriptions.
        """
        # Default/Fallback structure
        vuln_id = f"RED-{int(datetime.utcnow().timestamp())}-{index}"
        
        enriched = {
            "id": vuln_id,
            "type": finding["type"],
            "severity": finding["severity"],
            "location": finding["location"],
            "description": finding["description"],
            "poc_code": f"# PoC generation for {finding['type']} not available in dry-run",
            "confidence": 0.8, # Placeholder
            "tools_detected_by": [finding["tool"]]
        }

        if self.llm:
            # Construct Prompt
            prompt = f"""
            You are WhiteRabbitNeo, an offensive security AI.
            Analyze this vulnerability finding and generate a Python Proof-of-Concept (PoC) exploit.

            Vulnerability: {finding['type']}
            Description: {finding['description']}
            File: {finding['location']['file']}
            Line: {finding['location']['line']}

            Output JSON only:
            {{
                "poc_code": "code string",
                "technical_analysis": "string"
            }}
            """
            
            try:
                # LLM Inference
                output = self.llm.create_completion(
                    prompt=prompt,
                    max_tokens=600,
                    stop=["```"],
                    temperature=0.3
                )
                text = output['choices'][0]['text']
                # Basic parsing (JSON extraction would be more robust)
                # For V1 MVP, just storing the text if parsing fails
                enriched["poc_code"] = text.strip()
            except Exception as e:
                logger.error(f"LLM Generation failed: {e}")

        return enriched
