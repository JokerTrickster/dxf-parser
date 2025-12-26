# 설치 가이드

## 1. Python 가상환경 생성 (권장)

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

## 2. 의존성 설치

```bash
pip install -r requirements.txt
```

또는 개별 설치:
```bash
pip install ezdxf>=1.0.0
pip install anthropic>=0.18.0
pip install pyyaml>=6.0
pip install python-dotenv>=1.0.0
```

## 3. API 키 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 키 입력
# ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
```

API 키 발급: https://console.anthropic.com/

## 4. 테스트 실행

```bash
# 도움말 확인
python3 dxf_ai_extractor.py --help

# 샘플 DXF 파일로 테스트
python3 dxf_ai_extractor.py osong-b1.dxf --stats
```

## 문제 해결

### ImportError: No module named 'yaml'
→ 가상환경을 활성화했는지 확인
→ `pip install pyyaml` 실행

### API 키 오류
→ `.env` 파일의 `ANTHROPIC_API_KEY` 확인
→ API 키가 `sk-ant-`로 시작하는지 확인

### DXF 파일 읽기 오류
→ 파일 경로 확인
→ DXF 파일 버전 확인 (R2000 이상 권장)
