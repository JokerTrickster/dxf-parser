# DXF Parking Space Extractor

건설 도면 DXF 파일에서 주차면 정보를 자동으로 추출하고 CSV로 변환하는 시스템입니다.

## 📋 프로젝트 개요

### 핵심 기능

- **레이어 분석**: DXF 파일의 모든 블록을 자동 분석하고 AI가 주차면 타입 추정
- **레이어 선택**: 사용자가 원하는 레이어만 선택하여 추출 가능
- **주차면 추출**: 블록 이름 기반으로 다양한 주차면 유형 자동 분류
- **좌표 정규화**: 원점 기준 좌표 변환 및 mm → m 단위 변환
- **CSV/DXF 출력**: 표준화된 레이어 구조의 DXF 및 WKT 형식 CSV 생성

### 지원 주차면 타입

| 타입 | 설명 |
|------|------|
| `p-parking-basic` | 일반 주차 |
| `p-parking-large` | 확장형 주차 |
| `p-parking-small` | 경차 주차 |
| `p-parking-disable` | 장애인 주차 |
| `p-parking-electric` | 전기차 주차 |
| `p-parking-delivery` | 택배 주차 |
| `marker-disabled` | 장애인 마크 |
| `s-circulation-ramp` | 램프 |

## 🏗️ 시스템 아키텍처

```
┌─────────────┐
│   Frontend  │  React + Vite
│  (웹 UI)    │  - DXF 업로드
└──────┬──────┘  - 레이어 선택
       │         - 결과 다운로드
       ↓
┌─────────────┐
│  Backend    │  Go
│  (API 서버)  │  - HTTP API
└──────┬──────┘  - Job Queue (Channel)
       │         - Worker Pool
       ↓
┌─────────────┐
│   Python    │  Scripts (CLI)
│  (처리 엔진) │  - analyze_layers.py
└─────────────┘  - process_dxf.py
```

**Python은 별도 서버 구동 없이** Go 백엔드가 필요할 때마다 subprocess로 실행합니다.

## 🐍 Python 스크립트

### 1. analyze_layers.py

DXF 파일의 모든 블록을 분석하고 AI가 타입을 추정합니다.

**기능**:
- 모든 INSERT 블록 추출 및 사용 횟수 카운트
- LWPOLYLINE 면적 계산 (mm² → m²)
- 블록명 + 면적 기반 AI 타입 추정
- 주차면 관련 블록만 필터링 (옵션)
- JSON 결과 출력

**처리 로직**:
```
1. DXF 파일 로드 (ezdxf.readfile)
   └─ ModelSpace에서 모든 Entity 탐색

2. 중첩 블록 구조 탐색
   ├─ INSERT 엔티티 발견 → 메인 블록
   │   └─ 메인 블록 내부의 INSERT 탐색 → 서브 블록
   │       └─ 서브 블록 사용 횟수 카운트
   └─ 예: 지하주차장 도면 → PARK_일반 블록 639개

3. 각 블록의 상세 정보 추출
   ├─ LWPOLYLINE 엔티티 찾기
   │   ├─ 꼭짓점(vertices) 추출
   │   └─ Shoelace 공식으로 면적 계산
   │       └─ mm² → m² 변환 (/1000000)
   └─ 가장 큰 LWPOLYLINE 면적을 대표값으로 선택

4. AI 타입 추정 (suggest_layer_type)
   ├─ 면적 < 1m² → 마커로 분류
   │   └─ "장애", "disabled" 키워드 → marker-disabled
   ├─ 블록명 키워드 매칭
   │   ├─ "확장", "large" → p-parking-large
   │   ├─ "경차", "small" → p-parking-small
   │   ├─ "전기", "electric", "ev" → p-parking-electric
   │   ├─ "장애", "disabled" + 면적 ≥10m² → p-parking-disable
   │   ├─ "일반", "주차", "parking" → p-parking-basic
   │   └─ "램프", "ramp" → s-circulation-ramp
   └─ 매칭 실패 → unknown

5. 주차면 필터링 (--parking-only 플래그)
   ├─ p-parking-* → ✅ 포함
   ├─ marker-disabled → ✅ 포함
   ├─ s-circulation-* → ✅ 포함
   ├─ unknown + 면적 ≥5m² → ✅ 포함 (사용자 선택용)
   └─ 기타 (기둥, 설비 등) → ❌ 제외

6. JSON 출력
   └─ {blocks: [...], total_blocks: N}
```

