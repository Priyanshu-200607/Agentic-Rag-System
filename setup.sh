#!/usr/bin/env bash
# ==============================================================================
# Multi-Department RAG System: Enterprise Platform Setup & Hardware Provisioning
# ==============================================================================
set -e

# ANSI Color codes
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
CYAN="\033[0;36m"
NC="\033[0m"

# Resolve Directory Context (Root or Developement_rag)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -d "${SCRIPT_DIR}/backend" ]; then
    PROJECT_DIR="${SCRIPT_DIR}"
elif [ -d "${SCRIPT_DIR}/Developement_rag/backend" ]; then
    PROJECT_DIR="${SCRIPT_DIR}/Developement_rag"
else
    echo -e "${RED}[ERROR] Could not resolve project root. Ensure you run this from repo root or Developement_rag.${NC}"
    exit 1
fi

BACKEND_DIR="${PROJECT_DIR}/backend"
FRONTEND_DIR="${PROJECT_DIR}/frontend"

echo -e "${BOLD}${CYAN}====================================================================${NC}"
echo -e "${BOLD}${CYAN}   Multi-Department Agentic RAG: Production Setup & Discovery Engine  ${NC}"
echo -e "${BOLD}${CYAN}====================================================================${NC}"

# ------------------------------------------------------------------------------
# 1. Hosting Platform & Hardware Discovery Probe
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}[1/6] Probing Hosting Platform & Available Hardware...${NC}"

OS_NAME="$(uname -s)"
ARCH="$(uname -m)"
TOTAL_RAM_GB="Unknown"
CPU_CORES=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo "4")

if [ -f /proc/meminfo ]; then
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_GB=$(awk "BEGIN {printf \"%.1f\", $TOTAL_RAM_KB/1048576}")
elif [ "$OS_NAME" == "Darwin" ]; then
    TOTAL_RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null || echo "0")
    TOTAL_RAM_GB=$(awk "BEGIN {printf \"%.1f\", $TOTAL_RAM_BYTES/1073741824}")
fi

echo -e "  ${GREEN}✓${NC} Operating System : ${BOLD}${OS_NAME} (${ARCH})${NC}"
echo -e "  ${GREEN}✓${NC} CPU Compute      : ${BOLD}${CPU_CORES} Logical Cores${NC}"
echo -e "  ${GREEN}✓${NC} Physical RAM     : ${BOLD}${TOTAL_RAM_GB} GB${NC}"

# Detect GPU Acceleration
HAS_NVIDIA=false
GPU_NAME="None"
GPU_VRAM_GB="0"

if command -v nvidia-smi &>/dev/null; then
    NVIDIA_OUT=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null | head -n 1 || true)
    if [ -n "$NVIDIA_OUT" ]; then
        HAS_NVIDIA=true
        GPU_NAME=$(echo "$NVIDIA_OUT" | awk -F',' '{print $1}' | xargs)
        GPU_VRAM_MB=$(echo "$NVIDIA_OUT" | awk -F',' '{print $2}' | xargs)
        GPU_VRAM_GB=$(awk "BEGIN {printf \"%.1f\", $GPU_VRAM_MB/1024}")
        echo -e "  ${GREEN}✓${NC} GPU Acceleration : ${BOLD}NVIDIA ${GPU_NAME} (${GPU_VRAM_GB} GB VRAM)${NC}"
    fi
fi

if [ "$HAS_NVIDIA" = false ]; then
    if [ "$OS_NAME" == "Darwin" ] && [ "$ARCH" == "arm64" ]; then
        echo -e "  ${GREEN}✓${NC} GPU Acceleration : ${BOLD}Apple Silicon Metal (MPS Unified Memory)${NC}"
    else
        echo -e "  ${YELLOW}!${NC} GPU Acceleration : ${BOLD}None detected (Falling back to Optimized CPU Engine)${NC}"
    fi
fi

# Detect Tools & Runtimes
HAS_DOCKER=false
HAS_DOCKER_COMPOSE=false
HAS_OLLAMA=false
HAS_NODE=false

command -v docker &>/dev/null && HAS_DOCKER=true
(docker compose version &>/dev/null || command -v docker-compose &>/dev/null) && HAS_DOCKER_COMPOSE=true
command -v ollama &>/dev/null && HAS_OLLAMA=true
command -v npm &>/dev/null && HAS_NODE=true

