# DXF 파일 분석 및 라벨링 추출 처리 과정

## 개요

이 문서는 DXF 파일에서 특정 라벨링(블록)을 추출하고 분류하여 새로운 DXF 파일로 변환하는 전체 프로세스를 설명합니다.

---

## 전체 처리 흐름

```
┌─────────────────────────────────────────────────────┐
│ 1. DXF 파일 읽기 (ezdxf 라이브러리 사용)              │
│    - Document 객체 생성                              │
│    - Blocks & Modelspace 접근                       │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 2. INSERT 엔티티 탐색 및 블록 추출                   │
│    - Modelspace에서 모든 INSERT 엔티티 찾기         │
│    - 재귀적 블록 탐색 (최대 10 레벨)                │
│    - 각 블록에서 가장 큰 LWPOLYLINE 선택            │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 3. 좌표 변환 (Geometry Transformation)              │
│    - Scale 적용 (xscale, yscale)                   │
│    - Rotation 적용 (2D 회전 행렬)                   │
│    - Translation 적용 (INSERT 위치 더하기)          │
│    - Area 계산 (Shoelace 공식)                      │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 4. 블록 분류 (Classification)                       │
│    - 방법 A: 규칙 기반 (Rule-based)                 │
│    - 방법 B: LLM 기반 (Claude API)                  │
│    - 방법 C: 하드코딩 매핑                           │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 5. 레이어 매핑 및 출력 DXF 생성                      │
│    - 분류 결과를 레이어명으로 변환                   │
│    - 컬러 할당 (AutoCAD 컬러 인덱스)                │
│    - LWPOLYLINE 생성 및 ID 라벨 추가                │
└──────────────────┬──────────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────────┐
│ 6. 파일 저장                                         │
│    - output.dxf (분류된 레이어, 컬러, 라벨)         │
│    - output.csv (데이터 분석용)                     │
└─────────────────────────────────────────────────────┘
```

---

## 1. DXF 파일 읽기

### 구현 위치
`src/core/dxf_parser.py:24-35`

### 처리 과정
```python
def read(self, dxf_path: str) -> ezdxf.document.Drawing:
    return ezdxf.readfile(dxf_path)
```

### 상세 설명
- **라이브러리**: `ezdxf` Python 라이브러리 사용
- **지원 포맷**: AutoCAD R2010 이상
- **반환값**: ezdxf Document 객체
  - `doc.blocks`: 블록 정의 컬렉션
  - `doc.modelspace()`: 도면의 모델 스페이스 (엔티티 배치)

---

## 2. 블록 추출 (Block Extraction)

### 구현 위치
`src/core/block_extractor.py`

### 2.1 INSERT 엔티티 탐색

DXF 파일의 구조:
- **Block Definition**: 재사용 가능한 도형 템플릿 (예: 주차면 형상)
- **INSERT Entity**: Block을 실제로 배치한 인스턴스 (위치, 회전, 스케일 정보 포함)

#### 처리 과정 (`extract_all_blocks:27-56`)
```python
entities = []
modelspace = self.doc.modelspace()

for entity in modelspace:
    if entity.dxftype() == 'INSERT':
        extracted = self._extract_from_insert(entity, depth=0, max_depth=10)
        entities.extend(extracted)
```

**핵심 개념**:
- Modelspace의 모든 엔티티를 순회
- `INSERT` 타입만 선택 (블록 인스턴스)
- 재귀적으로 중첩된 블록도 추출 (최대 10레벨)

### 2.2 재귀적 블록 탐색

