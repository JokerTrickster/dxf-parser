# 아키텍처 문서

LLM 기반 DXF 다중 레이어 추출 시스템

## 시스템 개요

```
┌─────────────────────────────────────────────────────────────┐
│                     DXF AI Extractor                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Input: DXF File (주차장 도면)                                │
│     ↓                                                         │
│  ┌──────────────────────────────────────────────────┐        │
│  │  1. DXF Parser (src/core/dxf_parser.py)          │        │
│  │     - ezdxf로 파일 읽기                            │        │
│  │     - 문서 검증                                    │        │
│  └──────────────────────────────────────────────────┘        │
│     ↓                                                         │
│  ┌──────────────────────────────────────────────────┐        │
│  │  2. Block Extractor (src/core/block_extractor.py)│        │
│  │     - 재귀적 블록 탐색                             │        │
│  │     - 기하학 추출 (LWPOLYLINE/CIRCLE/POLYLINE)    │        │
│  │     - 좌표 변환 (스케일/회전/이동)                 │        │
│  └──────────────────────────────────────────────────┘        │
│     ↓                                                         │
│  ┌──────────────────────────────────────────────────┐        │
│  │  3. LLM Classifier (src/ai/llm_classifier.py)    │        │
│  │     ┌─────────────────────────────────────┐      │        │
│  │     │ Cache Hit?                          │      │        │
│  │     │   Yes → Return Cached Result        │      │        │
│  │     │   No  → Call Claude API             │      │        │
│  │     └─────────────────────────────────────┘      │        │
│  │     - 블록명 + 문맥 분석                          │        │
│  │     - 카테고리/타입 분류                          │        │
│  │     - 확신도 계산                                 │        │
│  └──────────────────────────────────────────────────┘        │
│     ↓                                                         │
│  ┌──────────────────────────────────────────────────┐        │
│  │  4. Output Generator                             │        │
│  │     - DXF 파일 생성 (레이어별 분류)               │        │
│  │     - CSV 내보내기 (메타데이터 포함)              │        │
│  └──────────────────────────────────────────────────┘        │
│     ↓                                                         │
│  Output: Classified DXF + CSV                                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## 디렉토리 구조

```
dxf-parser/
├── src/                                # 소스 코드
│   ├── core/                           # 핵심 로직
│   │   ├── dxf_parser.py               # DXF 읽기/쓰기
│   │   ├── block_extractor.py          # 블록 추출
│   │   └── geometry_processor.py       # 기하학 연산
│   ├── ai/                             # AI 분류
│   │   ├── llm_classifier.py           # LLM 분류기
│   │   └── cache_manager.py            # 캐싱 관리
│   ├── models/                         # 데이터 모델
│   │   ├── layer_schema.py             # 레이어 스키마
│   │   └── extracted_entity.py         # 추출 엔티티
│   └── utils/                          # 유틸리티
│       ├── logger.py                   # 로깅
│       └── validator.py                # 검증
├── config/                             # 설정 파일
│   ├── layer_categories.yaml           # 레이어 정의
│   └── llm_prompts.yaml                # LLM 프롬프트
├── dxf_ai_extractor.py                 # 메인 진입점
├── dxf_parking_extractor.py            # 기존 파일 (deprecated)
├── test_basic.py                       # 기본 테스트
├── requirements.txt                    # 의존성
├── .env.example                        # 환경변수 템플릿
└── .env                                # 환경변수 (git 제외)
```

## 핵심 컴포넌트

### 1. DXF Parser (`src/core/dxf_parser.py`)

**역할**: DXF 파일 읽기/쓰기

```python
class DXFParser:
    def read(dxf_path: str) -> Document
    def create_output_dxf(entities, output_path)
    def export_to_csv(entities, csv_path)
```

**기능**:
- ezdxf를 사용한 DXF 파일 읽기
- 레이어별 엔티티 그룹화
- MTEXT 라벨 추가
- CSV 내보내기

### 2. Block Extractor (`src/core/block_extractor.py`)

**역할**: DXF에서 블록 추출 및 기하학 변환

```python
class BlockExtractor:
    def extract_all_blocks(max_depth=10) -> List[ExtractedEntity]
    def _extract_from_insert(insert_entity) -> List[ExtractedEntity]
    def _extract_block_geometry(block) -> List[(x, y)]
