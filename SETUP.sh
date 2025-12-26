#!/bin/bash
# DXF AI Extractor 자동 설치 스크립트

echo "==================================="
echo "DXF AI Extractor 설치"
echo "==================================="
echo ""

# 1. 가상환경 생성
if [ ! -d "venv" ]; then
    echo "📦 가상환경 생성 중..."
    python3 -m venv venv
    echo "✓ 가상환경 생성 완료"
else
    echo "✓ 가상환경 이미 존재"
fi

echo ""

# 2. 가상환경 활성화
echo "🔄 가상환경 활성화 중..."
source venv/bin/activate

echo ""

# 3. 의존성 설치
echo "📚 의존성 설치 중..."
pip install --quiet --upgrade pip
pip install --quiet ezdxf anthropic pyyaml python-dotenv

echo "✓ 의존성 설치 완료"
echo ""

# 4. API 키 확인
if grep -q "여기에_실제_API_키_입력" .env 2>/dev/null; then
    echo "⚠️  .env 파일에 API 키를 설정해주세요"
elif grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then
    echo "✓ API 키 설정 완료"
else
    echo "⚠️  .env 파일을 확인해주세요"
fi

echo ""

# 5. 구조 테스트
echo "🧪 기본 테스트 실행 중..."
python3 test_basic.py

echo ""
echo "==================================="
echo "설치 완료!"
echo "==================================="
echo ""
echo "다음 명령어로 테스트하세요:"
echo "  source venv/bin/activate"
echo "  python3 test_api_simple.py"
echo "  python3 dxf_ai_extractor.py osong-b1.dxf --stats"
echo ""
