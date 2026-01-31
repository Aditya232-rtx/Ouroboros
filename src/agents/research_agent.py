"""
Ouroboros AI - Research Agent
Autonomous threat discovery using Phi-3.5-mini + Brave Search MCP
"""

import logging
import json
import hashlib
import uuid
from typing import List, Literal, Optional, Any
from typing_extensions import TypedDict
from datetime import datetime
from pathlib import Path

from src.agents.base_agent import BaseAgent, AgentInput, AgentOutput
from src.tools.brave_mcp_client import BraveSearchClient, BraveSearchResult

# Direct Ollama import via model loader
# from langchain_ollama import ChatOllama
# import os

logger = logging.getLogger(__name__)


class ExploitBlueprint(TypedDict):
    """Blueprint for a dynamically generated exploit"""
    id: str
    cve_id: Optional[str]
    title: str
    description: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    target_technology: str
    attack_vector: Literal["NETWORK", "LOCAL", "ADJACENT", "PHYSICAL", "UNKNOWN"]
    preconditions: List[str]
    steps: List[str]
    reference_urls: List[str]
    # Dashboard-specific fields
    affected_assets: List[str]  # List of affected packages/components
    discovered_at: str  # ISO timestamp
    cvss_score: Optional[float]  # CVSS score 0-10
    solution: Optional[str]  # Patch/fix information
    details: Optional[str]  # Extended details for detail view


class ResearchAgentInput(AgentInput):
    """Input schema for Research Agent"""
    tech_stack: List[str]
    freshness: str = "30d"
    max_results_per_tech: int = 10


class ResearchAgentOutput(AgentOutput):
    """Output schema for Research Agent"""
    blueprints: List[ExploitBlueprint]
    total_discovered: int
    deduplication_count: int


