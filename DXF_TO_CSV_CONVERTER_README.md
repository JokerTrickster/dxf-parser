# DXF to MyGeoData CSV Converter

DXF 파일을 MyGeoData.cloud와 동일한 형식의 CSV 파일로 변환하는 도구입니다.

## 개요

이 도구는 `osong-b1_B1_converted.dxf`와 같은 DXF 파일을 MyGeoData.cloud 웹 서비스와 동일한 형식의 CSV 파일로 변환합니다. 웹 서비스를 사용하지 않고도 로컬에서 자동으로 변환할 수 있습니다.

## 기능

- **LWPOLYLINE 변환**: 주차면, 구역 등의 폴리곤 데이터
- **LINE 변환**: 건물 외곽선 등의 선 데이터
- **ARC 변환**: 곡선 데이터 (32개 점으로 근사)
- **레이어별 색상 코딩**: 레이어 이름에 따라 자동으로 색상 할당
- **MyGeoData 형식**: EntityHandle 따옴표, 좌표 정밀도 등 형식 준수

## 사용법

### 기본 사용
```bash
source venv/bin/activate
python dxf_to_mygeodata_csv.py <입력.dxf> <출력.csv>
```

### 예시
```bash
# osong-b1_B1_converted.dxf를 osong-b1_B1_converted_self.csv로 변환
python dxf_to_mygeodata_csv.py osong-b1_B1_converted.dxf osong-b1_B1_converted_self.csv
```

## 출력 형식

CSV 파일은 다음과 같은 컬럼으로 구성됩니다:

| 컬럼 | 설명 | 예시 |
|------|------|------|
| X | X 좌표 | 203000.000000022 |
| Y | Y 좌표 | 95804.491351194 |
| Z | Z 좌표 (2D 도면은 0) | 0 |
| Layer | 레이어 이름 | p-parking-basic |
| PaperSpace | 페이퍼 스페이스 (비어있음) | |
| SubClasses | AutoCAD 서브클래스 | AcDbEntity:AcDbPolyline |
| Linetype | 라인 타입 (비어있음) | |
| EntityHandle | 엔티티 핸들 (16진수) | "36" |
| Text | 텍스트 (비어있음) | |
| OGR_STYLE | OGR 스타일 (색상 정보) | PEN(c:#000000) |

## 레이어별 색상 매핑

```python
'p-parking-basic': '#000000',       # 흰색/검은색
'p-parking-large': '#00ff00',       # 초록색
'p-parking-disable': '#ff0000',     # 빨간색
'p-parking-disabled': '#ff0000',    # 빨간색
'p-parking-small': '#ffff00',       # 노란색
'p-parking-compact': '#ffff00',     # 노란색
'p-parking-electric': '#0000ff',    # 파란색
'p-parking-large-electric': '#0000ff',  # 파란색
'p-parking-women': '#ff00ff',       # 마젠타
'p-parking-large-women': '#ff00ff', # 마젠타
's-structure-column': '#00ffff',    # 시안
's-structure-wall': '#808080',      # 회색
'c-circulation-stairs': '#ffa500',  # 주황색
'building-outline': '#808080',      # 회색
```

## 처리 방식

### LWPOLYLINE
- 각 꼭짓점을 개별 CSV 행으로 출력
- 닫힌 폴리곤의 경우 첫 점을 마지막에 반복

### LINE
- 시작점과 끝점 2개 행으로 출력
- SubClasses: `AcDbEntity:AcDbLine`

### ARC
- 32개 점으로 근사하여 출력
- SubClasses: `AcDbEntity:AcDbCircle:AcDbArc`

## MyGeoData.cloud와의 비교

### 동일한 점
- ✅ CSV 컬럼 구조
- ✅ EntityHandle 따옴표 처리 ("36")
- ✅ 레이어별 색상 코딩
- ✅ SubClasses 형식
- ✅ 폴리곤 닫힘 처리 (첫 점 = 마지막 점)

### 차이점
- 📍 **부동소수점 정밀도**:
  - MyGeoData: `203000.000000022`, `95804.491351194`
  - 우리 도구: `203000.000000022352`, `95804.491351193981`
  - **영향**: 매우 미미한 차이 (마이크로미터 단위). GIS 시스템에서는 실질적으로 동일하게 처리됩니다.

- 📊 **행 수 차이**:
  - MyGeoData: 16,675 행 (헤더 포함)
  - 우리 도구: 16,879 행 (헤더 포함)
  - **원인**: ARC 엔티티를 32개 점으로 근사하는 방식의 차이 (204행 차이)

## 통계

### osong-b1_B1_converted.dxf 변환 결과
```
처리된 엔티티: 5,706개
  - LWPOLYLINE: 1,640개
  - LINE: 4,045개
  - ARC: 21개

출력 행 수: 16,878개 (헤더 제외)
```

### 레이어별 분포
```
building-outline: 4,258개
p-parking-basic: 639개
p-parking-large: 492개
p-parking-large-women: 95개
p-parking-small: 93개
p-parking-large-electric: 84개
p-parking-disable: 45개
```

## 의존성

- Python 3.x
- ezdxf: DXF 파일 읽기/쓰기

## 주의사항

1. **가상환경 활성화**: 반드시 `source venv/bin/activate` 실행 후 사용
2. **절대 경로**: 입력/출력 파일 경로는 절대 경로 또는 현재 디렉토리 기준 상대 경로
3. **메모리**: 대용량 DXF 파일(>100MB)은 메모리 사용량이 높을 수 있음

## 확장

새로운 레이어 색상을 추가하려면 `get_layer_color_hex()` 함수의 `color_map` 딕셔너리를 수정하세요:

```python
color_map = {
    'your-new-layer': '#rrggbb',  # RGB 색상 코드
    ...
}
```

## 라이선스

이 프로젝트의 라이선스를 따릅니다.

## 참고

- DXF 형식: AutoCAD R2010
- CSV 인코딩: UTF-8
- 좌표계: DXF 파일의 원본 좌표계 유지
