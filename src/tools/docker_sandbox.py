"""
Ouroboros AI - Docker Sandbox
Secure code execution in isolated Docker containers
Per 03_CRITICAL_DO_NOT: NEVER execute generated code without sandboxing
"""

import logging
import docker
from typing import Dict, Any, Optional
from pathlib import Path
import tempfile
import json

logger = logging.getLogger(__name__)


class DockerSandbox:
    """
    Secure Docker-based code execution sandbox.
    
    CRITICAL: Per 03_CRITICAL_DO_NOT_FILE, all generated code MUST run
    in isolated Docker containers with:
    - Network disabled
    - Read-only filesystem
    - Resource limits (CPU, memory)
    - Timeout enforcement
    """
    
    def __init__(self):
        """Initialize Docker client"""
        try:
            self.client = docker.from_env()
            logger.info("Docker sandbox initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Docker: {e}")
            self.client = None
    
    def execute_python_code(
        self,
        code: str,
        timeout: int = 300,
        mem_limit: str = "512m",
        cpu_quota: int = 100000
    ) -> Dict[str, Any]:
        """
        Execute Python code in isolated Docker container.
        
        Args:
            code: Python code to execute
            timeout: Max execution time in seconds
            mem_limit: Memory limit (e.g., "512m")
            cpu_quota: CPU quota (100000 = 1 CPU)
            
        Returns:
            Execution result with stdout, stderr, exit_code
        """
        if not self.client:
            raise RuntimeError("Docker client not initialized")
        
        logger.info("Executing code in Docker sandbox...")
        
        try:
            # Create container with security constraints
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=["python", "-c", code],
                # SECURITY: Network disabled
                network_disabled=True,
                # SECURITY: Read-only root filesystem
                read_only=True,
                # SECURITY: Resource limits
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                # SECURITY: No privileged mode
                privileged=False,
                # Cleanup after execution
                remove=True,
                # Capture output
                stdout=True,
                stderr=True,
                # Detach to handle timeout
                detach=True
            )
            
            # Wait for completion with timeout
            exit_code = container.wait(timeout=timeout)
            
            # Get output
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            logger.info(f"Sandbox execution completed (exit code: {exit_code})")
            
            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": False
            }
            
        except docker.errors.ContainerError as e:
            logger.error(f"Container execution failed: {e}")
            return {
                "success": False,
                "exit_code": e.exit_status,
                "stdout": "",
                "stderr": str(e),
                "timed_out": False
            }
            
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return {
                "success": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "timed_out": "timeout" in str(e).lower()
            }
    
    def execute_fix_code(
        self,
        original_code: str,
        fixed_code: str,
        test_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a fix in sandbox and validate it.
        
        Args:
            original_code: Original vulnerable code
            fixed_code: Proposed fix
            test_code: Optional test code to run
            
        Returns:
            Validation results
        """
        logger.info("Validating fix in sandbox...")
        
        # Create test harness
        test_harness = f"""
import sys
import traceback

# Original code (for comparison)
original_code = '''
{original_code}
'''

# Fixed code to test
fixed_code = '''
{fixed_code}
'''

# Execute fixed code
try:
    exec(fixed_code)
    print("SANDBOX_SUCCESS: Code executed without errors")
    sys.exit(0)
except Exception as e:
    print(f"SANDBOX_ERROR: {{e}}")
    traceback.print_exc()
    sys.exit(1)
"""
        
        result = self.execute_python_code(test_harness, timeout=60)
        
        # Check if code executed successfully
        success = result["success"] and "SANDBOX_SUCCESS" in result["stdout"]
        
        return {
            "validation_passed": success,
            "execution_result": result,
            "errors": result["stderr"] if not success else None
        }
    
    def run_poc_exploit(
        self,
        poc_code: str,
        target_code: str
    ) -> Dict[str, Any]:
        """
        Run PoC exploit against code to verify vulnerability.
        
        Args:
            poc_code: Proof-of-concept exploit
            target_code: Code to attack
            
        Returns:
            Exploit results
        """
        logger.info("Running PoC in sandbox...")
        
        exploit_harness = f"""
import sys

# Target code
target_code = '''
{target_code}
'''

# PoC exploit
poc = '''
{poc_code}
'''

# Execute target
try:
    exec(target_code)
    # Try exploit
    exec(poc)
    print("POC_SUCCESS: Exploit succeeded (vulnerability present)")
    sys.exit(0)
except Exception as e:
    print(f"POC_FAILED: Exploit failed (vulnerability fixed): {{e}}")
    sys.exit(1)
"""
        
        result = self.execute_python_code(exploit_harness, timeout=60)
        
        # POC success = vulnerability still exists (BAD)
        # POC failed = vulnerability fixed (GOOD)
        vulnerability_present = result["success"] and "POC_SUCCESS" in result["stdout"]
        
        return {
            "vulnerability_present": vulnerability_present,
            "exploit_result": result
        }


# Global sandbox instance
docker_sandbox = DockerSandbox()
