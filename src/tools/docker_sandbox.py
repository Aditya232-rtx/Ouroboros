"""
Ouroboros AI - Docker Sandbox
Secure code execution in isolated Docker containers
Per 03_CRITICAL_DO_NOT: NEVER execute generated code without sandboxing
"""

import logging
import docker
import base64
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
    
    def _encode_code_for_container(self, code: str) -> str:
        """
        Safely encode code for container execution using base64.
        
        SECURITY: Never interpolate untrusted code into string literals.
        Base64 encoding prevents triple-quote injection attacks.
        """
        return base64.b64encode(code.encode('utf-8')).decode('ascii')
    
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
        
        # SECURITY: Base64-encode code to prevent injection
        encoded_code = self._encode_code_for_container(code)
        
        try:
            # Create container with security constraints
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=[
                    "python", "-c",
                    f"import base64; exec(base64.b64decode('{encoded_code}').decode('utf-8'))"
                ],
                # SECURITY: Network disabled
                network_disabled=True,
                # SECURITY: Read-only root filesystem  
                read_only=True,
                # SECURITY: tmpfs for writable temp space
                tmpfs={"/tmp": "size=64M"},
                # SECURITY: Resource limits
                mem_limit=mem_limit,
                cpu_quota=cpu_quota,
                # SECURITY: No privileged mode
                privileged=False,
                # SECURITY: Drop all capabilities
                cap_drop=["ALL"],
                # Do NOT auto-remove so we can read logs
                remove=False,
                # Capture output
                stdout=True,
                stderr=True,
                # Detach to handle timeout
                detach=True
            )
            
            # Wait for completion with timeout — returns {"StatusCode": int, "Error": ...}
            result = container.wait(timeout=timeout)
            exit_code = result.get("StatusCode", -1)
            
            # Get output before cleanup
            stdout = container.logs(stdout=True, stderr=False).decode('utf-8')
            stderr = container.logs(stdout=False, stderr=True).decode('utf-8')
            
            # Cleanup container
            container.remove(force=True)
            
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
            # Try to cleanup container on error
            try:
                container.remove(force=True)
            except Exception:
                pass
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
        
        SECURITY: Code is base64-encoded before being passed to container
        to prevent triple-quote injection attacks.
        """
        logger.info("Validating fix in sandbox...")
        
        # Build test harness as a single string — will be base64-encoded
        test_harness = (
            "import sys, traceback\n"
            "try:\n"
            "    exec(fixed_code_content)\n"
            "    print('SANDBOX_SUCCESS: Code executed without errors')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print(f'SANDBOX_ERROR: {e}')\n"
            "    traceback.print_exc()\n"
            "    sys.exit(1)\n"
        )
        
        # Inject fixed_code as a variable via base64, not string interpolation
        encoded_fixed = self._encode_code_for_container(fixed_code)
        bootstrap = (
            f"import base64\n"
            f"fixed_code_content = base64.b64decode('{encoded_fixed}').decode('utf-8')\n"
            + test_harness
        )
        
        result = self.execute_python_code(bootstrap, timeout=60)
        
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
        
        SECURITY: Both poc_code and target_code are base64-encoded
        to prevent code injection during string construction.
        """
        logger.info("Running PoC in sandbox...")
        
        encoded_poc = self._encode_code_for_container(poc_code)
        encoded_target = self._encode_code_for_container(target_code)
        
        exploit_harness = (
            f"import sys, base64\n"
            f"target_code = base64.b64decode('{encoded_target}').decode('utf-8')\n"
            f"poc_code = base64.b64decode('{encoded_poc}').decode('utf-8')\n"
            "try:\n"
            "    exec(target_code)\n"
            "    exec(poc_code)\n"
            "    print('EXPLOIT_SUCCESS: Vulnerability confirmed')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print(f'EXPLOIT_FAILED: {e}')\n"
            "    sys.exit(1)\n"
        )
        
        result = self.execute_python_code(exploit_harness, timeout=30, mem_limit="256m")
        
        return {
            "exploit_successful": result["success"] and "EXPLOIT_SUCCESS" in result["stdout"],
            "execution_result": result,
        }

    def verify_vulnerability(
        self,
        poc_code: str,
        target_code: str
    ) -> Dict[str, Any]:
        """
        Verify if a vulnerability is still present by running PoC exploit.
        
        Returns whether vulnerability is present (bad) or fixed (good).
        """
        logger.info("Verifying vulnerability presence in sandbox...")
        
        encoded_poc = self._encode_code_for_container(poc_code)
        encoded_target = self._encode_code_for_container(target_code)
        
        exploit_harness = (
            f"import sys, base64\n"
            f"target_code = base64.b64decode('{encoded_target}').decode('utf-8')\n"
            f"poc_code = base64.b64decode('{encoded_poc}').decode('utf-8')\n"
            "try:\n"
            "    exec(target_code)\n"
            "    exec(poc_code)\n"
            "    print('POC_SUCCESS: Exploit succeeded (vulnerability present)')\n"
            "    sys.exit(0)\n"
            "except Exception as e:\n"
            "    print(f'POC_FAILED: Exploit failed (vulnerability fixed): {e}')\n"
            "    sys.exit(1)\n"
        )
        
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
