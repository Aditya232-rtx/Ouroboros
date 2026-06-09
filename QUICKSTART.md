# Ouroboros AI Quick Start Guide

## Prerequisites
- Docker and Docker Compose
- Ollama (for local model inference)
- 8GB+ RAM
- Git

## Setup (5 minutes)

### 1. Clone and Navigate
```bash
git clone https://github.com/your-org/ouroboros.git
cd ouroboros
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Required values:
- `GITHUB_TOKEN`: Your GitHub personal access token
- `GOOGLE_SERVICE_ACCOUNT_FILE`: Path to Google service account JSON

### 3. Load Ollama Models
```bash
# If you haven't imported the models yet
cd models
ollama create ouroboros-red -f Modelfile.qwen
ollama create ouroboros-blue -f Modelfile.deepseek
ollama create ouroboros-support -f Modelfile.phi3.new
cd ..

# Verify models
ollama list
```

### 4. Start Services
```bash
# Run setup script
./scripts/setup.sh

# Or manually:
docker-compose up -d
```

### 5. Initialize Database
```bash
python scripts/init_db.py
```

### 6. Start API (Local Development)
```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run API
uvicorn src.api.main:app --reload
```

## Usage

### Web Interface
Open http://localhost:8000/docs for interactive API documentation.

### API Example
```bash
# Start a scan
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/user/repo",
    "branch": "main",
    "scan_profile": "standard"
  }'

# Check status
curl http://localhost:8000/api/scan/SCAN-xxx
```

### Expected Workflow
1. Submit GitHub repository URL
2. RED agent scans for vulnerabilities (~60s)
3. GOVERNANCE prioritizes findings (~5s)
4. BLUE agent generates fixes (~30s per vuln)
5. RED verifies each fix (~20s)
6. Loop until all verified
7. Create GitHub PR with fixes
8. Generate compliance report

## Services

| Service | Port | Purpose |
|---------|------|---------|
| API | 8000 | FastAPI REST interface |
| Postgres | 5432 | State persistence |
| Redis | 6379 | Caching |
| immudb | 3322 | Audit logging |
| OPA | 8181 | Policy evaluation |
| Ollama | 11434 | Model inference |

## Troubleshooting

### Models not loading
```bash
# Check Ollama service
ollama list

# Restart Ollama
ollama serve
```

### Database connection failed
```bash
# Check PostgreSQL
docker-compose logs postgres

# Restart services
docker-compose restart postgres
```

### OPA policies not found
```bash
# Verify policies directory
ls -la config/opa_policies/

# Check OPA logs
docker-compose logs opa
```

## Next Steps
- Review `/docs` for complete documentation
- See `context/` for architecture details
- Check `tests/` for examples
