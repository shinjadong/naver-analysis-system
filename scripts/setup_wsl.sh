#!/bin/bash
# Naver AI Evolution - WSL2 설정 스크립트

set -e

echo "============================================"
echo "  Naver AI Evolution - WSL Setup"
echo "============================================"
echo ""

PROJECT_ROOT="/mnt/c/ai-projects/naver-ai-evolution"
VENV_PATH="$HOME/venvs/naver-ai"

# 1. 시스템 패키지 설치
echo "[1/5] 시스템 패키지 설치..."
sudo apt update -qq
sudo apt install -y -qq \
    python3.10 python3.10-venv python3-pip \
    adb \
    docker.io docker-compose \
    > /dev/null 2>&1

echo "  OK: 시스템 패키지 설치됨"

# 2. Python 가상환경 설정
echo "[2/5] Python 가상환경 설정..."
mkdir -p "$HOME/venvs"
if [ ! -d "$VENV_PATH" ]; then
    python3.10 -m venv "$VENV_PATH"
fi

source "$VENV_PATH/bin/activate"
pip install --upgrade pip -q
pip install -e "$PROJECT_ROOT[wsl]" -q

echo "  OK: Python 환경 설정됨"


# 3. Docker 설정
echo "[3/5] Docker 설정..."
sudo usermod -aG docker $USER 2>/dev/null || true
sudo systemctl enable docker 2>/dev/null || true
sudo systemctl start docker 2>/dev/null || true

echo "  OK: Docker 설정됨"

# 4. 공유 디렉토리 심볼릭 링크
echo "[4/5] 공유 디렉토리 링크..."
SHARED_DIR="/mnt/c/ai-projects/shared"
mkdir -p "$SHARED_DIR/message_queues/wsl_inbox"
mkdir -p "$SHARED_DIR/message_queues/wsl_outbox"

if [ ! -L "$HOME/ai-shared" ]; then
    ln -sf "$SHARED_DIR" "$HOME/ai-shared"
fi

echo "  OK: 공유 디렉토리 링크됨"

# 5. 환경 변수 설정
echo "[5/5] 환경 변수 설정..."
ENV_FILE="$HOME/.naver_ai_env"
cat > "$ENV_FILE" << 'EOF'
# Naver AI Evolution 환경 변수
export PROJECT_ROOT="/mnt/c/ai-projects/naver-ai-evolution"
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
export SHARED_DIR="/mnt/c/ai-projects/shared"

# Python 가상환경 자동 활성화
if [ -d "$HOME/venvs/naver-ai" ]; then
    source "$HOME/venvs/naver-ai/bin/activate"
fi

# DeepSeek API 키 (설정 필요)
# export DEEPSEEK_API_KEY="your-api-key"
EOF

# bashrc에 추가
if ! grep -q "naver_ai_env" "$HOME/.bashrc"; then
    echo "" >> "$HOME/.bashrc"
    echo "# Naver AI Evolution" >> "$HOME/.bashrc"
    echo "source $ENV_FILE" >> "$HOME/.bashrc"
fi

echo "  OK: 환경 변수 설정됨"

echo ""
echo "============================================"
echo "  설정 완료!"
echo "============================================"
echo ""
echo "다음 단계:"
echo "  1. 새 터미널 열기 (환경 변수 적용)"
echo "  2. DEEPSEEK_API_KEY 설정: ~/.naver_ai_env 파일 편집"
echo "  3. Docker 서비스 시작:"
echo "     cd $PROJECT_ROOT && docker-compose -f docker-compose.wsl.yml up -d"
echo "  4. AI 서비스 시작:"
echo "     python3 src/wsl/linux_daemons.py --start"
