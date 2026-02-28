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
        self.dockerfile_auto_generated: bool = False  # Track if we created the Dockerfile

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
                logger.info("Found docker-compose file, using compose workflow.")
                return self._start_compose(compose_files[0])
            
            # check for Dockerfile
            if (self.sandbox_path / "Dockerfile").exists():
                logger.info("Found existing Dockerfile in repository.")
                return self._start_dockerfile()

            # Attempt to auto-generate Dockerfile based on project type
            logger.info("No Dockerfile found — attempting auto-generation based on project type...")
            if self._generate_dockerfile():
                self.dockerfile_auto_generated = True
                logger.info("✅ Dockerfile auto-generated successfully (vulns from it will be excluded). Starting container...")
                return self._start_dockerfile()

            return False, "No Docker configuration found and could not auto-generate (unsupported project type)"

        except Exception as e:
            logger.error(f"Failed to start sandbox: {e}")
            return False, str(e)

    def _generate_dockerfile(self) -> bool:
        """
        Generates a default Dockerfile based on detected project type.
        Supports: Node.js, Python, Go, Java (Maven/Gradle), Ruby, PHP, Rust, .NET, static HTML.
        Intelligently detects the entry point for each language.
        """
        try:
            # ── Node.js ──
            if (self.sandbox_path / "package.json").exists():
                return self._gen_nodejs_dockerfile()

            # ── Python ──
            if (self.sandbox_path / "requirements.txt").exists() or \
               (self.sandbox_path / "setup.py").exists() or \
               (self.sandbox_path / "pyproject.toml").exists() or \
               (self.sandbox_path / "Pipfile").exists():
                return self._gen_python_dockerfile()

            # ── Go ──
            if (self.sandbox_path / "go.mod").exists():
                return self._gen_go_dockerfile()

            # ── Java (Maven) ──
            if (self.sandbox_path / "pom.xml").exists():
                return self._gen_java_maven_dockerfile()

            # ── Java (Gradle) ──
            if (self.sandbox_path / "build.gradle").exists() or \
               (self.sandbox_path / "build.gradle.kts").exists():
                return self._gen_java_gradle_dockerfile()

            # ── Ruby ──
            if (self.sandbox_path / "Gemfile").exists():
                return self._gen_ruby_dockerfile()

            # ── PHP (Composer) ──
            if (self.sandbox_path / "composer.json").exists():
                return self._gen_php_dockerfile()

            # ── Rust ──
            if (self.sandbox_path / "Cargo.toml").exists():
                return self._gen_rust_dockerfile()

            # ── .NET ──
            csproj = list(self.sandbox_path.glob("*.csproj"))
            if csproj:
                return self._gen_dotnet_dockerfile(csproj[0].name)

            # ── Static HTML fallback ──
            if list(self.sandbox_path.glob("*.html")) or (self.sandbox_path / "index.html").exists():
                return self._gen_static_dockerfile()

            logger.warning("Could not detect project type for Dockerfile generation.")
            return False

        except Exception as e:
            logger.error(f"Failed to generate Dockerfile: {e}")
            return False

    # ────────────────────────── per-language generators ──────────────────────────

    def _gen_nodejs_dockerfile(self) -> bool:
        """Generate Dockerfile for Node.js projects with smart start-script detection."""
        logger.info("Detected Node.js project. Generating Dockerfile...")
        import json as _json

        # Detect the start command from package.json
        start_cmd = 'node server.js'  # safe default
        port = 3000
        try:
            pkg = _json.loads((self.sandbox_path / "package.json").read_text())
            scripts = pkg.get("scripts", {})
            if "start" in scripts:
                start_cmd = "npm start"
            elif "dev" in scripts:
                start_cmd = "npm run dev"
            elif "serve" in scripts:
                start_cmd = "npm run serve"
            else:
                # Detect main entry from package.json "main" field
                main = pkg.get("main", "")
                if main:
                    start_cmd = f"node {main}"
                else:
                    # Search for common entry files
                    for candidate in ["server.js", "index.js", "app.js", "src/index.js", "src/server.js", "src/app.js"]:
                        if (self.sandbox_path / candidate).exists():
                            start_cmd = f"node {candidate}"
                            break
        except Exception:
            pass

        dockerfile_content = f"""FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production 2>/dev/null || npm install
COPY . .
EXPOSE {port}
ENV PORT={port}
CMD {_json.dumps(start_cmd.split())}
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_python_dockerfile(self) -> bool:
        """Generate Dockerfile for Python projects with smart entry-point detection."""
        logger.info("Detected Python project. Generating Dockerfile...")

        # Detect entry point
        entry_cmd = None
        port = 5000

        # Check for common web frameworks
        req_text = ""
        for req_file in ["requirements.txt", "Pipfile", "pyproject.toml", "setup.py"]:
            p = self.sandbox_path / req_file
            if p.exists():
                req_text += p.read_text(errors='ignore').lower()

        is_django = "django" in req_text
        is_flask = "flask" in req_text
        is_fastapi = "fastapi" in req_text or "uvicorn" in req_text

        if is_django:
            # Look for manage.py or wsgi.py
            manage_files = list(self.sandbox_path.rglob("manage.py"))
            wsgi_files = list(self.sandbox_path.rglob("wsgi.py"))
            if wsgi_files:
                wsgi_rel = wsgi_files[0].relative_to(self.sandbox_path)
                wsgi_module = str(wsgi_rel).replace("/", ".").replace(".py", "")
                entry_cmd = f"gunicorn {wsgi_module}:application --bind 0.0.0.0:8000"
                port = 8000
            elif manage_files:
                entry_cmd = "python manage.py runserver 0.0.0.0:8000"
                port = 8000
        elif is_fastapi:
            # Search for the app object
            for candidate in ["main.py", "app.py", "server.py", "api.py", "src/main.py", "app/main.py"]:
                if (self.sandbox_path / candidate).exists():
                    module = candidate.replace("/", ".").replace(".py", "")
                    entry_cmd = f"uvicorn {module}:app --host 0.0.0.0 --port 8000"
                    port = 8000
                    break
        elif is_flask:
            for candidate in ["app.py", "main.py", "server.py", "run.py", "wsgi.py", "application.py"]:
                if (self.sandbox_path / candidate).exists():
                    entry_cmd = f"python {candidate}"
                    port = 5000
                    break

        # Generic fallback: find ANY likely entry point
        if not entry_cmd:
            for candidate in ["app.py", "main.py", "server.py", "run.py", "manage.py", "wsgi.py", "index.py"]:
                if (self.sandbox_path / candidate).exists():
                    entry_cmd = f"python {candidate}"
                    break

        # Last resort
        if not entry_cmd:
            # Check for __main__.py pattern
            py_files = list(self.sandbox_path.glob("*.py"))
            if py_files:
                entry_cmd = f"python {py_files[0].name}"
            else:
                entry_cmd = "python -m http.server 8000"
                port = 8000

        # Install method
        install_step = "RUN pip install --no-cache-dir -r requirements.txt"
        if (self.sandbox_path / "Pipfile").exists():
            install_step = "RUN pip install pipenv && pipenv install --system --deploy"
        elif not (self.sandbox_path / "requirements.txt").exists():
            if (self.sandbox_path / "setup.py").exists():
                install_step = "RUN pip install --no-cache-dir -e ."
            elif (self.sandbox_path / "pyproject.toml").exists():
                install_step = "RUN pip install --no-cache-dir ."

        # Extra deps for frameworks
        extras = ""
        if is_django and "gunicorn" not in req_text:
            extras = "RUN pip install gunicorn\n"
        elif is_fastapi and "uvicorn" not in req_text:
            extras = "RUN pip install uvicorn\n"

        import json as _json
        dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
{install_step}
{extras}EXPOSE {port}
ENV PORT={port}
CMD {_json.dumps(entry_cmd.split())}
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_go_dockerfile(self) -> bool:
        """Generate Dockerfile for Go projects."""
        logger.info("Detected Go project. Generating Dockerfile...")
        dockerfile_content = """FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /server .