#### 구현 (`_extract_from_insert:58-135`)
```python
def _extract_from_insert(self, insert_entity, depth, max_depth, parent_transform=None):
    # 1. 블록 정의 조회
    block_name = insert_entity.dxf.name
    block = self.doc.blocks[block_name]

    # 2. 블록 기하학 추출
    geometry = self._extract_block_geometry(block)

    # 3. 변환 정보 추출
    insert_point = (insert_entity.dxf.insert.x, insert_entity.dxf.insert.y)
    rotation = insert_entity.dxf.rotation
    scale_x = getattr(insert_entity.dxf, 'xscale', 1.0)
    scale_y = getattr(insert_entity.dxf, 'yscale', 1.0)

    # 4. 좌표 변환 적용
    transformed_vertices = self.geometry_processor.transform_vertices(
        geometry, insert_point, rotation, scale_x, scale_y
    )

    # 5. 면적 계산
    area = self.geometry_processor.calculate_area(transformed_vertices)

    # 6. 엔티티 객체 생성
    entity = ExtractedEntity(
        block_name=block_name,
        geometry_type='LWPOLYLINE',
        vertices=transformed_vertices,
        area=area,
        insert_point=insert_point,
        rotation=rotation
    )

    # 7. 중첩 블록 재귀 탐색
    for nested_entity in block:
        if nested_entity.dxftype() == 'INSERT':
            nested_entities = self._extract_from_insert(
                nested_entity, depth=depth+1, max_depth=max_depth
            )
            entities.extend(nested_entities)
```

**재귀 처리 이유**:
- 복잡한 도면에서는 블록 안에 블록이 중첩되어 있음
- 예: 전체 층 블록 → 구역 블록 → 개별 주차면 블록
- 최대 10레벨까지 탐색하여 무한 루프 방지

### 2.3 블록 기하학 추출

#### 구현 (`_extract_block_geometry:137-195`)
```python
def _extract_block_geometry(self, block):
    largest_polyline = None
    largest_area = 0.0

    for entity in block:
        vertices = None

        # LWPOLYLINE 처리
        if entity.dxftype() == 'LWPOLYLINE':
            vertices = [(point[0], point[1]) for point in entity.get_points('xy')]

        # POLYLINE 처리
        elif entity.dxftype() == 'POLYLINE':
            vertices = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]

        # CIRCLE 처리 (32개 점으로 근사)
        elif entity.dxftype() == 'CIRCLE':
            center = (entity.dxf.center.x, entity.dxf.center.y)
            radius = entity.dxf.radius
            vertices = self.geometry_processor.extract_circle_vertices(center, radius)

        # 가장 큰 폴리곤 선택
        if vertices and len(vertices) >= 3:
            area = self.geometry_processor.calculate_area(vertices)
            if area > largest_area:
                largest_area = area
                largest_polyline = vertices

    return largest_polyline
```

**핵심 로직**:
- 블록 내 모든 엔티티를 검사
- **가장 큰 면적의 폴리곤만 선택** (외곽선)
- 내부 마킹(선, 텍스트 등)은 무시
- 지원 타입: `LWPOLYLINE`, `POLYLINE`, `CIRCLE`
- 원은 32개 점으로 근사하여 폴리곤으로 변환

**캐싱**:
```python
# 블록 정의당 한 번만 계산 (성능 최적화)
if block_name in self.block_geometry_cache:
    return self.block_geometry_cache[block_name]
```

---

## 3. 좌표 변환 (Geometry Transformation)

### 구현 위치
`src/core/geometry_processor.py:37-82`

### 3.1 변환 파이프라인

DXF에서 블록은 **로컬 좌표계**로 정의되고, INSERT 시 **월드 좌표계**로 변환됩니다.

#### 변환 순서 (중요!)
```
원본 좌표 → Scale → Rotation → Translation → 최종 좌표
```

#### 구현
```python
def transform_vertices(vertices, insert_point, rotation, scale_x=1.0, scale_y=1.0):
    rad = math.radians(rotation)
    cos_r = math.cos(rad)
    sin_r = math.sin(rad)

    transformed = []
    for x, y in vertices:
        # 1. Scale
        x *= scale_x
        y *= scale_y

        # 2. Rotation (2D 회전 행렬)
        x_rot = x * cos_r - y * sin_r
        y_rot = x * sin_r + y * cos_r

        # 3. Translation
        x_final = x_rot + insert_point[0]
        y_final = y_rot + insert_point[1]

        transformed.append((x_final, y_final))

    return transformed
```

### 3.2 면적 계산 (Shoelace 공식)

