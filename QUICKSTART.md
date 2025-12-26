# 빠른 시작 가이드

## 5분 안에 시작하기

### 1단계: 환경 준비 (2분)

```bash
# 프로젝트 디렉토리로 이동
cd dxf-parser

# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2단계: API 키 설정 (1분)

```bash
# .env 파일 생성
cp .env.example .env

# 편집기로 .env 열기
# ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

**API 키 발급**: https://console.anthropic.com/

### 3단계: 테스트 실행 (2분)

```bash
# 기본 테스트
python3 test_basic.py

# 샘플 DXF 파일로 실행
python3 dxf_ai_extractor.py osong-b1.dxf --stats
```

## 주요 명령어

### 기본 실행
```bash
python3 dxf_ai_extractor.py input.dxf
```

출력:
- `input_converted.dxf` - 분류된 레이어 DXF
- `input_layers.csv` - 분류 정보 CSV

### 옵션 지정
```bash
# 출력 파일명 지정
python3 dxf_ai_extractor.py input.dxf -o output.dxf --csv data.csv

# 통계 보기
python3 dxf_ai_extractor.py input.dxf --stats

# 디버그 모드
python3 dxf_ai_extractor.py input.dxf --log-level DEBUG
```

### 캐시 관리
```bash
# 캐시 초기화
python3 dxf_ai_extractor.py input.dxf --clear-cache

# 캐시 비활성화
python3 dxf_ai_extractor.py input.dxf --no-cache
```

## 출력 예시

### 콘솔 출력
```
2024-01-01 10:00:00 - dxf-parser - INFO - DXF 파일 검증 성공: 유효한 DXF 파일
2024-01-01 10:00:01 - dxf-parser - INFO - 레이어 스키마 로드 중...
2024-01-01 10:00:02 - dxf-parser - INFO - LLM 분류기 초기화 중...
2024-01-01 10:00:03 - dxf-parser - INFO - 모델 스페이스 탐색 시작 (최대 깊이: 10)
2024-01-01 10:00:05 - dxf-parser - INFO - 총 100개 블록 추출 완료
2024-01-01 10:00:06 - dxf-parser - INFO - LLM 분류 시작...
2024-01-01 10:00:07 - dxf-parser - INFO - 분류 중... (1/100) PARK_일반
2024-01-01 10:01:00 - dxf-parser - INFO - DXF 파일 생성 중...
2024-01-01 10:01:02 - dxf-parser - INFO - CSV 파일 생성 중...

=== 완료 ===
출력 DXF: osong-b1_converted.dxf
출력 CSV: osong-b1_layers.csv
추출된 레이어: 100개
```

### CSV 출력 (샘플)
```csv
id,block_name,category,type,confidence,layer,center_x,center_y,rotation,area,vertex_count,vertices,reasoning
1,PARK_일반,parking,basic,0.98,p-parking-basic,1234.56,5678.90,0.00,12.50,4,0.00,0.00;2500.00,0.00;...,일반 주차면 블록명 패턴
2,PARK_장애인,parking,disabled,0.99,p-parking-disabled,2345.67,6789.01,0.00,16.50,4,...,장애인 주차 키워드 포함
3,기둥-C1,structure,column,0.95,s-structure-column,3456.78,7890.12,0.00,0.20,32,...,기둥을 의미하는 키워드
```

## 다음 단계

- 📖 [상세 문서](README_AI.md) 읽기
- 🔧 [설치 가이드](INSTALL.md) 참고
- 🚀 [마이그레이션 가이드](MIGRATION_GUIDE.md) 확인
- ⚙️ [레이어 커스터마이징](config/layer_categories.yaml)

## 도움이 필요하신가요?

```bash
# 도움말 보기
python3 dxf_ai_extractor.py --help

# 기본 테스트 실행
python3 test_basic.py
```