FROM alpine:3.19
COPY --from=builder /server /server
EXPOSE 8080
ENV PORT=8080
CMD ["/server"]
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_java_maven_dockerfile(self) -> bool:
        """Generate Dockerfile for Java Maven projects."""
        logger.info("Detected Java (Maven) project. Generating Dockerfile...")
        dockerfile_content = """FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests -B

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENV PORT=8080
CMD ["java", "-jar", "app.jar"]
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_java_gradle_dockerfile(self) -> bool:
        """Generate Dockerfile for Java Gradle projects."""
        logger.info("Detected Java (Gradle) project. Generating Dockerfile...")
        dockerfile_content = """FROM gradle:8-jdk21 AS builder
WORKDIR /app
COPY . .
RUN gradle build -x test --no-daemon

FROM eclipse-temurin:21-jre-alpine
WORKDIR /app
COPY --from=builder /app/build/libs/*.jar app.jar
EXPOSE 8080
ENV PORT=8080
CMD ["java", "-jar", "app.jar"]
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_ruby_dockerfile(self) -> bool:
        """Generate Dockerfile for Ruby projects."""
        logger.info("Detected Ruby project. Generating Dockerfile...")
        # Detect Rails vs generic
        is_rails = (self.sandbox_path / "config" / "environment.rb").exists() or \
                    (self.sandbox_path / "bin" / "rails").exists()
        if is_rails:
            cmd = '["rails", "server", "-b", "0.0.0.0", "-p", "3000"]'
        else:
            # Look for config.ru (Rack app)
            if (self.sandbox_path / "config.ru").exists():
                cmd = '["bundle", "exec", "rackup", "--host", "0.0.0.0", "-p", "3000"]'
            else:
                cmd = '["ruby", "app.rb"]'

        dockerfile_content = f"""FROM ruby:3.2-slim
RUN apt-get update -qq && apt-get install -y build-essential libpq-dev nodejs
WORKDIR /app
COPY Gemfile Gemfile.lock* ./
RUN bundle install
COPY . .
EXPOSE 3000
ENV PORT=3000
CMD {cmd}
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_php_dockerfile(self) -> bool:
        """Generate Dockerfile for PHP projects."""
        logger.info("Detected PHP project. Generating Dockerfile...")
        # Detect Laravel
        is_laravel = (self.sandbox_path / "artisan").exists()
        if is_laravel:
            cmd = '["php", "artisan", "serve", "--host=0.0.0.0", "--port=8000"]'
            port = 8000
        else:
            cmd = '["php", "-S", "0.0.0.0:8080", "-t", "public"]'
            port = 8080
            # Check if there's a public dir; if not serve from root
            if not (self.sandbox_path / "public").exists():
                cmd = '["php", "-S", "0.0.0.0:8080"]'

        dockerfile_content = f"""FROM php:8.3-cli
RUN apt-get update && apt-get install -y unzip git
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer
WORKDIR /app
COPY . .
RUN composer install --no-interaction --no-dev 2>/dev/null || true
EXPOSE {port}
ENV PORT={port}
CMD {cmd}
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_rust_dockerfile(self) -> bool:
        """Generate Dockerfile for Rust projects."""
        logger.info("Detected Rust project. Generating Dockerfile...")
        dockerfile_content = """FROM rust:1.77-slim AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/* /usr/local/bin/
EXPOSE 8080
ENV PORT=8080
CMD ["app"]
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_dotnet_dockerfile(self, csproj_name: str) -> bool:
        """Generate Dockerfile for .NET projects."""
        logger.info(f"Detected .NET project ({csproj_name}). Generating Dockerfile...")
        project_name = csproj_name.replace(".csproj", "")
        dockerfile_content = f"""FROM mcr.microsoft.com/dotnet/sdk:8.0 AS builder
WORKDIR /app
COPY . .
RUN dotnet publish -c Release -o /publish

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=builder /publish .
EXPOSE 8080
ENV ASPNETCORE_URLS=http://+:8080
CMD ["dotnet", "{project_name}.dll"]
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

    def _gen_static_dockerfile(self) -> bool:
        """Generate Dockerfile for static HTML/CSS/JS sites."""
        logger.info("Detected static site. Generating Dockerfile with nginx...")
        dockerfile_content = """FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""
        (self.sandbox_path / "Dockerfile").write_text(dockerfile_content)
        return True

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