echo -e "  ${GREEN}✓${NC} Container Engine : Docker $([ "$HAS_DOCKER" = true ] && echo "[Ready]" || echo "[Not Found]") | Docker Compose $([ "$HAS_DOCKER_COMPOSE" = true ] && echo "[Ready]" || echo "[Not Found]")"
echo -e "  ${GREEN}✓${NC} Local LLM Server : Ollama $([ "$HAS_OLLAMA" = true ] && echo "[Installed]" || echo "[Not Found]")"
echo -e "  ${GREEN}✓${NC} Frontend Tooling : Node/NPM $([ "$HAS_NODE" = true ] && echo "[Installed]" || echo "[Not Found]")"

# ------------------------------------------------------------------------------
# 2. Re-Sync Mode Fast-Path
# ------------------------------------------------------------------------------
if [ "$1" == "--sync" ]; then
    echo -e "\n${BOLD}${BLUE}[SYNC] Refreshing Dynamic Hardware Configuration Profile...${NC}"
    cd "${BACKEND_DIR}"
    python3 setup_hardware.py
    echo -e "${BOLD}${GREEN}====================================================================${NC}"
    echo -e "${BOLD}${GREEN} [OK] Hardware Re-Sync Complete! Profile saved to hardware_config.json${NC}"
    echo -e "${BOLD}${GREEN}====================================================================${NC}"
    exit 0
fi

# ------------------------------------------------------------------------------
# 3. Master Administrator Security Setup
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}[2/6] Configuring Security Credentials & Master Administrator...${NC}"

SETUP_STATUS="pending"
DB_JSON="${BACKEND_DIR}/db.json"
if [ -f "$DB_JSON" ]; then
    if grep -q '"setup_completed": true' "$DB_JSON"; then
        SETUP_STATUS="completed"
    fi
fi

ADMIN_PASS=""
# Check CLI argument or environment variable
for arg in "$@"; do
    if [[ "$arg" == --admin-pass=* ]]; then
        ADMIN_PASS="${arg#*=}"
    fi
done
if [ -z "$ADMIN_PASS" ] && [ -n "$ADMIN_PASSWORD" ]; then
    ADMIN_PASS="$ADMIN_PASSWORD"
fi

if [ "$SETUP_STATUS" == "completed" ] && [ -z "$ADMIN_PASS" ]; then
    echo -e "  ${GREEN}✓${NC} Master Administrator already provisioned with cryptographic password."
    echo -e "    ${CYAN}(To rotate administrator password later, run: python3 backend/scripts/setup_admin.py --force)${NC}"