**사용법**:
```bash
# 모든 블록 분석
python3 src/analyze_layers.py data/dxf/input.dxf --output data/json/analysis.json

# 주차면 관련 블록만 필터링
python3 src/analyze_layers.py data/dxf/input.dxf --parking-only --output data/json/parking_blocks.json
```

**출력 예시**:
```json
{
  "blocks": [
    {
      "name": "#배치도_지하주차장$0$확장형주차",
      "count": 1091,
      "sample_area": 13.52,
      "suggested_type": "p-parking-large"
    },
    {
      "name": "#배치도_지하주차장$0$p-일반",
      "count": 704,
      "sample_area": 12.5,
      "suggested_type": "p-parking-basic"
    }
  ],
  "total_blocks": 234
}
```

### 2. process_dxf.py

레이어 매핑 기반으로 DXF를 처리하고 CSV로 변환합니다.

**기능**:
- 중첩 블록의 좌표 변환 (Matrix44 누적)
- 장애인 마크 근처 주차면 자동 재분류
- 단위 변환 (mm → m) 및 좌표 정규화
- 표준화된 레이어 구조의 DXF 생성
- WKT 형식 CSV 출력

**처리 로직**:
```
STEP 1: DXF 파일에서 주차면 추출
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.1 레이어 매핑 로드
    └─ JSON 파일 읽기: {블록명: 레이어타입}
        예: "#배치도_지하주차장$0$확장형주차": "p-parking-large"

1.2 중첩 블록 구조 탐색 (extract_nested_blocks)
    ├─ ModelSpace → INSERT 엔티티
    │   └─ 메인 블록 (예: #배치도_지하주차장$0)
    │       └─ 서브 INSERT 엔티티
    │           └─ 실제 주차면 블록 (예: 확장형주차)
    │
    ├─ 좌표 변환 (Matrix44)
    │   ├─ 메인 블록 변환 행렬 (rotation, scale, translation)
    │   ├─ 서브 블록 변환 행렬
    │   └─ 누적 변환: 최종좌표 = 메인행렬 × 서브행렬 × 원본좌표
    │
    └─ LWPOLYLINE 추출
        ├─ 각 꼭짓점에 변환 행렬 적용
        ├─ 단위 변환: mm → m (/1000)
        └─ 레이어 매핑 적용: 블록명 → 표준 레이어명

1.3 장애인 주차 자동 재분류 (reclassify_disabled_parking)
    ├─ marker-disabled 엔티티 좌표 추출 (장애인 마크)
    ├─ 각 주차면과 장애인 마크 간 거리 계산
    │   └─ 거리 = √[(x1-x2)² + (y1-y2)²]
    └─ tolerance(기본 7m) 이내 주차면 → p-parking-disable로 변경
        예: 일반주차 68개 → 장애인주차로 재분류

STEP 2: 깨끗한 DXF 파일 생성
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.1 좌표 정규화 (normalize_coordinates)
    ├─ 모든 주차면의 최소 X, Y 좌표 찾기
    │   └─ min_x, min_y 계산
    ├─ 오프셋 적용
    │   └─ 새 좌표 = 원본 좌표 - (min_x, min_y)
    └─ 원점(0,0) 기준 좌표계로 정규화

2.2 새 DXF 문서 생성
    ├─ 표준 레이어 생성
    │   ├─ p-parking-basic (색상: #000000)
    │   ├─ p-parking-large (색상: #00FF00)
    │   ├─ p-parking-small (색상: #0000FF)
    │   ├─ p-parking-disable (색상: #FF0000)
    │   └─ p-parking-electric (색상: #FFFF00)
    │
    └─ LWPOLYLINE 엔티티 생성
        ├─ 레이어 지정
        ├─ 닫힌 폴리라인 (closed=True)
        └─ 정규화된 좌표 추가

STEP 3: DXF → CSV 변환
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.1 LWPOLYLINE → WKT 변환
    ├─ 각 폴리라인의 꼭짓점 추출
    ├─ WKT POLYGON 형식 생성
    │   └─ "POLYGON((x1 y1, x2 y2, x3 y3, x4 y4, x1 y1))"
    └─ 첫 점과 마지막 점 일치 확인 (닫힌 다각형)

3.2 CSV 행 생성
    ├─ 컬럼: X, Y, Z, Layer, PaperSpace, SubClasses, ...
    ├─ 각 꼭짓점마다 1개 행 생성
    └─ 폴리곤 구분: 빈 행으로 분리

3.3 CSV 파일 저장
    └─ UTF-8 인코딩, 헤더 포함

최종 출력:
  - processed.dxf: 표준화된 DXF (AutoCAD/QGIS)
  - output.csv: WKT 형식 CSV (웹 뷰어)
```

