# ──────────────────────────────────────────────────────────────────
# Ouroboros AI — SDK Dockerfile
# All-in-one image: Python deps + security tools + SDK
# ──────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

LABEL maintainer="Ouroboros Team <team@ouroboros.ai>"
LABEL description="Ouroboros AI Security Automation SDK"
LABEL version="2.0.0"

# ── Environment ───────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ── System deps + security tooling ───────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    build-essential \
    libpq-dev \
    gnupg \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Trivy — container/IaC vulnerability scanner
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Gitleaks — secrets detection
RUN ARCH=$(dpkg --print-architecture) && \
    curl -sL "https://github.com/gitleaks/gitleaks/releases/download/v8.18.2/gitleaks_8.18.2_linux_${ARCH}.tar.gz" \
    | tar -xz -C /usr/local/bin gitleaks || true

# ── Python dependencies (slim: no torch/pyrit/playwright) ────────
COPY requirements.txt requirements.docker.txt ./
RUN pip install --no-cache-dir -r requirements.docker.txt

# ── Application code ─────────────────────────────────────────────
COPY ouroboros/ ./ouroboros/
COPY src/ ./src/
COPY config/ ./config/
COPY templates/ ./templates/
COPY pyproject.toml setup.py* ./

# Create a minimal README so pyproject.toml doesn't fail
RUN echo "# Ouroboros SDK" > README.md

# Install the SDK in editable mode so `ouroboros` CLI is available
RUN pip install -e .

# ── Non-root user ────────────────────────────────────────────────
RUN groupadd -r ouroboros && useradd -r -g ouroboros -m ouroboros && \
    mkdir -p logs models outputs data && \
    chown -R ouroboros:ouroboros /app

# ── Expose API port ──────────────────────────────────────────────
EXPOSE 8000

# ── Healthcheck ──────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

USER ouroboros

# Default: run the API server
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
