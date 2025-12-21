# DXF 주차장 도면 레이어 자동 생성 도구

주차장 CAD 도면(DXF)에서 주차면을 자동으로 추출하고, 표준화된 레이어 구조로 변환하는 Python 도구입니다.

## 요구사항

```bash
pip install ezdxf
```

## 사용법

### 기본 사용

```bash
python3 dxf_parking_extractor.py <입력파일.dxf>
```

### 옵션

| 옵션 | 설명 |
|------|------|
| `-o, --output` | 출력 DXF 파일명 지정 |
| `-c, --csv` | CSV 내보내기 파일명 지정 |
| `--normalize` | 좌표를 원점 기준으로 정규화 |
| `--floor B1/B2` | 특정 층만 추출 |
| `--split-floors` | 층별로 파일 분리 저장 |
| `--no-ids` | 주차면 ID 텍스트 제외 |

### 예시

```bash
# 기본 변환 (전체)
python3 dxf_parking_extractor.py osong-b1.dxf

# 좌표 정규화 적용
python3 dxf_parking_extractor.py osong-b1.dxf --normalize

# 층별 분리 저장 + 좌표 정규화
python3 dxf_parking_extractor.py osong-b1.dxf --split-floors --normalize

# B1층만 추출
python3 dxf_parking_extractor.py osong-b1.dxf --floor B1 --normalize

# 출력 파일명 지정
python3 dxf_parking_extractor.py osong-b1.dxf -o output.dxf -c output.csv

# ID 텍스트 없이 생성
python3 dxf_parking_extractor.py osong-b1.dxf --no-ids
```

## 출력 레이어 구조

| 레이어명 | 설명 | 색상 |
|----------|------|------|
| `p-parking-basic` | 일반 주차면 | 흰색 (7) |
| `p-parking-large` | 확장 주차면 | 초록 (3) |
| `p-parking-small` | 경차 주차면 | 시안 (4) |
| `p-parking-disable` | 장애인 주차면 | 빨강 (1) |
| `p-parking-large-electric` | 전기차 주차면 | 파랑 (5) |
| `p-parking-large-women` | 가족배려 주차면 | 마젠타 (6) |
| `p-parking-id` | 주차면 ID 텍스트 | 흰색 (7) |

## 지원하는 원본 블록 타입

도구는 다음 블록명 패턴을 자동 인식합니다:

- `PARK_일반` → `p-parking-basic`
- `PARK_확장` → `p-parking-large`
- `PARK_경차` → `p-parking-small`
- `PARK_장애인` → `p-parking-disable`
- `Park-환경친화`, `PARK-EC` → `p-parking-large-electric`
- `가족배려주차(확장형)`, `가족배려주차(일반형)`, `교통약자우선` → `p-parking-large-women`

## 출력 파일

### DXF 파일
- 각 주차면이 닫힌 LWPOLYLINE으로 저장
- 레이어별로 분류되어 있음
- 주차면 ID가 MTEXT로 중앙에 배치

### CSV 파일
| 컬럼 | 설명 |
|------|------|
| id | 주차면 일련번호 |
| layer | 레이어명 |
| type | 원본 주차면 타입 |
| center_x | 중심점 X 좌표 |
| center_y | 중심점 Y 좌표 |
| rotation | 회전 각도 |
| vertex_count | 꼭짓점 수 |
| vertices | 꼭짓점 좌표 (세미콜론 구분) |

## 레이어 매핑 커스터마이징

`dxf_parking_extractor.py` 파일의 `LAYER_MAPPING` 딕셔너리를 수정하여 다른 블록 패턴을 추가할 수 있습니다:

```python
LAYER_MAPPING = {
    'PARK_일반': 'p-parking-basic',
    'PARK_확장': 'p-parking-large',
    # 새로운 패턴 추가
    '새블록명': 'p-parking-custom',
}
```

---

## 기술 문서: 레이어 추출 방식

### 사용 기술

| 기술 | 용도 |
|------|------|
| **ezdxf** | DXF 파일 파싱 및 생성 (Python 라이브러리) |
| **블록 구조 분석** | CAD 블록 참조(INSERT) 추적 |
| **재귀 탐색** | 중첩 블록 구조 처리 |
| **기하학 계산** | 면적 계산, 좌표 변환 |

### 추출 프로세스

```
원본 DXF
    │
    ▼
┌─────────────────────────────────────┐
│ 1. 메인 블록 탐색                    │
│    - '지하1층평면도', '지하2층평면도' │
│    - 모델스페이스 INSERT 엔티티      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 2. 재귀적 블록 탐색                  │
│    - INSERT 엔티티에서 블록명 추출   │
│    - 중첩 블록 최대 10단계까지 탐색  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 3. 주차면 블록 식별                  │
│    - 블록명에서 키워드 패턴 매칭     │
│    - PARK_일반, PARK_확장 등         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 4. 기하학 추출                       │
│    - 블록 내 LWPOLYLINE 분석         │
│    - 가장 큰 면적의 폴리라인 선택    │
│    - 신발끈 공식으로 면적 계산       │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 5. 좌표 변환                         │
│    - INSERT 위치(이동)               │
│    - 회전 각도 적용                  │
│    - 스케일 적용                     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│ 6. 레이어 매핑 및 출력               │
│    - 표준 레이어명으로 변환          │
│    - 새 DXF 파일 생성                │
└─────────────────────────────────────┘
```