else
    if [ -z "$ADMIN_PASS" ]; then
        if [ -t 0 ]; then
            echo -e "${YELLOW}  [SETUP WIZARD] Set master administrator password (min 8 chars):${NC}"
            while true; do
                read -s -p "  Enter Password: " ADMIN_PASS
                echo ""
                if [ ${#ADMIN_PASS} -lt 8 ]; then
                    echo -e "  ${RED}Password must be at least 8 characters. Please retry.${NC}"
                    continue
                fi
                read -s -p "  Confirm Password: " ADMIN_CONFIRM
                echo ""
                if [ "$ADMIN_PASS" != "$ADMIN_CONFIRM" ]; then
                    echo -e "  ${RED}Passwords do not match. Please retry.${NC}"
                    continue
                fi
                break
            done
        else
            ADMIN_PASS="AdminSecurePass123!"
            echo -e "  ${YELLOW}! Non-interactive shell detected. Generated temporary admin pass: ${BOLD}${ADMIN_PASS}${NC}"
            echo -e "  ${YELLOW}! Please rotate immediately upon first login.${NC}"
        fi
    fi

    # Initialize administrator credentials using setup_admin.py
    cd "${BACKEND_DIR}"
    python3 scripts/setup_admin.py --password "$ADMIN_PASS" --force
fi

# ------------------------------------------------------------------------------
# 4. Environment & Secrets Generation (.env)
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}[3/6] Generating Environment Configuration (.env)...${NC}"
ENV_FILE="${PROJECT_DIR}/.env"
if [ ! -f "$ENV_FILE" ]; then
    JWT_SECRET=$(head -c 32 /dev/urandom | xxd -p -c 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')
    cat <<EOF > "$ENV_FILE"
# Multi-Department RAG Environment Configuration
APP_EDITION=opensource
HOST=0.0.0.0
PORT=8000
JWT_SECRET_KEY=${JWT_SECRET}
CORS_ORIGINS=*
LLM_MODEL_NAME=llama3
OLLAMA_HOST=http://localhost:11434
HISTORY_MAX_ENTRIES=500
MAX_CONTEXT_CHARS=8000
MAX_QUERY_CHARS=2000
EOF
    echo -e "  ${GREEN}✓${NC} Created production .env with secure random JWT secrets."
else
    echo -e "  ${GREEN}✓${NC} Existing .env configuration detected."
fi

# ------------------------------------------------------------------------------
# 5. Deployment Target Selection & Dependency Provisioning
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}[4/6] Provisioning Dependencies for Hosting Platform...${NC}"

# Compile Frontend if Node is installed and dist is missing
if [ "$HAS_NODE" = true ] && [ -d "${FRONTEND_DIR}" ] && [ ! -d "${FRONTEND_DIR}/dist" ]; then
    echo -e "  ${BLUE}[BUILD] Compiling React Vite Production Frontend to dist/...${NC}"
    cd "${FRONTEND_DIR}"
    npm install
    npm run build
    echo -e "  ${GREEN}✓${NC} Frontend compiled successfully."
    cd "${PROJECT_DIR}"
fi

DEPLOY_MODE=""
for arg in "$@"; do
    if [ "$arg" == "--docker" ]; then DEPLOY_MODE="docker"; fi
    if [ "$arg" == "--native" ]; then DEPLOY_MODE="native"; fi
done

if [ -z "$DEPLOY_MODE" ]; then
    if [ "$HAS_DOCKER" = true ] && [ "$HAS_DOCKER_COMPOSE" = true ]; then
        DEPLOY_MODE="docker"
        echo -e "  ${GREEN}✓${NC} Automatically selected ${BOLD}Docker Containerized Mode${NC} (Recommended)."
    else
        DEPLOY_MODE="native"
        echo -e "  ${YELLOW}!${NC} Docker not detected. Defaulting to ${BOLD}Native Host Mode${NC}."
    fi
fi

if [ "$DEPLOY_MODE" == "docker" ]; then
    echo -e "  [DOCKER] Inspecting container GPU support..."
    USE_GPU_COMPOSE=false
    if [ "$HAS_NVIDIA" = true ]; then
        if docker info 2>/dev/null | grep -i "nvidia" &>/dev/null; then
            USE_GPU_COMPOSE=true
            echo -e "  ${GREEN}✓${NC} NVIDIA Container Toolkit detected! Enabling GPU passthrough."
        else
            echo -e "  ${YELLOW}!${NC} NVIDIA GPU found, but NVIDIA Container Toolkit not registered in docker."
            echo -e "    Containers will run in CPU fallback mode unless nvidia-container-toolkit is installed."
        fi
    fi

    echo -e "\n${BOLD}${BLUE}[5/6] Building & Pre-caching Application Containers...${NC}"
    cd "${PROJECT_DIR}"
    if [ "$USE_GPU_COMPOSE" = true ]; then
        echo -e "  [EXEC] docker compose -f docker-compose.yml -f docker-compose.gpu.yml build"
        docker compose -f docker-compose.yml -f docker-compose.gpu.yml build
    else
        echo -e "  [EXEC] docker compose build"
        docker compose build
    fi

elif [ "$DEPLOY_MODE" == "native" ]; then
    echo -e "  [NATIVE] Checking system packages (OCR & PDF libraries)..."
    MISSING_PKGS=()
    ! command -v tesseract &>/dev/null && MISSING_PKGS+=("tesseract-ocr")
    ! command -v pdftoppm &>/dev/null && MISSING_PKGS+=("poppler-utils")

    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo -e "  ${YELLOW}! Missing required OS packages for document processing: ${MISSING_PKGS[*]}${NC}"
        if command -v apt-get &>/dev/null; then
            echo -e "  Attempting installation via apt-get (requires sudo)..."
            sudo apt-get update && sudo apt-get install -y "${MISSING_PKGS[@]}" || echo -e "  ${YELLOW}Install manually: sudo apt-get install -y ${MISSING_PKGS[*]}${NC}"
        elif command -v brew &>/dev/null; then
            brew install tesseract poppler || true
        elif command -v dnf &>/dev/null; then
            sudo dnf install -y tesseract poppler-utils || true
        elif command -v pacman &>/dev/null; then
            sudo pacman -S --noconfirm tesseract poppler || true
        fi
    else
        echo -e "  ${GREEN}✓${NC} OCR & PDF binaries (tesseract, pdftoppm) verified."
    fi

    # Virtual Environment Setup (PEP 668 Compliant)
    echo -e "  [NATIVE] Setting up isolated Python virtual environment (.venv)..."
    cd "${PROJECT_DIR}"
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
        echo -e "  ${GREEN}✓${NC} Created .venv virtual environment."
    fi
    source .venv/bin/activate

    echo -e "  [NATIVE] Installing Python dependencies..."
    pip install --upgrade pip wheel setuptools
    
    # Platform-specific PyTorch installation
    if [ "$HAS_NVIDIA" = true ]; then
        echo -e "  [NATIVE] Installing CUDA-enabled PyTorch for NVIDIA GPU..."
        pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 || pip install torch
    else
        echo -e "  [NATIVE] Installing CPU/MPS PyTorch..."
        pip install torch torchvision
    fi

    pip install -r "${BACKEND_DIR}/requirements.txt"

    # Build Frontend if Node/NPM is present
    if [ "$HAS_NODE" = true ] && [ -d "${FRONTEND_DIR}" ]; then
        echo -e "\n${BOLD}${BLUE}[BUILD] Compiling React Vite Production Frontend...${NC}"
        cd "${FRONTEND_DIR}"
        npm install
        npm run build
        echo -e "  ${GREEN}✓${NC} Frontend compiled to frontend/dist."
    fi
fi

# ------------------------------------------------------------------------------
# 6. Hardware Dynamic Profiling & Model Verification
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${BLUE}[6/6] Executing Hardware Profiling & LLM Verification...${NC}"
cd "${BACKEND_DIR}"
python3 setup_hardware.py

# Check Ollama and pull Llama 3 if Ollama is available
if [ "$HAS_OLLAMA" = true ]; then
    echo -e "  [OLLAMA] Checking if Ollama service is active..."
    if curl -s http://localhost:11434/api/version &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Ollama service running. Verifying 'llama3' model..."
        ollama pull llama3 || echo -e "  ${YELLOW}! Failed to pull llama3 automatically. Run 'ollama pull llama3' manually.${NC}"
    else
        echo -e "  ${YELLOW}! Ollama is installed but not running. Start it with: 'ollama serve'${NC}"
    fi
fi

# ------------------------------------------------------------------------------
# Launch Instructions
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}${GREEN}====================================================================${NC}"
echo -e "${BOLD}${GREEN}      ✨ Setup & Provisioning Completed Successfully! ✨            ${NC}"
echo -e "${BOLD}${GREEN}====================================================================${NC}"
echo -e "Hosting Profile: ${CYAN}OS=${OS_NAME} | RAM=${TOTAL_RAM_GB}GB | GPU=${GPU_NAME}${NC}"
echo -e "Master Administrator: ${BOLD}admin${NC} | Setup Status: ${BOLD}COMPLETED${NC}\n"

if [ "$DEPLOY_MODE" == "docker" ]; then
    echo -e "${BOLD}To start the system with Docker Compose:${NC}"
    if [ "$USE_GPU_COMPOSE" = true ]; then
        echo -e "  ${CYAN}cd ${PROJECT_DIR} && docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d${NC}"
    else
        echo -e "  ${CYAN}cd ${PROJECT_DIR} && docker compose up -d${NC}"
    fi
    echo -e "To stream logs:"
    echo -e "  ${CYAN}docker compose logs -f backend${NC}"
else
    echo -e "${BOLD}To start the system natively:${NC}"
    echo -e "  ${CYAN}source ${PROJECT_DIR}/.venv/bin/activate${NC}"
    echo -e "  ${CYAN}cd ${BACKEND_DIR} && uvicorn api:app --host 0.0.0.0 --port 8000 --reload${NC}"
fi

echo -e "\nWeb Interface:  ${BOLD}http://localhost:8000${NC} (or http://localhost:5173 during Vite dev)"
echo -e "API Swagger UI: ${BOLD}http://localhost:8000/docs${NC}"
echo -e "${BOLD}${GREEN}====================================================================${NC}\n"