```

**알고리즘**:
1. 모델 스페이스에서 INSERT 엔티티 탐색
2. 재귀적으로 중첩된 블록 탐색 (최대 10단계)
3. 각 블록의 기하학 추출 (LWPOLYLINE 우선)
4. 면적 계산 후 가장 큰 폴리라인 선택
5. 좌표 변환 (스케일 → 회전 → 이동)

**지원 엔티티**:
- `LWPOLYLINE`: 경량 폴리라인 (주요)
- `POLYLINE`: 레거시 폴리라인
- `CIRCLE`: 원 (32각형으로 근사)

### 3. Geometry Processor (`src/core/geometry_processor.py`)

**역할**: 기하학적 연산

```python
class GeometryProcessor:
    @staticmethod
    def calculate_area(vertices) -> float  # Shoelace 공식
    @staticmethod
    def transform_vertices(vertices, insert_point, rotation, scale)
    @staticmethod
    def extract_circle_vertices(center, radius, segments=32)
```

**변환 순서**:
```
원본 좌표
  ↓ (1) 스케일링
  ↓ (2) 회전
  ↓ (3) 이동
최종 좌표
```

### 4. LLM Classifier (`src/ai/llm_classifier.py`)

**역할**: Claude API를 사용한 블록 분류

```python
class LLMLayerClassifier:
    def classify(block_name, context) -> Classification
    def batch_classify(blocks) -> List[Classification]
```

**분류 프로세스**:
```
블록명 "PARK_일반" + 문맥 (면적, 주변 블록 등)
  ↓
캐시 확인
  ↓ (캐시 미스)
LLM API 호출
  ↓
프롬프트 생성 (system + user)
  ↓
Claude 응답
  ↓
JSON 파싱
  ↓
Classification(category='parking', type='basic', confidence=0.98)
  ↓
캐시 저장
```

**프롬프트 구조**:
- **System Prompt**: 전문가 역할 정의, 카테고리 설명
- **User Prompt**: 블록 정보, 문맥 데이터
- **Response**: JSON 형식 (category, type, confidence, reasoning)

### 5. Cache Manager (`src/ai/cache_manager.py`)

**역할**: 분류 결과 캐싱으로 비용 절감

```python
class CacheManager:
    def get(block_name) -> Optional[dict]
    def set(block_name, classification)
    def save_cache()
```

**캐시 파일 형식** (`.layer_classification_cache.json`):
```json
{
  "PARK_일반": {
    "category": "parking",
    "type": "basic",
    "confidence": 0.98,
    "reasoning": "일반 주차면 키워드 포함",
    "cached_at": "2024-01-01T10:00:00"
  },
  "기둥-C1": {
    "category": "structure",
    "type": "column",
    "confidence": 0.95,
    "reasoning": "기둥 키워드",
    "cached_at": "2024-01-01T10:00:01"
  }
}
```

## 데이터 모델

### ExtractedEntity
```python
@dataclass
class ExtractedEntity:
    block_name: str                      # "PARK_일반"
    geometry_type: str                   # "LWPOLYLINE"
    vertices: List[Tuple[float, float]]  # [(x1,y1), (x2,y2), ...]
    area: Optional[float]                # 12.5 m²
    insert_point: Tuple[float, float]    # (1234.56, 5678.90)
    rotation: float                      # 45.0°
    classification: Optional[Classification]
```

### Classification
```python
@dataclass
class Classification:
    category: str        # "parking"
    type: str           # "basic"
    confidence: float   # 0.98
    reasoning: str      # "일반 주차면 키워드 포함"
    method: str         # "llm" | "cached"
```

### LayerSchema
```python
@dataclass
class LayerSchema:
    categories: Dict[str, LayerCategory]

    def get_output_layer(category, type) -> str
    def get_color(category, type) -> int
```

## 설정 시스템

### layer_categories.yaml
레이어 카테고리 정의 (사용자 확장 가능)

```yaml
categories:
  parking:
    types:
      basic:
        output_layer: "p-parking-basic"
        color: 7
        typical_keywords: ["일반", "NORMAL"]