### 핵심 알고리즘

#### 1. 블록 구조 분석

DXF 파일은 블록(Block) 기반 구조를 사용합니다. 주차면은 블록으로 정의되고, INSERT 엔티티로 도면에 배치됩니다.

```
DXF 구조:
├── BLOCKS (블록 정의)
│   ├── 지하1층평면도
│   │   └── INSERT → PARK_일반 (위치, 회전)
│   │   └── INSERT → PARK_확장 (위치, 회전)
│   ├── PARK_일반
│   │   └── LWPOLYLINE (2500 x 5000 사각형)
│   └── PARK_확장
│       └── LWPOLYLINE (2600 x 5200 사각형)
└── MODELSPACE
    └── INSERT → 지하1층평면도
```

#### 2. 재귀적 블록 탐색

```python
def extract_parking_from_block(block, depth=0):
    if depth > 10:  # 무한 재귀 방지
        return

    for entity in block:
        if entity.dxftype() == "INSERT":
            block_name = entity.dxf.name

            # 주차면 블록인지 확인
            if is_parking_block(block_name):
                extract_geometry(entity)

            # 중첩 블록 탐색
            nested_block = doc.blocks[block_name]
            extract_parking_from_block(nested_block, depth + 1)
```

#### 3. 주차면 외곽선 추출 (면적 기반)

블록 내에 여러 LWPOLYLINE이 있을 수 있습니다 (외곽선 + 내부 마킹). 가장 큰 면적을 가진 닫힌 폴리라인을 주차면 외곽선으로 식별합니다.

```python
# 신발끈 공식 (Shoelace Formula)
def calculate_area(vertices):
    area = 0
    n = len(vertices)
    for i in range(n):
        j = (i + 1) % n
        area += vertices[i][0] * vertices[j][1]
        area -= vertices[j][0] * vertices[i][1]
    return abs(area) / 2
```

#### 4. 좌표 변환 (이동 + 회전 + 스케일)

INSERT 엔티티의 속성을 사용하여 블록 좌표를 월드 좌표로 변환합니다.

```python
def transform_vertices(vertices, insert_point, rotation, scale_x, scale_y):
    rad = math.radians(rotation)
    cos_r, sin_r = math.cos(rad), math.sin(rad)

    transformed = []
    for x, y in vertices:
        # 1. 스케일 적용
        x *= scale_x
        y *= scale_y
        # 2. 회전 적용
        new_x = x * cos_r - y * sin_r
        new_y = x * sin_r + y * cos_r
        # 3. 이동 적용
        new_x += insert_point.x
        new_y += insert_point.y
        transformed.append((new_x, new_y))

    return transformed
```

### 주차면 크기 분석 결과

원본 DXF 분석을 통해 파악한 주차면 크기:

| 타입 | 크기 (mm) | 용도 |
|------|-----------|------|
| PARK_일반 | 2500 x 5000 | 일반 승용차 |
| PARK_확장 | 2600 x 5200 | 대형차/SUV |
| PARK_경차 | 2000 x 3600 | 경차 전용 |
| PARK_장애인 | 5000 x 3300 | 장애인 전용 (넓은 통로) |
| Park-환경친화 | 2500 x 5000 | 전기차 충전 |

### 층 분리 알고리즘

X 좌표 기준 클러스터링으로 층을 분리합니다:

```python
def separate_floors(parking_data):
    x_values = [center_x for parking in parking_data]
    x_mid = (min(x_values) + max(x_values)) / 2

    floors = {'B1': [], 'B2': []}
    for parking in parking_data:
        if parking.center_x > x_mid:
            floors['B1'].append(parking)
        else:
            floors['B2'].append(parking)

    return floors
```

### 참고 파일 분석

`banpo-b3.dxf` (참고용 파일)의 레이어 구조를 분석하여 출력 레이어명을 결정했습니다:

```
banpo-b3.dxf 레이어:
├── p-parking-basic (8개)
├── p-parking-large (50개)
├── p-parking-small (12개)
├── p-parking-disable (4개)
├── p-parking-large-electric (10개)
├── p-parking-large-women (18개)
└── p-parking-cctvid (53개)
```

### 한계 및 개선 가능 사항

1. **블록명 의존성**: 주차면 식별이 블록명 패턴에 의존합니다. 다른 명명 규칙을 사용하는 DXF는 `LAYER_MAPPING` 수정이 필요합니다.

2. **층 분리 로직**: 현재 X 좌표 기반 단순 분리입니다. 복잡한 도면은 수동 조정이 필요할 수 있습니다.

3. **LLM 연동 가능성**: 블록명이 불명확한 경우 Claude API를 활용하여 주차면 여부를 판단하는 기능 추가 가능합니다.