#### 구현 (`calculate_area:14-35`)
```python
def calculate_area(vertices: List[Tuple[float, float]]) -> float:
    n = len(vertices)
    area = 0.0

    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]  # x_i * y_(i+1)
        area -= vertices[j][0] * vertices[i][1]  # x_(i+1) * y_i

    return abs(area) / 2.0
```

**수학적 배경**:
- Shoelace Formula (신발끈 공식)
- 다각형의 꼭짓점 좌표만으로 면적 계산
- 시계방향/반시계방향 무관 (abs 처리)

**용도**:
- 엔티티 크기 기반 분류 (주차면: 10-15m², 기둥: 0.1-1m²)
- 블록 내 가장 큰 폴리곤 선택

---

## 4. 블록 분류 (Classification)

이 시스템은 3가지 분류 방법을 지원합니다.

### 방법 A: 규칙 기반 분류 (Rule-based)

#### 구현 위치
`src/ai/rule_based_classifier.py`

#### 특징
- **비용**: $0 (API 호출 없음)
- **속도**: 즉시
- **정확도**: ~85%
- **장점**: 빠르고 비용 없음
- **단점**: 미리 정의된 패턴만 인식

#### 분류 로직 (`_classify_by_rules:337-387`)

##### 1) 키워드 매칭
```python
def _match_keywords(block_name: str, keywords: List[str]) -> float:
    # 블록명을 $ 구분자로 분할
    # 예: "지하1층평면도$0$PARK_일반" → ["지하1층평면도", "0", "PARK_일반"]
    block_parts = block_name.split('$')

    for keyword in keywords:
        pattern = re.compile(keyword, re.IGNORECASE)

        # 정규표현식 매칭
        if pattern.search(block_name):
            return 1.0

    return 0.0
```

**키워드 예시** (`_build_rules:43-291`):
```python
{
    'category': 'parking',
    'type': 'disabled',
    'confidence': 0.95,
    'keywords': ['장애인', 'DISABLED', 'HANDICAP', '배리어프리'],
    'area_range': (15000000, 20000000)  # 15-20 m² (mm² 단위)
}
```

##### 2) 기하학 검증
```python
def _match_geometry(context: Dict, rule: Dict) -> float:
    score = 1.0

    # 면적 검증
    if 'area_range' in rule and context.get('area'):
        area = context['area']
        min_area, max_area = rule['area_range']

        if min_area <= area <= max_area:
            score *= 1.0  # 완전 일치
        elif area < min_area * 0.5 or area > max_area * 2:
            score *= 0.3  # 크게 벗어남
        else:
            score *= 0.7  # 약간 벗어남

    # 꼭짓점 수 검증 (기둥 판별 등)
    if 'vertex_range' in rule:
        vertex_count = context['vertex_count']
        min_v, max_v = rule['vertex_range']
        if not (min_v <= vertex_count <= max_v):
            score *= 0.5

    return score
```

##### 3) 최종 확신도 계산
```python
final_confidence = rule['confidence'] * keyword_match_score * geometry_score
```

**예시**:
- 규칙 기본 확신도: 0.95
- 키워드 매칭: 1.0 ("장애인" 발견)
- 면적 검증: 1.0 (16m² → 15-20m² 범위 내)
- 최종 확신도: 0.95 × 1.0 × 1.0 = 0.95

#### 규칙 우선순위
```python
rules = [
    # 1. 소방/안전 (circulation-exit)
    {'keywords': ['FSD', '소방', '비상'], ...},

    # 2. 계단 (circulation-stairs)
    {'keywords': ['계단', 'STAIR'], ...},

    # 3. 주차 (parking)
    {'type': 'disabled', 'keywords': ['장애인'], ...},
    {'type': 'electric', 'keywords': ['전기차', 'EV'], ...},
    {'type': 'women', 'keywords': ['여성', '가족'], ...},
    {'type': 'compact', 'keywords': ['경차'], ...},
    {'type': 'large', 'keywords': ['확장', 'LARGE'], ...},
    {'type': 'basic', 'keywords': ['일반', 'PARK'], ...},

    # 4. 구조물 (structure)
    {'type': 'column', 'keywords': ['기둥', 'COLUMN'], ...},
    {'type': 'wall', 'keywords': ['벽', 'WALL'], ...},

    # 5. 동선 (circulation)
    {'type': 'entrance', 'keywords': ['출입구', 'ENTRANCE'], ...},
    {'type': 'ramp', 'keywords': ['경사로', 'RAMP'], ...},

    # 6. 시설 (facility)
    {'type': 'restroom', 'keywords': ['화장실', 'WC'], ...},
    {'type': 'mechanical', 'keywords': ['기계실'], ...},
]
```

