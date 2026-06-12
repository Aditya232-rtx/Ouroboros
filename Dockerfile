# Ouroboros AI - Production Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies including security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libpq-dev \
    nmap \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI (for Docker-in-Docker control)
RUN curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh

# Install Node.js (for MCP Servers)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# Install Trivy
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Install Gitleaks
RUN curl -sS https://github.com/gitleaks/gitleaks/releases/download/v8.18.2/gitleaks_8.18.2_linux_x64.tar.gz | tar -xz -C /usr/local/bin gitleaks

# Install Nuclei
RUN curl -sS https://github.com/projectdiscovery/nuclei/releases/download/v3.2.0/nuclei_3.2.0_linux_amd64.tar.gz | tar -xz -C /usr/local/bin nuclei

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN groupadd -r ouroboros && useradd -r -g ouroboros -m ouroboros && \
    mkdir -p logs models outputs data && \
    chown -R ouroboros:ouroboros logs models outputs data

# Expose API port
EXPOSE 8000

# Switch to non-root user
USER ouroboros

# Health check (using health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application using Uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
