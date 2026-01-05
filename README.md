# DXF Parking Space Extractor

## 📍 프로젝트 소개

### 개요
DXF Parking Space Extractor는 CAD 도면(DXF) 파일에서 주차면 정보를 자동으로 추출하고 표준화하는 지능형 Python 도구입니다. AI 기술과 기하학적 분석을 활용하여 복잡한 CAD 도면에서 주차 공간을 정확하게 식별하고 변환합니다.

## 🚀 주요 기능

### 주요 특징
- 다양한 DXF 파일에서 주차면 자동 추출
- 표준화된 레이어 구조로 변환
- AI 기반 블록 분류
- 다중 층 지원
- CSV 및 표준 DXF 형식으로 출력

### 지원하는 주차면 유형
- 일반 주차면
- 확장 주차면
- 경차 주차면
- 장애인 주차면
- 전기차 충전 주차면
- 가족배려 주차면

## 🛠 기술 스택

### 주요 기술
- **Language**: Python 3.9+
- **DXF 파싱**: ezdxf
- **API 프레임워크**: FastAPI
- **AI 분류**: Claude AI / OpenAI
- **타입 힌팅**: Python Typing
- **테스트**: pytest
- **코드 품질**: mypy, flake8, black

### 아키텍처
프로젝트는 클린 아키텍처 원칙을 따르며, 다음과 같은 레이어로 구성됩니다:

```
src/
├── core/           # 핵심 도메인 로직
│   └── dxf_parser.py
├── domain/         # 엔티티 및 추상화
│   └── entities/
├── application/    # 유스케이스 및 서비스
│   └── services/
├── infrastructure/ # 외부 인터페이스 구현
│   └── converters/
└── presentation/   # API 및 CLI 인터페이스
    ├── api/
    └── cli/
```

## 🔧 설치 및 설정

### 사전 요구사항
- Python 3.9 이상
- pip
- 가상 환경 (권장)

### 설치 단계
```bash
# 저장소 클론
git clone https://github.com/yourusername/dxf-parking-extractor.git
cd dxf-parking-extractor

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate

# 종속성 설치
pip install -r requirements.txt
```

## 🖥 사용 방법

### CLI 변환
```bash
# 기본 변환
python3 dxf_parking_extractor.py input.dxf

# 좌표 정규화
python3 dxf_parking_extractor.py input.dxf --normalize

# 특정 층 추출
python3 dxf_parking_extractor.py input.dxf --floor B1

# 출력 파일 지정
python3 dxf_parking_extractor.py input.dxf -o output.dxf -c output.csv
```

### FastAPI 서버 실행
```bash
uvicorn src.presentation.main:app --reload --port 7000
```

## 📊 출력 형식

### DXF 출력
- 표준화된 레이어 구조
- 닫힌 LWPOLYLINE으로 주차면 저장
- 주차면 ID 중앙 배치

### CSV 출력
| 컬럼 | 설명 |
|------|------|
| id | 주차면 일련번호 |
| layer | 레이어명 |
| type | 원본 주차면 타입 |
| center_x | 중심점 X 좌표 |
| center_y | 중심점 Y 좌표 |
| rotation | 회전 각도 |
| vertex_count | 꼭짓점 수 |
| vertices | 꼭짓점 좌표 |

## 🧪 테스트

### 테스트 실행
```bash
# 모든 테스트 실행
pytest tests/

# 특정 테스트 실행
pytest tests/test_api.py::test_convert_parking_spaces
```

## 🤝 기여 방법
1. 포크(Fork) 생성
2. 기능 브랜치 생성 (`git checkout -b feature/새로운기능`)
3. 변경사항 커밋 (`git commit -am '새로운 기능 추가'`)
4. 브랜치에 푸시 (`git push origin feature/새로운기능`)
5. 풀 리퀘스트 생성

## 📄 라이센스
[라이센스 정보 추가]

## 🐞 문제 신고
깃허브 이슈 트래커를 통해 버그나 기능 요청을 알려주세요.

## 🔍 참고 자료
- [ezdxf 문서](https://ezdxf.readthedocs.io/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)