**중요**: 긴 키워드가 먼저 매칭됨 (예: "가족배려주차(확장형)" → "확장" 전에 매칭)

#### 캐싱
```python
# JSON 파일 캐시 (.layer_classification_cache.json)
if cached := self.cache.get(block_name):
    return cached

# 분류 후 캐시 저장
self.cache.set(block_name, result)
```

---

### 방법 B: LLM 기반 분류 (Claude API)

#### 구현 위치
`src/ai/llm_classifier.py`

#### 특징
- **비용**: ~$0.01/블록
- **속도**: 1-2초/블록
- **정확도**: ~90%
- **장점**: 미지의 패턴 인식 가능
- **단점**: 비용 발생, 속도 느림

#### 프롬프트 구조 (`config/llm_prompts.yaml`)
```yaml
system_prompt: |
  당신은 건축 CAD 도면 전문가입니다.
  블록 이름과 기하학 정보를 보고 레이어를 분류하세요.

classification_prompt: |
  블록 이름: {block_name}
  면적: {area} mm²
  꼭짓점 개수: {vertex_count}

  다음 JSON 형식으로 응답하세요:
  {{
    "category": "parking|structure|circulation|facility|other",
    "type": "basic|disabled|column|stairs|...",
    "confidence": 0.0-1.0,
    "reasoning": "분류 근거"
  }}
```

#### API 호출
```python
response = self.client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": prompt}
    ]
)

result = json.loads(response.content[0].text)
```

#### 캐싱 전략
- JSON 파일 캐시로 비용 절감
- 동일 블록명은 재분류하지 않음

---

### 방법 C: 하드코딩 매핑

#### 구현 위치
`dxf_parking_extractor.py:30-50`

#### 특징
- **비용**: $0
- **속도**: 즉시
- **정확도**: 100% (알려진 블록만)
- **단점**: 새 블록명마다 수동 업데이트 필요

#### 매핑 예시
```python
LAYER_MAPPING = {
    'PARK_일반': 'p-parking-basic',
    'PARK_확장': 'p-parking-large',
    'PARK_장애인': 'p-parking-disabled',
    'PARK_전기차': 'p-parking-electric',
    'PARK_경차': 'p-parking-compact',
    'COLUMN_500x700': 's-structure-column',
    'STAIRS_B1': 'c-circulation-stairs',
}

def classify(block_name):
    for keyword, layer in LAYER_MAPPING.items():
        if keyword in block_name:
            return layer
```

---

## 5. 레이어 매핑 및 출력

### 5.1 레이어명 생성

#### 구현 위치
`src/models/extracted_entity.py:44-63`

```python
@property
def output_layer(self) -> str:
    category = self.classification.category  # parking, structure, circulation, facility, other
    type_name = self.classification.type      # basic, disabled, column, stairs, etc.

    # 접두사 매핑
    prefix_map = {
        'parking': 'p',
        'structure': 's',
        'circulation': 'c',
        'facility': 'f',
        'other': 'x'
    }

    prefix = prefix_map.get(category, 'x')
    return f"{prefix}-{category}-{type_name}"
```

**레이어명 형식**: `{prefix}-{category}-{type}`

#### 레이어명 예시
| Category | Type | Layer Name | Description |
|----------|------|------------|-------------|
| parking | basic | `p-parking-basic` | 일반 주차면 |
| parking | disabled | `p-parking-disabled` | 장애인 주차면 |
| parking | electric | `p-parking-electric` | 전기차 주차면 |
| structure | column | `s-structure-column` | 기둥 |
| circulation | stairs | `c-circulation-stairs` | 계단 |
| facility | restroom | `f-facility-restroom` | 화장실 |
| other | unclassified | `x-other-unclassified` | 미분류 |