class ResearchAgent(BaseAgent):
    """
    Research Agent - Autonomous threat intelligence
    
    Uses Phi-3.5-mini to analyze recent security research from Brave Search
    and generate exploit blueprints for dynamic injection into Red Agent.
    """
    
    def __init__(self, brave_client: Optional[BraveSearchClient] = None):
        """
        Initialize Research Agent with Phi-3.5-mini model.
        
        Args:
            brave_client: Brave Search MCP client (optional, will create if not provided)
        """
        # Initialize shared model via registry
        from src.models import get_model
        model = get_model("research")
        
        super().__init__(model=model, agent_id="RESEARCH")
        
        self.brave_client = brave_client or BraveSearchClient()
        
        # Deduplication cache (SHA-256 of reference URLs)
        self.seen_hashes = set()
        
        # System prompt for Phi-3.5-mini
        self.system_prompt = """You are a security research assistant specializing in vulnerability intelligence.

TASK: Analyze web search results and identify concrete, recent security vulnerabilities and exploits.

INPUT FORMAT:
- Target technology stack (list of frameworks/libraries)
- Web search results (title, snippet, URL, published date)

OUTPUT FORMAT: JSON array of exploit blueprints

EXPLOIT BLUEPRINT SCHEMA:
{
  "id": "research::<uuid4>",
  "cve_id": "CVE-2026-12345" or null,
  "title": "Brief exploit title",
  "description": "Detailed description of the vulnerability",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN",
  "target_technology": "express|django|nginx|etc",
  "attack_vector": "NETWORK|LOCAL|ADJACENT|PHYSICAL|UNKNOWN",
  "preconditions": ["List of preconditions required"],
  "steps": ["High-level exploit steps"],
  "reference_urls": ["List of reference URLs from search results"],
  "affected_assets": ["Specific package names or component identifiers affected"],
  "cvss_score": 7.5,
  "solution": "Upgrade to version X or apply patch Y" or null,
  "details": "Extended technical details, PoC links, impact analysis"
}

FILTERING RULES:
1. ONLY include exploits/vulnerabilities from the last ~30 days
2. ONLY include items with concrete PoC code or detailed writeups
3. Skip blog posts, news articles, or general security advice
4. Prioritize GitHub repositories, security advisories, and exploit databases
5. Ensure target_technology matches the input tech stack
6. Extract CVSS scores from search results if available
7. Identify specific package/component names for affected_assets

OUTPUT: Return ONLY a valid JSON array. No markdown, no explanations."""
    
    def validate_input(self, input_data: dict) -> ResearchAgentInput:
        """Validate Research Agent input"""
        return ResearchAgentInput(**input_data)
    
    async def execute(self, input_data: dict) -> dict:
        """
        Execute Research Agent threat hunting.
        
        Steps:
        1. Generate targeted search queries for each technology
        2. Call Brave Search MCP for each query
        3. Analyze results with Phi-3.5-mini
        4. Deduplicate and return blueprints
        """
        validated_input = self.validate_input(input_data)
        
        self.logger.info(f"Starting threat hunt for {len(validated_input.tech_stack)} technologies")
        
        try:
            # Step 1: Hunt for new threats
            blueprints = await self.hunt_new_threats(
                tech_stack=validated_input.tech_stack,
                freshness=validated_input.freshness,
                max_results=validated_input.max_results_per_tech
            )
            
            # Step 2: Deduplicate
            unique_blueprints = self._deduplicate_blueprints(blueprints)
            
            dedup_count = len(blueprints) - len(unique_blueprints)
            
            self.logger.info(
                f"Discovered {len(unique_blueprints)} unique threats "
                f"({dedup_count} duplicates filtered)"
            )
            
            return {
                "blueprints": unique_blueprints,
                "total_discovered": len(unique_blueprints),
                "deduplication_count": dedup_count
            }
            
        except Exception as e:
            self.logger.error(f"Research Agent execution failed: {e}", exc_info=True)
            return {
                "blueprints": [],
                "total_discovered": 0,
                "deduplication_count": 0,
                "error": str(e)
            }
    
    async def hunt_new_threats(
        self,
        tech_stack: List[str],
        freshness: str = "30d",
        max_results: int = 10
    ) -> List[ExploitBlueprint]:
        """
        Hunt for new threats targeting the given technology stack.
        
        Args:
            tech_stack: List of technologies to research
            freshness: Time window for search results
            max_results: Maximum results per technology
            
        Returns:
            List of ExploitBlueprint objects
        """
        all_search_results = []
        
        # Step 1: Generate queries and search
        for tech in tech_stack:
            self.logger.info(f"Researching threats for {tech}...")
            
            # Generate 3-5 focused queries per technology
            queries = self._generate_queries(tech)
            
            for query in queries:
                try:
                    results = await self.brave_client.search(
                        query=query,
                        freshness=freshness,
                        limit=max_results
                    )
                    
                    all_search_results.extend(results)
                    
                except Exception as e:
                    self.logger.warning(f"Search failed for query '{query}': {e}")
                    continue
        
        if not all_search_results:
            self.logger.warning("No search results found")
            return []
        
        # Step 2: Analyze with Phi-3.5-mini
        blueprints = await self.generate_blueprints(tech_stack, all_search_results)
        
        return blueprints
    
    def _generate_queries(self, tech: str) -> List[str]:
        """
        Generate focused search queries for a technology.
        
        Args:
            tech: Technology name
            
        Returns:
            List of search query strings
        """
        current_year = datetime.now().year
        
        return [
            f"Exploit PoC {tech} {current_year} site:github.com",
            f"Zero-day {tech} RCE writeup {current_year}",
            f"{tech} vulnerability PoC exploit {current_year}",
            f"{tech} security advisory {current_year} CVE",
            f"{tech} critical vulnerability disclosure {current_year}"
        ]
    
    async def generate_blueprints(
        self,
        tech_stack: List[str],
        search_results: List[BraveSearchResult]
    ) -> List[ExploitBlueprint]:
        """
        Generate exploit blueprints from search results using Phi-3.5-mini.
        
        Args:
            tech_stack: Target technology stack
            search_results: Search results from Brave
            
        Returns:
            List of ExploitBlueprint objects
        """
        # Construct prompt
        prompt = f"""{self.system_prompt}

TARGET TECHNOLOGY STACK:
{json.dumps(tech_stack, indent=2)}

WEB SEARCH RESULTS:
{json.dumps([
    {
        "title": r["title"],
        "snippet": r["snippet"],
        "url": r["url"],
        "published_at": r.get("published_at", "unknown")
    }
    for r in search_results
], indent=2)}

Analyze these search results and generate exploit blueprints. Output JSON array only."""
        
        try:
            # Call Phi-3.5-mini
            self.logger.info("Analyzing search results with Phi-3.5-mini...")
            response = self._call_llm(prompt)
            
            # Parse JSON response
            blueprints_data = self._parse_json_response(response)
            
            # Handle cases where response is a dict with 'blueprints' key
            if isinstance(blueprints_data, dict):
                blueprints_data = blueprints_data.get("blueprints", [])
            
            # Convert to ExploitBlueprint objects
            blueprints = []
            for i, bp_data in enumerate(blueprints_data):
                try:
                    # Ensure ID is present
                    if "id" not in bp_data:
                        bp_data["id"] = f"research::{uuid.uuid4()}"
                    
                    # Validate required fields
                    blueprint = self._validate_blueprint(bp_data)
                    if blueprint:
                        blueprints.append(blueprint)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to parse blueprint {i+1}: {e}")
                    continue
            
            self.logger.info(f"Generated {len(blueprints)} blueprints from LLM analysis")
            return blueprints
            
        except Exception as e:
            self.logger.error(f"Blueprint generation failed: {e}", exc_info=True)
            return []
    
    def _validate_blueprint(self, bp_data: dict) -> Optional[ExploitBlueprint]:
        """
        Validate and normalize a blueprint object.
        
        Args:
            bp_data: Raw blueprint data from LLM
            
        Returns:
            Validated ExploitBlueprint or None if invalid
        """
        try:
            # Required fields
            required = ["id", "title", "description", "target_technology"]
            for field in required:
                if field not in bp_data or not bp_data[field]:
                    self.logger.warning(f"Blueprint missing required field: {field}")
                    return None
            
            # Normalize severity
            severity = bp_data.get("severity", "UNKNOWN").upper()
            if severity not in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]:
                severity = "UNKNOWN"
            
            # Normalize attack vector
            attack_vector = bp_data.get("attack_vector", "UNKNOWN").upper()
            if attack_vector not in ["NETWORK", "LOCAL", "ADJACENT", "PHYSICAL", "UNKNOWN"]:
                attack_vector = "UNKNOWN"
            
            # Construct validated blueprint
            blueprint: ExploitBlueprint = {
                "id": bp_data["id"],
                "cve_id": bp_data.get("cve_id"),
                "title": bp_data["title"],
                "description": bp_data["description"],
                "severity": severity,
                "target_technology": bp_data["target_technology"],
                "attack_vector": attack_vector,
                "preconditions": bp_data.get("preconditions", []),
                "steps": bp_data.get("steps", []),
                "reference_urls": bp_data.get("reference_urls", []),
                # Dashboard fields with defaults
                "affected_assets": bp_data.get("affected_assets", [bp_data["target_technology"]]),
                "discovered_at": bp_data.get("discovered_at", datetime.now().isoformat()),
                "cvss_score": bp_data.get("cvss_score"),
                "solution": bp_data.get("solution"),
                "details": bp_data.get("details", bp_data["description"])
            }
            
            return blueprint
            
        except Exception as e:
            self.logger.warning(f"Blueprint validation failed: {e}")
            return None
    
    def _deduplicate_blueprints(self, blueprints: List[ExploitBlueprint]) -> List[ExploitBlueprint]:
        """
        Deduplicate blueprints using SHA-256 hash of reference URLs.
        
        Args:
            blueprints: List of blueprints to deduplicate
            
        Returns:
            List of unique blueprints
        """
        unique = []
        
        for bp in blueprints:
            # Compute hash from sorted reference URLs
            urls = sorted(bp.get("reference_urls", []))
            url_string = "|".join(urls)
            hash_value = hashlib.sha256(url_string.encode()).hexdigest()
            
            if hash_value not in self.seen_hashes:
                self.seen_hashes.add(hash_value)
                unique.append(bp)
        
        return unique
    
    async def write_dynamic_exploits_module(self, blueprints: List[ExploitBlueprint]) -> int:
        """
        Regenerate src/security/tools/dynamic_exploits.py from blueprints.
        
        Args:
            blueprints: List of exploit blueprints to generate
            
        Returns:
            Number of exploit classes written
        """
        module_path = Path("src/security/tools/dynamic_exploits.py")
        changelog_path = Path("research_findings/EXPLOIT_CHANGELOG.md")
        
        try:
            # Generate module content
            content = self._generate_module_content(blueprints)
            
            # Write to file
            module_path.parent.mkdir(parents=True, exist_ok=True)
            module_path.write_text(content, encoding="utf-8")
            
            # Also write JSON for API consumption
            await self.write_vulnerabilities_json(blueprints)
            
            # Update changelog
            self._update_changelog(changelog_path, blueprints)
            
            self.logger.info(f"Generated dynamic exploits module with {len(blueprints)} exploits")
            return len(blueprints)
            
        except Exception as e:
            self.logger.error(f"Failed to write dynamic exploits module: {e}", exc_info=True)
            return 0
    
    async def write_vulnerabilities_json(self, blueprints: List[ExploitBlueprint]) -> bool:
        """
        Write vulnerability data to JSON for API consumption.
        
        Args:
            blueprints: List of exploit blueprints
            
        Returns:
            bool: Success status
        """
        json_path = Path("research_findings/vulnerabilities.json")
        
        try:
            # Ensure directory exists
            json_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert blueprints to JSON-serializable format
            vulnerabilities = []
            for bp in blueprints:
                vuln_data = dict(bp)  # Convert TypedDict to regular dict
                vulnerabilities.append(vuln_data)
            
            # Write JSON file
            with json_path.open('w', encoding='utf-8') as f:
                json.dump({
                    "last_updated": datetime.now().isoformat(),
                    "total_count": len(vulnerabilities),
                    "vulnerabilities": vulnerabilities
                }, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Wrote {len(vulnerabilities)} vulnerabilities to {json_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to write vulnerabilities JSON: {e}", exc_info=True)
            return False
    
    def _generate_module_content(self, blueprints: List[ExploitBlueprint]) -> str:
        """
        Generate Python module content from blueprints.
        
        Args:
            blueprints: List of exploit blueprints
            
        Returns:
            Python module content as string
        """
        # Header and imports
        lines = [
            '# GENERATED BY RESEARCH AGENT',
            '# DO NOT EDIT MANUALLY – CHANGES WILL BE OVERWRITTEN',
            '',
            'from typing import List',
            'from src.security.tools.executor import PentestExecutor',
            '',
            '',
            'class DynamicExploit:',
            '    """',
            '    Base class for research-generated exploits.',
            '    All subclasses must implement execute() using only sandbox-safe APIs.',
            '    """',
            '    ',
            '    id: str',
            '    cve_id: str | None',
            '    target_technology: str',
            '    severity: str  # CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN',
            '    ',
            '    def execute(self, executor: "PentestExecutor", target: str) -> dict:',
            '        """',
            '        Run exploit inside the sandbox.',
            '        ',
            '        Returns:',
            '            {',
            '                "success": bool,',
            '                "evidence": str,',
            '            }',
            '        """',
            '        raise NotImplementedError',
            '',
            '',
            'DYNAMIC_EXPLOITS: List[DynamicExploit] = []',
            ''
        ]
        
        # Generate exploit classes
        for i, bp in enumerate(blueprints):
            class_name = f"Exploit_{bp['id'].replace('research::', '').replace('-', '_')[:16]}"
            
            lines.extend([
                '',
                f'class {class_name}(DynamicExploit):',
                f'    """',
                f'    {bp["title"]}',
                f'    ',
                f'    {bp["description"][:200]}...',
                f'    """',
                f'    id = "{bp["id"]}"',
                f'    cve_id = "{bp["cve_id"]}" if "{bp["cve_id"]}" != "None" else None',
                f'    target_technology = "{bp["target_technology"]}"',
                f'    severity = "{bp["severity"]}"',
                '    ',
                '    def execute(self, executor: "PentestExecutor", target: str) -> dict:',
                '        """',
                f'        Execute exploit for {bp["title"]}.',
                '        ',
                '        SAFETY: Only uses executor.run_command() and executor.http_request().',
                '        NO direct os, subprocess, or file operations.',
                '        """',
                '        # TODO: Implement actual exploit logic',
                '        # For now, return a placeholder',
                '        return {',
                '            "success": False,',
                f'            "evidence": "Exploit {bp["id"]} not yet implemented",',
                f'            "blueprint_title": "{bp["title"]}"',
                '        }',
                '',
                '',
                f'DYNAMIC_EXPLOITS.append({class_name}())',
                ''
            ])
        
        return '\n'.join(lines)
    
    def _update_changelog(self, changelog_path: Path, blueprints: List[ExploitBlueprint]) -> None:
        """
        Update the exploit changelog with new discoveries.
        
        Args:
            changelog_path: Path to EXPLOIT_CHANGELOG.md
            blueprints: List of newly discovered exploit blueprints
        """
        try:
            # Ensure directory exists
            changelog_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing content or create new
            if changelog_path.exists():
                existing_content = changelog_path.read_text(encoding='utf-8')
            else:
                existing_content = "# Dynamic Exploits Change Log\n\n---\n\n"
            
            # Create new entry
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M UTC')
            entry_lines = [
                f"### Update: {timestamp}",
                f"- **Exploits Added**: {len(blueprints)}",
                f"- **Status**: Automatic research cycle completed",
                f"- **Discoveries**:"
            ]
            
            for bp in blueprints:
                cve = bp.get('cve_id', 'N/A')
                severity = bp.get('severity', 'UNKNOWN')
                title = bp.get('title', 'Unknown')
                entry_lines.append(f"  - [{severity}] {title} ({cve})")
            
            entry_lines.extend(["", "---", ""])
            
            # Insert before "## Next Update" or append
            new_entry = '\n'.join(entry_lines)
            if "## Next Update" in existing_content:
                parts = existing_content.split("## Next Update")
                updated_content = parts[0] + new_entry + "\n## Next Update" + parts[1]
            else:
                updated_content = existing_content + "\n" + new_entry
            
            # Write back
            changelog_path.write_text(updated_content, encoding='utf-8')
            self.logger.info(f"Updated changelog: {changelog_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to update changelog: {e}")
    
    async def export_to_markdown(self, blueprints: List[ExploitBlueprint], output_path: str) -> bool:
        """
        Export exploit blueprints to a markdown file (fallback when dynamic_exploits.py fails).
        
        Args:
            blueprints: List of exploit blueprints to export
            output_path: Path to output markdown file
            
        Returns:
            bool: True if export successful
        """
        try:
            lines = [
                f"# Research Agent Findings - {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}",
                "",
                f"**Total Discovered**: {len(blueprints)}",
                "",
                "---",
                ""
            ]
            
            for i, bp in enumerate(blueprints, 1):
                lines.extend([
                    f"## {i}. {bp['title']}",
                    "",
                    f"- **ID**: `{bp['id']}`",
                    f"- **CVE**: {bp['cve_id'] or 'N/A'}",
                    f"- **Severity**: **{bp['severity']}**",
                    f"- **Target Technology**: `{bp['target_technology']}`",
                    f"- **Attack Vector**: {bp['attack_vector']}",
                    "",
                    "### Description",
                    bp['description'],
                    ""
                ])
                
                if bp.get('preconditions'):
                    lines.append("### Preconditions")
                    for pre in bp['preconditions']:
                        lines.append(f"- {pre}")
                    lines.append("")
                
                if bp.get('steps'):
                    lines.append("### Exploit Steps")
                    for idx, step in enumerate(bp['steps'], 1):
                        lines.append(f"{idx}. {step}")
                    lines.append("")
                
                if bp.get('reference_urls'):
                    lines.append("### References")
                    for url in bp['reference_urls']:
                        lines.append(f"- [{url}]({url})")
                    lines.append("")
                
                lines.append("---")
                lines.append("")
            
            # Write to file
            Path(output_path).write_text('\n'.join(lines), encoding='utf-8')
            
            self.logger.info(f"Exported {len(blueprints)} blueprints to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export markdown: {e}", exc_info=True)
            return False
    
    def format_output(self, result: dict) -> ResearchAgentOutput:
        """Format Research Agent output"""
        return ResearchAgentOutput(
            agent_id=self.agent_id,
            timestamp=datetime.now().isoformat(),
            status="success" if result.get("blueprints") else "error",
            blueprints=result.get("blueprints", []),
            total_discovered=result.get("total_discovered", 0),
            deduplication_count=result.get("deduplication_count", 0)
        )
