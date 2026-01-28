# Ouroboros AI - Quick Start Guide

This guide will take you from a fresh machine to a fully running Ouroboros AI system, including the Red Agent, Blue Agent, Dashboard, and MCP integrations.

## 📋 Prerequisites

Ensure you have the following installed before starting:

1.  **Python 3.11+**: [Download](https://www.python.org/downloads/)
2.  **Node.js 20+** (LTS): [Download](https://nodejs.org/)
3.  **Docker & Docker Compose**: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
4.  **Ollama**: [Download](https://ollama.com/) (Required for local AI models)
5.  **Git**: [Download](https://git-scm.com/)
6.  **(Optional) Security Tools**: `nmap`, `nuclei`, `trivy` (if running local verification scripts outside Docker)

---

## 🚀 Step 1: AI Model Setup (Ollama)

Ouroboros relies on local LLMs for privacy and cost-efficiency. Pull the required models:

```bash
# 1. Start Ollama
ollama serve

# 2. Pull the models (in a separate terminal)
# Red Agent (Coding & Offensive Security)
ollama pull qwen2.5-coder:32b  # or 7b for lower VRAM

# Blue Agent (Reasoning, Fix Generation)
ollama pull deepseek-r1:14b    # or 7b

# Support Agents (Documentation, Governance - fast/light)
ollama pull phi3.5
```

---

## 🛠️ Step 2: Backend Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Aditya232-rtx/Ouroboros.git
cd Ouroboros
```

### 2. Configure Environment Variables
Copy the example environment file and update it with your secrets.

```bash
cp .env.example .env
nano .env  # Or use your code editor
```

**Critical Variables to Set:**
*   `GITHUB_TOKEN`: Your GitHub PAT (Classic) with `repo` scope.
*   `OLLAMA_BASE_URL`: Usually `http://localhost:11434/v1`.
*   `POSTGRES_PASSWORD`, `REDIS_PASSWORD`: Change these if deploying publicly.

### 3. Python Virtual Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## 🐳 Step 3: Infrastructure (Docker)

Start the supporting services (PostgreSQL, Redis, Immudb, OPA).

```bash
docker-compose up -d
```
*Wait ~10 seconds for databases to initialize.*

### Initialize Database
Push the schema to the running PostgreSQL instance.
```bash
# Ensure venv is active
python scripts/init_db.py
```

---

## 🔌 Step 4: MCP Server Setup

The system uses [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers for filesystem, GitHub, and Google Drive access. These are Node.js applications.

```bash
# Install specific MCP servers locally
npm install @modelcontextprotocol/server-filesystem @modelcontextprotocol/server-github @modelcontextprotocol/server-gdrive @modelcontextprotocol/server-slack
```

---

## 💻 Step 5: Frontend Dashboard Setup

The "War Room" dashboard allows you to visualize scans and agent activities.

```bash
cd frontend
npm install
npm run dev
```
The frontend will start at **http://localhost:3000**.

---

## ✅ Step 6: Verify Installation

We have a built-in verification script that:
1.  Checks for required tools (Nmap, Nuclei, etc.).
2.  Tests MCP connections.
3.  Runs a full "Red Agent" scan against a test repository.

```bash
# Open a new terminal from project root
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:.

# Run the full verification suite
python scripts/verify_red_agent_full.py
```

**Expected Output:**
*   ✅ Connection to MCP servers verified.
*   ✅ Vulnerable app cloned to sandbox (automatic Dockerfile generation).
*   ✅ Vulnerabilities detected (High/Critical) via Semgrep/Trivy/Nuclei.

---

## 🏃 Usage

### Option A: Web Dashboard
1.  Open **http://localhost:3000/dashboard**.
2.  Navigate to **Red Agent**.
3.  Enter a target GitHub URL (e.g., `https://github.com/Aditya232-rtx/vul`) and click **Start Scan**.

### Option B: API (Swagger UI)
1.  Start the Backend API:
    ```bash
    uvicorn src.api.main:app --reload --port 8000
    ```
2.  Open **http://localhost:8000/docs**.
3.  Use the `POST /api/scan` endpoint to trigger a scan manually.

---

## 📂 Directory Structure Key

*   `src/agents/`: Logic for Red, Blue, and Governance agents.
*   `src/security/tools/`: Wrappers for Nmap, Nuclei, Semgrep, etc.
*   `frontend/`: Next.js 14 Dashboard code.
*   `scripts/`: Utilities for databases, verifying tools, and testing.
*   `outputs/`: Scan reports (HTML/JSON) and logs are saved here.

## 🆘 Troubleshooting

*   **"Docker not found" in Red Agent**: Ensure Docker Desktop is running and you verified it with `docker ps`.
*   **"Connection refused" to Ollama**: Make sure `ollama serve` is running in a separate terminal.
*   **"Missing Dependencies"**: Re-run `pip install -r requirements.txt` and `npm install` in the root.
