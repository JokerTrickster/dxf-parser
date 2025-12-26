# 마이그레이션 가이드

기존 `dxf_parking_extractor.py`에서 새로운 `dxf_ai_extractor.py`로 전환

## 주요 변경사항

### 1. 명령어 변경

**기존:**
```bash
python dxf_parking_extractor.py osong-b1.dxf -o output.dxf
```

**신규:**
```bash
python3 dxf_ai_extractor.py osong-b1.dxf -o output.dxf
```

### 2. 환경 설정 필요

**신규 시스템은 API 키가 필요합니다:**

```bash
# .env 파일 생성
cp .env.example .env

# API 키 설정
# ANTHROPIC_API_KEY=sk-ant-your-actual-key
```

### 3. 출력 레이어명 변경

**기존:**
- `p-parking-basic`
- `p-parking-disable`
- `p-parking-large`
- ...

**신규:**
- `p-parking-basic` (동일)
- `p-parking-disabled` (disable → disabled)
- `p-parking-large` (동일)
- + 구조물: `s-structure-column`, `s-structure-wall`
- + 동선: `c-circulation-entrance`, `c-circulation-stairs`
- + 시설: `f-facility-room`, `f-facility-mechanical`

### 4. CSV 출력 형식 확장

**추가된 컬럼:**
- `category`: 카테고리 (parking/structure/circulation/facility)
- `confidence`: 분류 확신도 (0.0~1.0)
- `reasoning`: 분류 근거

### 5. 새로운 기능

#### 5.1 다중 레이어 지원
```bash
# 기존: 주차면만
# 신규: 주차면 + 기둥 + 벽 + 출입구 + ...
python3 dxf_ai_extractor.py input.dxf
```

#### 5.2 캐싱 시스템
```bash
# 첫 실행: API 호출 (유료)
python3 dxf_ai_extractor.py input.dxf

# 두 번째 실행: 캐시 사용 (무료)
python3 dxf_ai_extractor.py input.dxf
```

#### 5.3 통계 출력
```bash
python3 dxf_ai_extractor.py input.dxf --stats
```

출력 예시:
```
=== 분류 통계 ===
총 요청: 100
캐시 히트: 0
API 호출: 100
캐시 히트율: 0.0%

카테고리별 분포:
  parking: 75
  structure: 20
  circulation: 5
```

## 호환성 유지

### 기존 코드 유지
`dxf_parking_extractor.py`는 그대로 유지되며 동일하게 작동합니다.

### 점진적 전환
1. **1단계**: 기존 코드로 계속 작업
2. **2단계**: 신규 시스템 병렬 테스트
3. **3단계**: 검증 후 완전 전환

### 비용 고려사항

| 항목 | 기존 | 신규 |
|------|------|------|
| 초기 비용 | $0 | ~$0.05/1000블록 |
| 반복 실행 | $0 | ~$0 (캐싱) |
| 확장성 | 제한적 | 무제한 |
| 정확도 | 규칙 기반 | AI 기반 (높음) |

**권장**: 소규모 테스트 → 캐시 구축 → 대량 작업

## 예제 워크플로우

### 워크플로우 1: 주차면만 추출 (기존 방식)
```bash
python dxf_parking_extractor.py osong-b1.dxf
```
→ 변경 없음, 기존대로 사용

### 워크플로우 2: 모든 레이어 추출 (신규)
```bash
# 1. 환경 설정 (최초 1회)
cp .env.example .env
# .env 편집하여 API 키 입력

# 2. 가상환경 생성 (최초 1회)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 실행
python3 dxf_ai_extractor.py osong-b1.dxf --stats

# 4. 출력 확인
# - osong-b1_converted.dxf
# - osong-b1_layers.csv
```

### 워크플로우 3: 대량 도면 처리
```bash
# 첫 도면: 캐시 구축
python3 dxf_ai_extractor.py drawing1.dxf

# 이후 도면: 캐시 활용 (무료)
python3 dxf_ai_extractor.py drawing2.dxf
python3 dxf_ai_extractor.py drawing3.dxf

# 캐시 통계 확인
python3 dxf_ai_extractor.py drawing4.dxf --stats
```

## 문제 해결

### Q1. 기존 스크립트가 갑자기 안 됩니다
→ 기존 `dxf_parking_extractor.py`는 변경 없음
→ `ezdxf` 라이브러리 확인

### Q2. 신규 시스템 비용이 부담됩니다
→ 캐싱 활성화 (기본값)
→ 첫 실행만 유료, 이후 무료
→ 소규모 테스트로 시작

### Q3. API 키가 없습니다
→ https://console.anthropic.com/ 에서 발급
→ 무료 크레딧 활용 가능

### Q4. 분류가 부정확합니다
→ `config/layer_categories.yaml` 수정
→ 캐시 초기화: `--clear-cache`
→ 로그 확인: `--log-level DEBUG`

## 롤백

신규 시스템에 문제가 있다면:

```bash
# 기존 시스템으로 즉시 복귀
python dxf_parking_extractor.py input.dxf
```

기존 코드는 전혀 변경되지 않았으므로 언제든 복귀 가능합니다.