### 5.2 컬러 할당

#### 구현 위치
`config/layer_categories.yaml`

```yaml
categories:
  parking:
    basic:
      output_layer: "p-parking-basic"
      color: 7  # 흰색
    disabled:
      output_layer: "p-parking-disabled"
      color: 1  # 빨간색
  structure:
    column:
      output_layer: "s-structure-column"
      color: 5  # 파란색
```

**AutoCAD 컬러 인덱스** (1-256):
- 1: 빨간색
- 2: 노란색
- 3: 초록색
- 5: 파란색
- 7: 흰색

### 5.3 DXF 파일 생성

#### 구현 위치
`src/core/dxf_parser.py:37-102`

```python
def create_output_dxf(entities, output_path, add_labels=True):
    # 1. 새 DXF 문서 생성
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    # 2. 레이어 생성 (중복 제거)
    for entity in entities:
        layer_name = entity.output_layer  # "p-parking-basic"
        category = entity.classification.category
        type_name = entity.classification.type

        if layer_name not in created_layers:
            color = self.layer_schema.get_color(category, type_name)
            doc.layers.add(layer_name, color=color)

    # 3. 엔티티 그리기
    for idx, entity in enumerate(entities, start=1):
        # LWPOLYLINE 생성 (닫힌 폴리곤)
        points = [(x, y) for x, y in entity.vertices]
        msp.add_lwpolyline(
            points,
            close=True,
            dxfattribs={'layer': entity.output_layer}
        )

        # ID 라벨 추가
        if add_labels:
            center = entity.center
            msp.add_mtext(
                str(idx),  # "1", "2", "3", ...
                dxfattribs={
                    'layer': entity.output_layer,
                    'insert': (center[0], center[1]),
                    'char_height': 200,
                    'attachment_point': 5  # 중앙 정렬
                }
            )

    # 4. 저장
    doc.saveas(output_path)
```

**출력 특징**:
- **레이어별 분류**: 동일 카테고리/타입은 같은 레이어
- **컬러 코딩**: 레이어별 다른 색상으로 시각화
- **ID 라벨**: 각 엔티티에 순번 표시 (분석 용이)
- **닫힌 폴리곤**: `close=True`로 외곽선 완성

---

## 6. CSV 내보내기

### 구현 위치
`src/core/dxf_parser.py:104-165`

### CSV 컬럼 구조
```python
columns = [
    'id',              # 순번 (1, 2, 3, ...)
    'block_name',      # 원본 블록명 ("PARK_일반$0$INSERT")
    'category',        # 분류 카테고리 ("parking")
    'type',            # 분류 타입 ("basic")
    'confidence',      # 확신도 (0.0 ~ 1.0)
    'layer',           # 출력 레이어명 ("p-parking-basic")
    'center_x',        # 중심 X 좌표
    'center_y',        # 중심 Y 좌표
    'rotation',        # 회전 각도 (도)
    'area',            # 면적 (mm²)
    'vertex_count',    # 꼭짓점 개수
    'vertices',        # 좌표 리스트 ("x1,y1;x2,y2;...")
    'reasoning'        # 분류 근거
]
```

### CSV 예시
```csv
id,block_name,category,type,confidence,layer,center_x,center_y,rotation,area,vertex_count,vertices,reasoning
1,PARK_일반$0$INSERT,parking,basic,0.90,p-parking-basic,5000.00,3000.00,0.00,12500000.00,4,5000.00,3000.00;7500.00,3000.00;7500.00,8000.00;5000.00,8000.00,키워드 매칭: 100%
2,PARK_장애인$0$INSERT,parking,disabled,0.95,p-parking-disabled,10000.00,3000.00,0.00,16000000.00,4,10000.00,3000.00;14000.00,3000.00;14000.00,7000.00;10000.00,7000.00,키워드 매칭: 100%
```

