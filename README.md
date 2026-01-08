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
└─────────────┘  - process_central_dxf.py
```

**Python은 별도 서버 구동 없이** Go 백엔드가 필요할 때마다 subprocess로 실행합니다.

## 🐍 Python 스크립트

### 1. analyze_layers.py

DXF 파일의 모든 블록을 분석하고 AI가 타입을 추정합니다.

**기능**:
- 모든 INSERT 블록 추출 및 사용 횟수 카운트
- LWPOLYLINE 면적 계산 (mm² → m²)
- 블록명 + 면적 기반 AI 타입 추정
- JSON 결과 출력

**사용법**:
```bash
python3 analyze_layers.py input.dxf --output analysis.json
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

### 2. process_central_dxf.py

레이어 매핑 기반으로 DXF를 처리하고 CSV로 변환합니다.

**기능**:
- 중첩 블록의 좌표 변환 (Matrix44 누적)
- 장애인 마크 근처 주차면 자동 재분류
- 단위 변환 (mm → m) 및 좌표 정규화
- 표준화된 레이어 구조의 DXF 생성
- WKT 형식 CSV 출력

**사용법**:
```bash
# 기본 사용
python3 process_central_dxf.py central.dxf

# 레이어 매핑 사용
python3 process_central_dxf.py central.dxf \
  --layer-mapping mapping.json \
  --tolerance 7.0 \
  --output-dxf output.dxf \
  --output-csv output.csv
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

### Python 스크립트 단독 사용

```bash
# 1. 레이어 분석
python3 analyze_layers.py your_file.dxf --output layers.json

# 2. 분석 결과 확인 및 매핑 JSON 생성
# (layers.json 참고하여 mapping.json 작성)

# 3. DXF 처리 및 CSV 생성
python3 process_central_dxf.py your_file.dxf \
  --layer-mapping mapping.json \
  --output-csv result.csv
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
   → Worker: Python process_central_dxf.py 실행
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

## 📚 문서

상세 구현 가이드:
- **[BACKEND_IMPLEMENTATION.md](BACKEND_IMPLEMENTATION.md)**: Go 백엔드 구현 가이드
- **[FRONTEND_IMPLEMENTATION.md](FRONTEND_IMPLEMENTATION.md)**: React 프론트엔드 구현 가이드
- **[IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)**: 현재 구현 상태 및 진행 상황

아키텍처 문서:
- **[SIMPLE_QUEUE_IMPLEMENTATION.md](SIMPLE_QUEUE_IMPLEMENTATION.md)**: Go 채널 기반 큐 구현
- **[DXF_PROCESSING_ARCHITECTURE.md](DXF_PROCESSING_ARCHITECTURE.md)**: 전체 시스템 아키텍처

## 🎯 프로젝트 특징

### 도면별 커스터마이징

각 건설 도면은 고유한 블록 명명 규칙을 가지므로, 프로젝트별로 블록 매핑을 정의할 수 있습니다:

```python
# process_central_dxf.py - Central 프로젝트용
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
python3 process_central_dxf.py central.dxf --tolerance 5.0
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