**사용법**:
```bash
# 기본 사용
python3 src/process_dxf.py data/dxf/central.dxf

# 레이어 매핑 사용
python3 src/process_dxf.py data/dxf/central.dxf \
  --layer-mapping data/json/mapping.json \
  --tolerance 7.0 \
  --output-dxf data/dxf/output.dxf \
  --output-csv data/csv/output.csv
```

**레이어 매핑 JSON 예시**:
```json
{
  "#배치도_지하주차장$0$확장형주차": "p-parking-large",
  "#배치도_지하주차장$0$p-일반": "p-parking-basic",
  "#배치도_지하주차장$0$p-경차": "p-parking-small",
  "#배치도_지하주차장$0$전기차 완속": "p-parking-electric",
  "#배치도_지하주차장$0$장애인전용주차": "marker-disabled"
}
```

**출력 예시**:
```
======================================================================
STEP 1: Central.dxf에서 주차면 추출
======================================================================
✅ 총 2122개 주차면/동선 추출 완료

장애인 주차 재분류 중 (tolerance=7.0m)...
  장애인 마크 발견: 68개
  재분류 완료: 85개 주차면 → 장애인 주차

레이어별 통계:
  일반주차 (p-parking-basic): 684개
  확장주차 (p-parking-large): 1081개
  경차주차 (p-parking-small): 128개
  장애인주차 (p-parking-disable): 85개
  전기차주차 (p-parking-electric): 114개
  택배주차 (p-parking-delivery): 20개

======================================================================
STEP 2: 깨끗한 DXF 파일 생성
======================================================================
✅ 저장 완료!

======================================================================
STEP 3: DXF → CSV 변환
======================================================================
✅ CSV 변환 완료!
```

## 🔧 설치 및 설정

### 사전 요구사항

- Python 3.9 이상
- Go 1.21 이상 (백엔드 구현 시)
- pip

### Python 환경 설정

```bash
# 저장소 클론
git clone https://github.com/JokerTrickster/map-editor.git
cd map-editor

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install ezdxf
```

### 프로젝트 구조

```
dxf-parser/
├── src/                         # Python 스크립트
│   ├── convert_dxf.py          # 🎯 통합 변환 스크립트 (추천)
│   ├── analyze_layers.py       # 레이어 분석
│   └── process_dxf.py  # CSV 변환
├── data/                        # 데이터 파일
│   ├── dxf/                     # DXF 원본 파일
│   ├── csv/                     # 생성된 CSV
│   └── json/                    # 레이어 매핑 JSON
├── venv/                        # Python 가상환경
└── README.md
```

### ⚡ 빠른 사용법 (추천)

**DXF 파일 하나만 입력하면 자동으로 CSV 생성:**

```bash
# 기본 사용 (가장 간단!)
python3 src/convert_dxf.py data/dxf/your_file.dxf

# 출력 파일명 지정
python3 src/convert_dxf.py data/dxf/your_file.dxf --output custom.csv

# 장애인 주차 재분류 거리 조정
python3 src/convert_dxf.py data/dxf/your_file.dxf --tolerance 5.0
```

**자동 처리 워크플로우:**
1. ✅ DXF 레이어 자동 분석
2. ✅ 주차면 블록만 자동 필터링
3. ✅ 레이어 매핑 자동 생성
4. ✅ CSV 자동 변환 및 저장

### 🔧 수동 사용법 (고급)

단계별로 직접 제어하고 싶을 때:

```bash
# 1. 레이어 분석
python3 src/analyze_layers.py data/dxf/your_file.dxf --output data/json/layers.json

# 2. 분석 결과 확인 및 매핑 JSON 생성
# (layers.json 참고하여 mapping.json 작성)

# 3. DXF 처리 및 CSV 생성
python3 src/process_dxf.py data/dxf/your_file.dxf \
  --layer-mapping data/json/mapping.json \
  --output-csv data/csv/result.csv
```

## 🔄 전체 워크플로우 (백엔드 연동 시)

### API 호출 흐름