**활용**:
- Excel/Python으로 통계 분석
- 분류 정확도 검증
- 면적/배치 분석

---

## 7. 실전 예시

### 입력 DXF 구조
```
osong-b1.dxf
├── Blocks (블록 정의)
│   ├── PARK_일반 → LWPOLYLINE [(0,0), (2500,0), (2500,5000), (0,5000)]
│   ├── PARK_장애인 → LWPOLYLINE [(0,0), (3500,0), (3500,4500), (0,4500)]
│   └── COLUMN_500 → LWPOLYLINE [(0,0), (500,0), (500,500), (0,500)]
└── Modelspace (배치)
    ├── INSERT "PARK_일반" at (5000, 3000), rotation=0°
    ├── INSERT "PARK_장애인" at (10000, 3000), rotation=0°
    └── INSERT "COLUMN_500" at (2000, 1000), rotation=45°
```

### 처리 과정

#### 1) 블록 추출
```python
# PARK_일반 블록
- 블록명: "PARK_일반"
- 로컬 좌표: [(0,0), (2500,0), (2500,5000), (0,5000)]
- INSERT 정보: position=(5000,3000), rotation=0°, scale=(1.0,1.0)
```

#### 2) 좌표 변환
```python
# Scale (이미 1.0)
vertices = [(0,0), (2500,0), (2500,5000), (0,5000)]

# Rotation (0°이므로 변화 없음)
vertices = [(0,0), (2500,0), (2500,5000), (0,5000)]

# Translation (+5000, +3000)
vertices = [
    (5000, 3000),
    (7500, 3000),
    (7500, 8000),
    (5000, 8000)
]
```

#### 3) 면적 계산
```python
# Shoelace 공식
area = abs((5000*3000 + 7500*8000 + 7500*8000 + 5000*3000)
         - (3000*7500 + 3000*7500 + 8000*5000 + 8000*5000)) / 2
     = 12,500,000 mm² (12.5 m²)
```

#### 4) 규칙 기반 분류
```python
# 키워드 매칭
block_name = "PARK_일반"
rule = {'keywords': ['일반', 'NORMAL', 'PARK'], ...}
match_score = 1.0  # "일반" 발견

# 면적 검증
area = 12,500,000 mm²
area_range = (10,000,000, 15,000,000)  # 10-15 m²
geo_score = 1.0  # 범위 내

# 최종 분류
category = "parking"
type = "basic"
confidence = 0.90 * 1.0 * 1.0 = 0.90
```

#### 5) 출력
```python
# 레이어명 생성
layer = "p-parking-basic"

# DXF 출력
msp.add_lwpolyline(
    [(5000,3000), (7500,3000), (7500,8000), (5000,8000)],
    close=True,
    dxfattribs={'layer': 'p-parking-basic'}
)

# ID 라벨
msp.add_mtext("1", dxfattribs={'insert': (6250, 5500), ...})
```

---

## 8. 주요 알고리즘 상세

### 8.1 Shoelace 공식 (면적 계산)

**수학적 정의**:
```
Area = |Σ(x_i * y_(i+1) - x_(i+1) * y_i)| / 2
```

**구현**:
```python
def calculate_area(vertices):
    n = len(vertices)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2.0
```

**예시**:
```python
vertices = [(0,0), (4,0), (4,3), (0,3)]
# 직사각형 4x3 = 12

area = (0*0 + 4*3 + 4*3 + 0*0) - (0*4 + 0*4 + 3*0 + 3*0)
     = (0 + 12 + 12 + 0) - (0 + 0 + 0 + 0)
     = 24 / 2 = 12 ✓
```

### 8.2 2D 회전 변환

**회전 행렬**:
```
[x']   [cos θ  -sin θ] [x]
[y'] = [sin θ   cos θ] [y]
```

**구현**:
```python
rad = math.radians(rotation)  # 도 → 라디안
cos_r = math.cos(rad)
sin_r = math.sin(rad)

x_rot = x * cos_r - y * sin_r
y_rot = x * sin_r + y * cos_r
```