```

### llm_prompts.yaml
LLM 프롬프트 템플릿

```yaml
system_prompt: |
  당신은 건축 CAD 도면 전문가입니다...

classification_prompt: |
  블록 정보:
  - 이름: {block_name}
  - 엔티티 타입: {geometry_type}
  ...
```

## 에러 처리

### 검증 레이어
1. **파일 검증** (`DXFValidator.validate_file`)
   - 파일 존재 확인
   - DXF 확장자 확인
   - DXF 구조 검증

2. **API 키 검증** (`DXFValidator.validate_api_key`)
   - 환경 변수 존재 확인
   - 키 형식 검증 (sk-ant-로 시작)

3. **분류 오류 처리**
   - API 호출 실패 시 폴백: `category='other', type='unclassified'`
   - 로그 기록 및 통계 추적

## 성능 최적화

### 1. 캐싱 전략
- **첫 실행**: 모든 블록 API 호출 (~1초/블록)
- **이후 실행**: 캐시된 블록 즉시 반환 (~0ms/블록)
- **캐시 히트율**: 실전 90% 이상

### 2. 배치 처리 (향후 개선 가능)
```python
# 현재: 개별 호출
for block in blocks:
    classify(block)

# 향후: 배치 API
classify_batch([block1, block2, ...])  # 단일 API 호출
```

### 3. 기하학 캐싱
```python
self.block_geometry_cache = {}  # 블록 정의 재사용
```

## 확장 포인트

### 1. 새로운 레이어 타입 추가
`config/layer_categories.yaml` 수정:
```yaml
categories:
  new_category:
    types:
      new_type:
        output_layer: "n-new_category-new_type"
        color: 10
```

### 2. 커스텀 분류 로직
`src/ai/llm_classifier.py` 상속:
```python
class CustomClassifier(LLMLayerClassifier):
    def classify(self, block_name, context):
        # 커스텀 전처리
        result = super().classify(block_name, context)
        # 커스텀 후처리
        return result
```

### 3. 추가 엔티티 타입
`src/core/block_extractor.py` 확장:
```python
elif entity.dxftype() == 'ARC':
    # ARC 처리 로직
```

## 보안 고려사항

1. **API 키 보호**
   - `.env` 파일은 `.gitignore`에 포함
   - 환경 변수로만 전달
   - 코드에 하드코딩 금지

2. **입력 검증**
   - DXF 파일 크기 제한 (메모리 보호)
   - 재귀 깊이 제한 (무한 루프 방지)

3. **출력 검증**
   - 파일 덮어쓰기 전 확인
   - 경로 주입 방지

## 테스트 전략

### 단위 테스트 (향후 추가)
```python
tests/
├── test_geometry_processor.py
├── test_block_extractor.py
├── test_llm_classifier.py
└── test_dxf_parser.py
```

### 통합 테스트
```bash
python3 test_basic.py  # 구조 검증
```

### E2E 테스트
```bash
python3 dxf_ai_extractor.py osong-b1.dxf --stats
```

## 모니터링

### 로깅 레벨
- `DEBUG`: 모든 분류 결과, API 호출
- `INFO`: 주요 단계, 진행 상황
- `WARNING`: 예상치 못한 상황
- `ERROR`: 실패한 작업

### 통계 수집
```python
{
    'total_requests': 100,
    'cache_hits': 75,
    'api_calls': 25,
    'cache_hit_rate': 0.75,
    'errors': 0
}
```

## 의존성

- **ezdxf** (>= 1.0.0): DXF 파일 처리
- **anthropic** (>= 0.18.0): Claude API 클라이언트
- **pyyaml** (>= 6.0): YAML 설정 파싱
- **python-dotenv** (>= 1.0.0): 환경 변수 관리

## 버전 관리

- **v1.0** (기존): `dxf_parking_extractor.py` - 주차면 전용
- **v2.0** (신규): `dxf_ai_extractor.py` - AI 기반 다중 레이어

## 라이선스 및 기여

기존 프로젝트와 동일한 라이선스 적용
