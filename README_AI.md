# DXF AI-Enhanced Layer Extractor

LLM 기반 다중 레이어 자동 분류 시스템

## 주요 기능

- 🤖 **AI 기반 분류**: Claude API를 사용하여 블록 이름을 의미론적으로 분석
- 🏗️ **다중 레이어 지원**: 주차면, 구조물, 동선, 시설 등 모든 레이어 타입 추출
- 💾 **스마트 캐싱**: 분류 결과를 캐싱하여 비용 절감 (95% 이상)
- 🎯 **높은 정확도**: 다양한 명명 규칙에 대응 (한국어/영어 혼용)
- 📊 **상세한 분석**: 분류 근거와 확신도 제공

## 설치

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 ANTHROPIC_API_KEY 입력
```

## 사용법

### 기본 사용
```bash
python dxf_ai_extractor.py osong-b1.dxf
```

출력:
- `osong-b1_converted.dxf` - 분류된 레이어가 적용된 DXF 파일
- `osong-b1_layers.csv` - 상세 분류 정보 CSV

### 고급 옵션
```bash
# 출력 파일명 지정
python dxf_ai_extractor.py input.dxf -o output.dxf --csv data.csv

# ID 라벨 제외
python dxf_ai_extractor.py input.dxf --no-labels

# 통계 출력
python dxf_ai_extractor.py input.dxf --stats

# 캐시 초기화
python dxf_ai_extractor.py input.dxf --clear-cache

# 디버그 모드
python dxf_ai_extractor.py input.dxf --log-level DEBUG
```

## 지원 레이어 카테고리

### 주차 공간 (parking)
- `basic`: 일반 주차
- `disabled`: 장애인 주차
- `compact`: 경차 주차
- `large`: 확장형 주차
- `electric`: 전기차 충전
- `women`: 여성/가족 우선

### 구조물 (structure)
- `column`: 기둥
- `wall`: 벽체
- `beam`: 보

### 동선 (circulation)
- `entrance`: 출입구
- `exit`: 출구
- `ramp`: 경사로
- `stairs`: 계단
- `elevator`: 엘리베이터

### 시설 (facility)
- `room`: 일반 실/공간
- `mechanical`: 기계실
- `electrical`: 전기실

## 아키텍처

```
dxf-parser/
├── src/
│   ├── core/           # 핵심 로직
│   │   ├── dxf_parser.py
│   │   ├── block_extractor.py
│   │   └── geometry_processor.py
│   ├── ai/             # AI 분류
│   │   ├── llm_classifier.py
│   │   └── cache_manager.py
│   ├── models/         # 데이터 모델
│   │   ├── layer_schema.py
│   │   └── extracted_entity.py
│   └── utils/          # 유틸리티
│       ├── logger.py
│       └── validator.py
├── config/
│   ├── layer_categories.yaml    # 레이어 정의
│   └── llm_prompts.yaml         # LLM 프롬프트
└── dxf_ai_extractor.py          # 메인 진입점
```

## 레이어 커스터마이징

`config/layer_categories.yaml` 파일을 수정하여 새로운 레이어 타입 추가 가능:

```yaml
categories:
  my_category:
    description: "새로운 카테고리"
    types:
      my_type:
        name: "타입 이름"
        output_layer: "m-my_category-my_type"
        color: 7
        typical_keywords: ["키워드1", "키워드2"]
```

## 비용 최적화

### 캐싱 시스템
- 첫 실행: 모든 블록 분류 (~$0.05/1000블록)
- 이후 실행: 캐시된 블록 재사용 (~$0/1000블록)
- 캐시 파일: `.layer_classification_cache.json`

### 예상 비용
| 블록 수 | 첫 실행 | 캐시 후 |
|--------|--------|--------|
| 100 | $0.005 | $0 |
| 1,000 | $0.05 | $0 |
| 10,000 | $0.50 | $0 |

## CSV 출력 형식

| 컬럼 | 설명 |
|------|------|
| id | 순번 |
| block_name | 원본 블록 이름 |
| category | 분류된 카테고리 |
| type | 세부 타입 |
| confidence | 확신도 (0.0~1.0) |
| layer | 출력 레이어명 |
| center_x, center_y | 중심 좌표 |
| rotation | 회전 각도 |
| area | 면적 |
| vertex_count | 꼭짓점 수 |
| vertices | 좌표 리스트 |
| reasoning | 분류 근거 |

## 문제 해결

### API 키 오류
```
Error: ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다
```
→ `.env` 파일에 API 키 설정

### 분류 오류
```
Error: 분류 실패
```
→ `--log-level DEBUG`로 상세 로그 확인

### 캐시 문제
```
# 캐시 초기화
python dxf_ai_extractor.py input.dxf --clear-cache
```

## 기존 코드와의 차이점

| 항목 | 기존 (dxf_parking_extractor.py) | 신규 (dxf_ai_extractor.py) |
|------|-------------------------------|---------------------------|
| 레이어 타입 | 주차면만 | 모든 레이어 |
| 명명 규칙 | 하드코딩 | LLM 자동 분류 |
| 확장성 | 코드 수정 필요 | 설정 파일로 확장 |
| 엔티티 타입 | LWPOLYLINE만 | LWPOLYLINE/CIRCLE/POLYLINE |
| 비용 | 무료 | 유료 (캐싱으로 최소화) |

## 라이선스

기존 프로젝트와 동일