**예시** (45° 회전):
```python
점 (1, 0)를 45° 회전
cos(45°) = 0.707
sin(45°) = 0.707

x' = 1 * 0.707 - 0 * 0.707 = 0.707
y' = 1 * 0.707 + 0 * 0.707 = 0.707

결과: (0.707, 0.707) → 대각선 방향 ✓
```

### 8.3 원의 폴리곤 근사

**구현**:
```python
def extract_circle_vertices(center, radius, segments=32):
    vertices = []
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        vertices.append((x, y))
    return vertices
```

**원리**:
- 원을 32개 점으로 분할
- 각 점 사이 각도: 360° / 32 = 11.25°
- 충분히 작아서 원처럼 보임

---

## 9. 성능 최적화

### 9.1 블록 기하학 캐싱
```python
# BlockExtractor 클래스
self.block_geometry_cache: Dict[str, List[Tuple[float, float]]] = {}

if block_name in self.block_geometry_cache:
    return self.block_geometry_cache[block_name]

# 계산 후 캐시 저장
self.block_geometry_cache[block_name] = vertices
```

**효과**: 동일 블록 정의가 여러 번 사용되어도 한 번만 계산

### 9.2 분류 결과 캐싱
```python
# CacheManager 클래스 (.layer_classification_cache.json)
{
    "PARK_일반": {
        "category": "parking",
        "type": "basic",
        "confidence": 0.90,
        "reasoning": "키워드 매칭: 100%"
    }
}
```

**효과**:
- API 호출 비용 절감 (LLM 모드)
- 재실행 시 즉시 분류

### 9.3 재귀 깊이 제한
```python
if depth > max_depth:  # max_depth = 10
    return []
```

**효과**: 무한 루프 방지, 과도한 메모리 사용 차단

---

## 10. 설정 파일

### 10.1 레이어 카테고리 (`config/layer_categories.yaml`)
```yaml
categories:
  parking:
    basic:
      output_layer: "p-parking-basic"
      color: 7
      typical_keywords: ["일반", "NORMAL", "STANDARD"]
    disabled:
      output_layer: "p-parking-disabled"
      color: 1
      typical_keywords: ["장애인", "DISABLED"]
```

### 10.2 LLM 프롬프트 (`config/llm_prompts.yaml`)
```yaml
system_prompt: |
  당신은 건축 CAD 도면 분석 전문가입니다.
  블록 이름과 기하학 정보를 분석하여 레이어를 분류하세요.

classification_prompt: |
  블록 이름: {block_name}
  기하학 타입: {geometry_type}
  면적: {area} mm²
  꼭짓점 개수: {vertex_count}

  카테고리: parking, structure, circulation, facility, other
  타입: basic, disabled, column, stairs, entrance, restroom 등
```

---

## 11. 엔트리 포인트 비교

### 11.1 `dxf_parking_extractor.py` (원본)
- **방법**: 하드코딩 매핑
- **비용**: $0
- **정확도**: 100% (알려진 블록만)
- **용도**: 특정 프로젝트 전용

### 11.2 `dxf_extractor_nollm.py` (규칙 기반)
- **방법**: 규칙 기반 분류
- **비용**: $0
- **정확도**: ~85%
- **용도**: 범용, 비용 절감

### 11.3 `dxf_ai_extractor.py` (AI 기반)
- **방법**: LLM (Claude) 분류
- **비용**: ~$0.01/블록
- **정확도**: ~90%
- **용도**: 최고 정확도 요구 시

### 11.4 `dxf_simple_extractor.py` (필터 없음)
- **방법**: 모든 블록 추출
- **비용**: $0
- **정확도**: N/A (필터링 없음)
- **용도**: 원시 데이터 추출

---

## 12. 데이터 구조

