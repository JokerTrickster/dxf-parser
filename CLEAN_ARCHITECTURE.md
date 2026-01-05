# Clean Architecture 설계

## 개요

DXF Parser 프로젝트를 Clean Architecture 원칙에 따라 재구성했습니다.

## Clean Architecture 계층

```
┌─────────────────────────────────────────────────────┐
│                  Presentation                        │
│              (API, CLI, Controllers)                 │
├─────────────────────────────────────────────────────┤
│                  Application                         │
│            (Use Cases, Services)                     │
├─────────────────────────────────────────────────────┤
│                    Domain                            │
│          (Entities, Interfaces)                      │
├─────────────────────────────────────────────────────┤
│                Infrastructure                        │
│    (DXF Parser, Classifiers, Converters)            │
└─────────────────────────────────────────────────────┘
```

## 의존성 규칙

**의존성 방향: 바깥 → 안쪽**

- ✅ Presentation → Application → Domain
- ✅ Infrastructure → Domain (인터페이스 구현)
- ❌ Domain → Infrastructure (절대 안됨!)
- ❌ Application → Presentation (절대 안됨!)

## 프로젝트 구조

```
src/
├── domain/                      # 핵심 비즈니스 규칙 (의존성 없음)
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── dxf_entity.py       # DXF 엔티티 (좌표, 타입 등)
│   │   ├── classification.py   # 분류 결과
│   │   └── layer_info.py       # 레이어 정보
│   └── repositories/            # 인터페이스 (추상 클래스)
│       ├── __init__.py
│       ├── dxf_repository.py   # DXF 읽기/쓰기 인터페이스
│       ├── converter_repository.py  # 변환 인터페이스
│       └── classifier_repository.py # 분류 인터페이스
│
├── application/                 # 애플리케이션 로직
│   ├── use_cases/
│   │   ├── __init__.py
│   │   ├── convert_dxf_to_csv.py      # CSV 변환 유즈케이스
│   │   ├── classify_entities.py       # 엔티티 분류 유즈케이스
│   │   └── extract_parking_spaces.py  # 주차면 추출 유즈케이스
│   ├── services/
│   │   ├── __init__.py
│   │   ├── classification_service.py  # 분류 서비스
│   │   └── geometry_service.py        # 기하학 연산 서비스
│   └── dto/
│       ├── __init__.py
│       ├── convert_request.py         # 변환 요청 DTO
│       └── convert_response.py        # 변환 응답 DTO
│
├── infrastructure/              # 외부 의존성 구현
│   ├── dxf/
│   │   ├── __init__.py
│   │   ├── ezdxf_repository.py        # ezdxf 기반 구현
│   │   ├── block_extractor.py         # 블록 추출
│   │   └── geometry_processor.py      # 기하학 처리
│   ├── classifiers/
│   │   ├── __init__.py
│   │   ├── llm_classifier.py          # LLM 분류기
│   │   ├── rule_based_classifier.py   # 규칙 기반 분류기
│   │   └── cache_manager.py           # 캐시 관리
│   ├── converters/
│   │   ├── __init__.py
│   │   └── mygeodata_csv_converter.py # MyGeoData CSV 변환기
│   └── persistence/
│       ├── __init__.py
│       └── file_system.py             # 파일 시스템 접근
│
└── presentation/                # 사용자 인터페이스
    ├── api/                     # FastAPI
    │   ├── __init__.py
    │   ├── dependencies.py      # DI 컨테이너
    │   ├── routes.py            # API 라우트
    │   └── schemas.py           # Pydantic 스키마
    ├── cli/                     # CLI 스크립트
    │   ├── __init__.py
    │   ├── convert_command.py   # 변환 CLI
    │   └── extract_command.py   # 추출 CLI
    └── main.py                  # FastAPI 앱
```

## 계층별 설명

### 1. Domain Layer (핵심)

**목적:** 비즈니스 규칙과 엔티티 정의

**특징:**
- 외부 의존성 없음 (순수 Python)
- 변경 빈도 가장 낮음
- 다른 계층의 기반

**주요 컴포넌트:**
- `DXFEntity`: DXF 엔티티 표현
- `Classification`: 분류 결과
- `IDXFRepository`: DXF 접근 인터페이스
- `IConverter`: 변환기 인터페이스

### 2. Application Layer (유즈케이스)

**목적:** 애플리케이션 비즈니스 로직

**특징:**
- Domain 계층만 의존
- 구체적인 구현 모름 (인터페이스 사용)
- 재사용 가능한 로직

**주요 유즈케이스:**
- `ConvertDXFToCSVUseCase`: DXF → CSV 변환 흐름
- `ClassifyEntitiesUseCase`: 엔티티 분류 흐름
- `ExtractParkingSpacesUseCase`: 주차면 추출 흐름

### 3. Infrastructure Layer (구현)

**목적:** 외부 기술 구현

**특징:**
- Domain 인터페이스 구현
- ezdxf, Claude API 등 외부 라이브러리 사용
- 교체 가능 (예: ezdxf → 다른 DXF 라이브러리)

**주요 구현:**
- `EzdxfRepository`: ezdxf 기반 DXF 처리
- `LLMClassifier`: Claude API 분류기
- `MyGeoDataCSVConverter`: CSV 변환기

### 4. Presentation Layer (인터페이스)

**목적:** 사용자 인터페이스 제공

