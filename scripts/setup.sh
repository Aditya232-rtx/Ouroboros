#!/bin/bash
# Ouroboros AI - Setup Script
# Initializes environment and starts all services

set -e

echo "🚀 Ouroboros AI Setup"
echo "===================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

echo -e "${GREEN}✅ Docker found${NC}"

# Check Ollama
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}⚠️  Ollama not found. Models will need to be loaded separately.${NC}"
else
    echo -e "${GREEN}✅ Ollama found${NC}"
    
    # Check if models are loaded
    echo "Checking Ollama models..."
    if ollama list | grep -q "ouroboros-red"; then
        echo -e "${GREEN}✅ ouroboros-red model found${NC}"
    else
        echo -e "${YELLOW}⚠️  ouroboros-red model not found${NC}"
    fi
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please update .env with your credentials${NC}"
fi

# Create required directories
echo "Creating required directories..."
mkdir -p logs secrets models

# Pull Docker images
echo "Pulling Docker images..."
docker-compose pull

# Start services
echo "Starting services..."
docker-compose up -d postgres redis immudb opa

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Initialize database
echo "Initializing database..."
docker-compose run --rm api python scripts/init_db.py

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Update .env with your GitHub token and Google credentials"
echo "2. Ensure Ollama models are loaded (ouroboros-red, ouroboros-blue, ouroboros-support)"
echo "3. Start the API: docker-compose up api"
echo "4. Access API at http://localhost:8000"
echo "5. View docs at http://localhost:8000/docs"
