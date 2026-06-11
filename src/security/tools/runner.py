import subprocess
import logging
import os
import time
import socket
import uuid
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class SandboxRunner:
    """
    Manages the lifecycle of a sandboxed application for dynamic analysis.
    Handles cloning, building, running, and tearing down Docker containers.
    """

    def __init__(self, sandbox_path: str):
        self.sandbox_path = Path(sandbox_path)
        self.container_id: Optional[str] = None
        self.compose_project: Optional[str] = None
        self.port: int = self._find_free_port()
        self.host_url: str = ""

    def _find_free_port(self) -> int:
        """Finds a free port on localhost."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def _wait_for_service(self, url: str, timeout: int = 60) -> bool:
        """Waits for the service to become responsive."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # We can't use requests here easily without adding it to imports, 
                # but we can use curl or simple socket connect.
                # Let's use subprocess curl for simplicity in this environment
                result = subprocess.run(
                    ["curl", "-I", "--silent", url], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    return True
            except Exception:
                pass
            time.sleep(2)
        return False

    def start(self) -> Tuple[bool, str]:
        """
        Attempts to start the application in the sandbox.
        Returns (success, url).
        """
        if not self.sandbox_path.exists():
            return False, "Sandbox path not found"

        logger.info(f"Attempting to start sandbox in {self.sandbox_path}")

        try:
            # check for docker-compose
            compose_files = list(self.sandbox_path.glob("docker-compose.y*ml"))
            if compose_files:
                return self._start_compose(compose_files[0])
            
            # check for Dockerfile
            if (self.sandbox_path / "Dockerfile").exists():
                return self._start_dockerfile()

            # Attempt to auto-generate Dockerfile
            if self._generate_dockerfile():
                return self._start_dockerfile()

            return False, "No Docker configuration found (Dockerfile or docker-compose.yml)"

        except Exception as e:
            logger.error(f"Failed to start sandbox: {e}")
            return False, str(e)

    def _generate_dockerfile(self) -> bool:
        """Generates a default Dockerfile based on project type."""
        try:
            if (self.sandbox_path / "package.json").exists():
                logger.info("Detected Node.js project. Generating Dockerfile...")
                dockerfile_content = """
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
"""
                (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
                return True

            elif (self.sandbox_path / "requirements.txt").exists():
                logger.info("Detected Python project. Generating Dockerfile...")
                dockerfile_content = """
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
"""
                (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
                return True
                
            return False
        except Exception as e:
            logger.error(f"Failed to generate Dockerfile: {e}")
            return False

    def _start_compose(self, compose_file: Path) -> Tuple[bool, str]:
        """Start using docker-compose."""
        # Use a unique project name to avoid collisions
        project_name = f"sandbox_{uuid.uuid4().hex[:8]}"
        self.compose_project = project_name
        
        # We need to map the internal port to our free port.
        # This is tricky with compose without modifying the file.
        # For now, we'll try to rely on the compose file's existing mapping or 
        # assume standard ports if we can't easily parse it.
        # IMPROVEMENT: Modify docker-compose.yml to expose ports to random_port
        
        # For this iteration, let's assume the user's compose file maps ports correctly
        # or we might fail to reach it if it's 80:80 and 80 is taken.
        # A safer bet for auto-analysis is to rely on finding the mapped port via 'docker compose port'
        
        cmd = ["docker-compose", "-p", project_name, "-f", str(compose_file), "up", "-d"]
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=self.sandbox_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, f"Docker Compose failed: {result.stderr}"

        # Try to find the port mapping for port 80 or 8080 or 3000
        target_ports = [80, 8080, 3000, 5000, 8000]
        mapped_port = None
        
        for p in target_ports:
            port_cmd = ["docker-compose", "-p", project_name, "-f", str(compose_file), "port", "web", str(p)] # Try service name 'web'
            # If 'web' doesn't exist, we might need to list services.
            # This is complex. Let's try 'docker compose ps' and parse.
            pass
        
        # Simplified approach: subprocess docker ps to find the mapped port for this project
        ps_cmd = ["docker", "ps", "--format", "{{.Ports}}", "--filter", f"label=com.docker.compose.project={project_name}"]
        ps_res = subprocess.run(ps_cmd, capture_output=True, text=True)
        
        if not ps_res.stdout:
            # Maybe it failed to start?
            return False, "Container started but no ports found"

        # Output format example: "0.0.0.0:32768->80/tcp, :::32768->80/tcp"
        # We want the host port.
        import re
        match = re.search(r'0\.0\.0\.0:(\d+)', ps_res.stdout)
        if match:
            self.port = int(match.group(1))
            self.host_url = f"http://localhost:{self.port}"
        else:
            # Fallback
            self.host_url = "http://localhost:80" # Risky

        if self._wait_for_service(self.host_url):
            return True, self.host_url
        else:
            return False, "Service failed to respond on detected port"

    def _start_dockerfile(self) -> Tuple[bool, str]:
        """Start using Dockerfile."""
        image_name = f"sandbox_{uuid.uuid4().hex[:8]}"
        self.container_id = f"cont_{image_name}"

        # Build
        build_cmd = ["docker", "build", "-t", image_name, "."]
        logger.info(f"Building: {' '.join(build_cmd)}")
        build_res = subprocess.run(build_cmd, cwd=self.sandbox_path, capture_output=True, text=True)
        if build_res.returncode != 0:
            return False, f"Build failed: {build_res.stderr}"

        # Run with port mapping
        # Map container 80/tcp to self.port. 
        # We assume the app inside listens on 80, 8080 or 3000.
        # Typically Dockerfiles expose a port. We can inspect it.
        inspect_cmd = ["docker", "image", "inspect", image_name, "--format", "{{.Config.ExposedPorts}}"]
        inspect_res = subprocess.run(inspect_cmd, capture_output=True, text=True)
        exposed_port = "80" # default
        if "8080/tcp" in inspect_res.stdout:
            exposed_port = "8080"
        elif "3000/tcp" in inspect_res.stdout:
            exposed_port = "3000"
        elif "5000/tcp" in inspect_res.stdout:
            exposed_port = "5000"
        
        # Check if app needs database (package.json has pg, mysql, mongo, etc.)
        needs_db = self._app_needs_database()
        
        if needs_db:
            # Use host network so app can reach host's database services
            logger.info("App appears to need database. Using host network mode.")
            run_cmd = [
                "docker", "run", "-d", 
                "--name", self.container_id,
                "--network", "host",
                image_name
            ]
            # With host network, the app's port IS the host port
            self.port = int(exposed_port)
        else:
            run_cmd = [
                "docker", "run", "-d", 
                "--name", self.container_id,
                "-p", f"{self.port}:{exposed_port}",
                image_name
            ]
            
        logger.info(f"Running: {' '.join(run_cmd)}")
        run_res = subprocess.run(run_cmd, capture_output=True, text=True)
        
        if run_res.returncode != 0:
            return False, f"Run failed: {run_res.stderr}"

        self.host_url = f"http://localhost:{self.port}"
        if self._wait_for_service(self.host_url):
            return True, self.host_url
        else:
             return False, "Service failed to respond"
    
    def _app_needs_database(self) -> bool:
        """Check if the app requires a database connection."""
        db_indicators = ["pg", "mysql", "mysql2", "mongodb", "mongoose", "sequelize", "typeorm", "prisma", "psycopg2", "pymongo", "sqlalchemy"]
        
        # Check package.json for Node.js
        package_json = self.sandbox_path / "package.json"
        if package_json.exists():
            try:
                import json
                data = json.loads(package_json.read_text())
                deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
                for dep in deps:
                    if dep in db_indicators:
                        logger.info(f"Detected database dependency: {dep}")
                        return True
            except Exception:
                pass
        
        # Check requirements.txt for Python
        requirements = self.sandbox_path / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                for indicator in db_indicators:
                    if indicator in content:
                        logger.info(f"Detected database dependency: {indicator}")
                        return True
            except Exception:
                pass
        
        return False

    def stop(self):
        """Teardown."""
        if self.compose_project:
            logger.info(f"Stopping compose project {self.compose_project}")
            subprocess.run(["docker-compose", "-p", self.compose_project, "down", "-v"], cwd=self.sandbox_path, capture_output=True)
            self.compose_project = None
            
        if self.container_id:
            logger.info(f"Stopping container {self.container_id}")
            subprocess.run(["docker", "rm", "-f", self.container_id], capture_output=True)
            self.container_id = None