**특징:**
- Application 계층 사용
- FastAPI, CLI 등 다양한 인터페이스
- 요청/응답 변환

**주요 컴포넌트:**
- `FastAPI Router`: RESTful API
- `CLI Commands`: 명령줄 인터페이스
- `Dependency Injection`: 의존성 주입

## 의존성 주입 (DI)

### FastAPI 예시

```python
# presentation/api/dependencies.py
from src.application.use_cases import ConvertDXFToCSVUseCase
from src.infrastructure.dxf import EzdxfRepository
from src.infrastructure.converters import MyGeoDataCSVConverter

def get_convert_use_case() -> ConvertDXFToCSVUseCase:
    dxf_repo = EzdxfRepository()
    converter = MyGeoDataCSVConverter()
    return ConvertDXFToCSVUseCase(dxf_repo, converter)

# presentation/api/routes.py
@router.post("/convert")
async def convert(
    file: UploadFile,
    use_case: ConvertDXFToCSVUseCase = Depends(get_convert_use_case)
):
    result = await use_case.execute(file.content, file.filename)
    return result
```

### CLI 예시

```python
# presentation/cli/convert_command.py
from src.application.use_cases import ConvertDXFToCSVUseCase
from src.infrastructure.dxf import EzdxfRepository
from src.infrastructure.converters import MyGeoDataCSVConverter

def main():
    # DI
    dxf_repo = EzdxfRepository()
    converter = MyGeoDataCSVConverter()
    use_case = ConvertDXFToCSVUseCase(dxf_repo, converter)

    # 실행
    result = use_case.execute(dxf_path, csv_path)
    print(f"변환 완료: {result.total_entities}개")
```

## 테스트 전략

### 1. Domain Layer 테스트

```python
# 순수 Python 로직만 테스트 (의존성 없음)
def test_dxf_entity_center():
    entity = DXFEntity(vertices=[(0,0), (10,0), (10,10), (0,10)])
    assert entity.center == (5, 5)
```

### 2. Application Layer 테스트

```python
# Mock 인터페이스로 테스트
def test_convert_use_case():
    mock_repo = Mock(IDXFRepository)
    mock_converter = Mock(IConverter)
    use_case = ConvertDXFToCSVUseCase(mock_repo, mock_converter)

    result = use_case.execute("test.dxf", "test.csv")
    assert result.success == True
```

### 3. Infrastructure Layer 테스트

```python
# 실제 라이브러리 통합 테스트
def test_ezdxf_repository():
    repo = EzdxfRepository()
    doc = repo.read("test.dxf")
    assert doc is not None
```

## 장점

### 1. 테스트 용이성 ⬆️
- Mock 인터페이스로 유닛 테스트
- 의존성 주입으로 격리된 테스트

### 2. 유지보수성 ⬆️
- 계층별 책임 분리
- 변경 영향 최소화

### 3. 확장성 ⬆️
- 새로운 인터페이스 추가 용이 (예: gRPC)
- 새로운 구현 교체 가능 (예: 다른 DXF 라이브러리)

### 4. 비즈니스 로직 보호 ⬆️
- Domain은 외부 변경에 영향 받지 않음
- 프레임워크 독립적

## 마이그레이션 경로

### ✅ 단계 1: Domain 계층 분리 (완료)
- `src/models/` → `src/domain/entities/`
- 인터페이스 정의 (`src/domain/repositories/`)
- 하위 호환성 래퍼 유지

### ✅ 단계 2: Application 계층 생성 (완료)
- 유즈케이스 추출 (`src/application/use_cases/`)
- 서비스 분리 (`src/application/services/`)
- DTO 정의 (`src/application/dto/`)

### ✅ 단계 3: Infrastructure 재구성 (완료)
- `src/converters/` → `src/infrastructure/converters/`
- IConverter 인터페이스 구현
- 하위 호환성 래퍼 유지

### ✅ 단계 4: Presentation 분리 (완료)
- 새로운 `src/presentation/api/` 생성
- 새로운 `src/presentation/cli/` 생성
- `app/main.py`가 새로운 presentation layer 사용
- 의존성 주입 패턴 적용

### 📝 참고: 기존 코드 유지
- `src/core/`, `src/ai/`: 현재 위치 유지 (향후 마이그레이션 가능)
- 모든 하위 호환성 래퍼 동작 확인 완료
- 테스트 결과: 100% 동일한 출력 (MD5 검증 완료)

## 비교: Before vs After

### Before (기존 구조)
```
src/
├── core/           # 혼재된 책임
├── ai/             # 분류기
├── models/         # 데이터 모델
└── converters/     # 변환기
```

**문제점:**
- 계층 경계 불명확
- 의존성 방향 혼재
- 테스트 어려움

### After (Clean Architecture)
```
src/
├── domain/         # 비즈니스 규칙 (독립)
├── application/    # 유즈케이스 (재사용)
├── infrastructure/ # 구현 (교체 가능)
└── presentation/   # 인터페이스 (확장 가능)
```

**개선점:**
- ✅ 명확한 계층 분리
- ✅ 단방향 의존성
- ✅ 테스트 용이
- ✅ 확장 가능

## 참고 자료

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [FastAPI with Clean Architecture](https://github.com/zhanymkanov/fastapi-best-practices)
- [Python Clean Architecture Example](https://github.com/Enforcer/clean-architecture)