### 12.1 ExtractedEntity
```python
@dataclass
class ExtractedEntity:
    block_name: str                          # "PARK_일반$0$INSERT"
    geometry_type: str                       # "LWPOLYLINE"
    vertices: List[Tuple[float, float]]      # [(5000,3000), ...]
    area: Optional[float]                    # 12500000.0 (mm²)
    insert_point: Tuple[float, float]        # (5000, 3000)
    rotation: float                          # 0.0 (도)
    classification: Optional[Classification] # 분류 결과

    @property
    def center(self) -> Tuple[float, float]:
        """중심점 = 꼭짓점 평균"""
        return (sum(x)/len, sum(y)/len)

    @property
    def output_layer(self) -> str:
        """레이어명 = "{prefix}-{category}-{type}" """
        return f"p-parking-basic"
```

### 12.2 Classification
```python
@dataclass
class Classification:
    category: str      # "parking"
    type: str          # "basic"
    confidence: float  # 0.90
    reasoning: str     # "키워드 매칭: 100%"
    method: str        # "rule-based" | "llm" | "cached"
```

---

## 13. 에러 처리

### 13.1 블록 정의 없음
```python
if block_name not in self.doc.blocks:
    self.logger.warning(f"블록 정의 없음: {block_name}")
    return []
```

### 13.2 최대 재귀 깊이 초과
```python
if depth > max_depth:
    self.logger.warning(f"최대 재귀 깊이 {max_depth} 초과")
    return []
```

### 13.3 미분류 블록
```python
# 규칙 매칭 실패 시
return Classification(
    category='other',
    type='unclassified',
    confidence=0.3,
    reasoning='규칙 매칭 실패'
)
```

---

## 14. 통계 및 로깅

### 14.1 분류기 통계
```python
stats = classifier.get_stats()
# {
#     'total_requests': 150,
#     'cache_hits': 50,
#     'rule_matches': 85,
#     'unclassified': 15,
#     'cache_hit_rate': 0.33,
#     'classification_rate': 0.57
# }
```

### 14.2 로깅 레벨
```python
logging.basicConfig(level=logging.INFO)

logger.info(f"총 {len(entities)}개 블록 추출 완료")
logger.warning(f"블록 정의 없음: {block_name}")
logger.error(f"DXF 파일 읽기 실패: {e}")
```

---

## 15. 요약

### 핵심 프로세스
1. **DXF 읽기**: ezdxf로 Document 객체 생성
2. **블록 추출**: Modelspace의 INSERT 엔티티 재귀 탐색
3. **기하학 추출**: 각 블록의 가장 큰 LWPOLYLINE 선택
4. **좌표 변환**: Scale → Rotation → Translation 순서로 월드 좌표 계산
5. **분류**: 규칙 기반 또는 LLM으로 카테고리/타입 결정
6. **출력**: 분류된 레이어로 새 DXF 생성, CSV 내보내기

### 핵심 알고리즘
- **Shoelace 공식**: 폴리곤 면적 계산
- **2D 회전 행렬**: 좌표 회전 변환
- **재귀 탐색**: 중첩 블록 처리
- **정규표현식**: 키워드 매칭
- **기하학 검증**: 면적/꼭짓점 수 범위 확인

### 주요 최적화
- 블록 기하학 캐싱
- 분류 결과 캐싱
- 재귀 깊이 제한
- 병렬 처리 가능 설계

### 확장성
- 새 카테고리/타입 추가: `config/layer_categories.yaml` 수정
- 새 규칙 추가: `rule_based_classifier.py`의 `_build_rules()` 수정
- 새 분류기 추가: `ClassifierInterface` 구현

---

## 16. 참고 자료

### 코드 위치
- 메인 로직: `src/core/`
- 분류기: `src/ai/`
- 데이터 모델: `src/models/`
- 설정 파일: `config/`
- 엔트리 포인트: 루트 디렉토리 (`dxf_*.py`)

### 관련 문서
- `ARCHITECTURE.md`: 전체 아키텍처 설명
- `QUICKSTART.md`: 빠른 시작 가이드
- `MIGRATION_GUIDE.md`: 버전 마이그레이션
- `README.md`: 프로젝트 개요

### 외부 라이브러리
- `ezdxf`: DXF 파일 읽기/쓰기
- `anthropic`: Claude API 호출
- `python-dotenv`: 환경 변수 관리