```
1. 파일 업로드
   POST /api/v1/dxf/upload
   → Go: 파일 저장
   → Python: analyze_layers.py 실행
   ← 레이어 분석 결과 반환

2. 레이어 분석 결과 조회
   GET /api/v1/jobs/{id}/layers
   ← { blocks: [...], total_blocks: 234 }

3. 레이어 선택 및 처리 시작
   POST /api/v1/jobs/{id}/process
   { layer_mapping: {...}, options: {...} }
   → Go: Queue에 Job 추가
   → Worker: Python process_dxf.py 실행
   ← 처리 시작 응답

4. 상태 조회 (Polling)
   GET /api/v1/jobs/{id}
   ← { status: "completed", statistics: {...} }

5. 결과 다운로드
   GET /api/v1/files/xxx.csv
   ← CSV 파일
```

## 📊 출력 형식

### CSV 출력 예시

```csv
GeometryID,Layer,LayerName,WKT,VertexCount,Area_m2,Color
0,p-parking-large,확장주차,"POLYGON((481.30 200.77,...))",4,13.52,#00FF00
1,p-parking-basic,일반주차,"POLYGON((468.75 200.77,...))",4,12.50,#000000
```

### DXF 출력 특징

- 표준화된 레이어 구조 (`p-parking-*`, `s-circulation-*`)
- 닫힌 LWPOLYLINE으로 주차면 표현
- 좌표 정규화 (원점 기준)
- 단위: 미터(m)

## 📚 주요 알고리즘

### Shoelace 공식 (면적 계산)

주차면 폴리라인의 면적을 계산하기 위해 사용:

```python
area = 0
for i in range(len(vertices)):
    j = (i + 1) % len(vertices)
    area += vertices[i][0] * vertices[j][1]
    area -= vertices[j][0] * vertices[i][1]
area = abs(area) / 2.0
```

### Matrix44 변환 (중첩 블록)

DXF 중첩 블록의 좌표를 계산:

```python
# 1. 메인 블록 변환 행렬
main_matrix = main_insert.matrix44()

# 2. 서브 블록 변환 행렬
sub_matrix = sub_insert.matrix44()

# 3. 누적 변환 적용
final_matrix = main_matrix @ sub_matrix

# 4. 각 꼭짓점 변환
for vertex in vertices:
    transformed = final_matrix.transform(vertex)
```

### 거리 기반 재분류

장애인 마크 근처 주차면을 자동 재분류:

```python
# 유클리드 거리 계산
distance = math.sqrt(
    (parking_x - marker_x)**2 +
    (parking_y - marker_y)**2
)

# tolerance 이내면 재분류
if distance <= tolerance:
    parking_layer = 'p-parking-disable'
```

## 🎯 프로젝트 특징

### 도면별 커스터마이징

각 건설 도면은 고유한 블록 명명 규칙을 가지므로, 프로젝트별로 블록 매핑을 정의할 수 있습니다:

```python
# process_dxf.py - Central 프로젝트용
BLOCK_TO_LAYER = {
    'p-일반': 'p-parking-basic',
    '확장형주차': 'p-parking-large',
    '장애인전용주차': 'p-parking-disable',
    # ...
}
```

또는 JSON 파일로 외부에서 매핑을 제공할 수 있습니다.

### 장애인 주차 자동 재분류

장애인 마크 근처(기본 7m)의 일반 주차면을 자동으로 장애인 주차로 재분류합니다:

```bash
# tolerance 조정 가능
python3 src/process_dxf.py data/dxf/central.dxf --tolerance 5.0
```

### 좌표 정규화

모든 주차면 좌표를 원점 기준으로 정규화하여 뷰어에서 일관된 표시를 보장합니다.

## 🔍 기술 스택

### Python
- **ezdxf**: DXF 파일 파싱 및 조작
- **json**: 데이터 직렬화
- **argparse**: CLI 인터페이스

### Backend (구현 예정)
- **Go**: 고성능 HTTP 서버
- **Gin**: 웹 프레임워크
- **Channels**: 간단한 인메모리 큐

### Frontend (구현 예정)
- **React**: UI 프레임워크
- **Vite**: 빌드 도구
- **Axios**: HTTP 클라이언트
- **Tailwind CSS**: 스타일링

## 🤝 기여

이슈 리포트 및 Pull Request는 언제나 환영입니다!

## 📄 라이센스

MIT License

## 🔗 관련 링크

- Repository: https://github.com/JokerTrickster/map-editor
- ezdxf Documentation: https://ezdxf.readthedocs.io/
