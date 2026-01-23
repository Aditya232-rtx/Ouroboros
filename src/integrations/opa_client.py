"""
Ouroboros AI - OPA (Open Policy Agent) Client
Policy evaluation for GOVERNANCE agent
"""

import logging
import requests
from typing import Dict, Any, List, Optional
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


class OPAClient:
    """
    Client for Open Policy Agent (OPA) policy evaluation.
    Used by GOVERNANCE agent for risk-based decision making.
    """
    
    def __init__(self, opa_url: str = None):
        """Initialize OPA client"""
        self.opa_url = opa_url or settings.opa_url
        self.policy_dir = settings.opa_policy_dir
        
    def evaluate_policy(
        self,
        policy_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate a Rego policy against input data.
        
        Args:
            policy_name: Name of the policy to evaluate
            input_data: Input data for policy evaluation
            
        Returns:
            Policy evaluation result
        """
        url = f"{self.opa_url}/v1/data/{policy_name}"
        
        try:
            response = requests.post(
                url,
                json={"input": input_data},
                timeout=5
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Policy '{policy_name}' evaluated successfully")
            
            return result.get("result", {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OPA evaluation failed: {e}")
            # Return safe default
            return {
                "allowed": False,
                "error": str(e),
                "risk_score": 100  # Max risk on failure
            }
    
    def calculate_risk_score(
        self,
        vulnerability: Dict[str, Any],
        environment: str = "production"
    ) -> Dict[str, Any]:
        """
        Calculate risk score for a vulnerability using OPA policies.
        
        Args:
            vulnerability: Vulnerability details (type, cvss, severity, etc.)
            environment: Target environment (dev|staging|production)
            
        Returns:
            Risk assessment including score and autonomy level
        """
        input_data = {
            "vulnerability": vulnerability,
            "environment": environment
        }
        
        result = self.evaluate_policy("governance/risk_calculation", input_data)
        
        return {
            "risk_score": result.get("risk_score", 50),
            "autonomy_level": result.get("autonomy_level", "require"),
            "rationale": result.get("rationale", "Policy evaluation failed"),
            "required_approvers": result.get("required_approvers", ["security_team"])
        }
    
    def prioritize_vulnerabilities(
        self,
        vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize vulnerabilities using OPA policies.
        
        Args:
            vulnerabilities: List of vulnerabilities from RED agent
            
        Returns:
            Prioritized queue with risk scores
        """
        prioritized = []
        
        for vuln in vulnerabilities:
            risk_assessment = self.calculate_risk_score(vuln)
            
            prioritized.append({
                "vulnerability_id": vuln.get("id"),
                "priority": self._calculate_priority(risk_assessment["risk_score"]),
                "risk_score": risk_assessment["risk_score"],
                "autonomy_level": risk_assessment["autonomy_level"],
                "required_approvers": risk_assessment["required_approvers"],
                "rationale": risk_assessment["rationale"]
            })
        
        # Sort by risk score (descending)
        prioritized.sort(key=lambda x: x["risk_score"], reverse=True)
        
        return prioritized
    
    def _calculate_priority(self, risk_score: float) -> int:
        """
        Convert risk score to priority number (1 = highest).
        
        Args:
            risk_score: Risk score (0-100)
            
        Returns:
            Priority (1-5)
        """
        if risk_score >= 80:
            return 1  # Critical
        elif risk_score >= 60:
            return 2  # High
        elif risk_score >= 40:
            return 3  # Medium
        elif risk_score >= 20:
            return 4  # Low
        else:
            return 5  # Info
    
    def load_policies(self):
        """
        Load Rego policies from policy directory.
        
        Note: In production, policies should be version-controlled and
        loaded into OPA server separately.
        """
        if not self.policy_dir.exists():
            logger.warning(f"Policy directory not found: {self.policy_dir}")
            return
        
        policy_files = list(self.policy_dir.glob("*.rego"))
        logger.info(f"Found {len(policy_files)} policy files")
        
        for policy_file in policy_files:
            logger.info(f"Policy: {policy_file.name}")


# Global OPA client instance
opa_client = OPAClient()
