# DXF to CSV Converter FastAPI Server

DXF 파일을 MyGeoData.cloud 형식의 CSV로 변환하는 FastAPI 기반 RESTful API 서버입니다.

## 기능

- ✅ DXF 파일 업로드 및 CSV 변환
- ✅ 변환 전 DXF 파일 정보 조회
- ✅ RESTful API 제공
- ✅ Docker 컨테이너 지원
- ✅ 자동 API 문서 (Swagger UI)
- ✅ 헬스체크 엔드포인트

## 빠른 시작

### 1. 로컬 개발 환경

```bash
# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python -m app.main

# 또는 uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 7000
```

서버 시작 후 접속:
- API: http://localhost:7000
- Swagger 문서: http://localhost:7000/docs
- ReDoc 문서: http://localhost:7000/redoc

### 2. Docker 실행

```bash
# Docker 이미지 빌드
docker build -t dxf-converter .

# 컨테이너 실행
docker run -p 7000:7000 dxf-converter
```

### 3. Docker Compose 실행 (추천)

```bash
# 서비스 시작
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 서비스 중지
docker-compose down
```

## API 엔드포인트

### 1. 서버 상태 확인

```bash
GET /api/v1/
```

**응답:**
```json
{
  "service": "DXF to CSV Converter",
  "version": "1.0.0",
  "status": "running"
}
```

### 2. 헬스체크

```bash
GET /api/v1/health
```

**응답:**
```json
{
  "status": "healthy"
}
```

### 3. DXF → CSV 변환

```bash
POST /api/v1/convert
Content-Type: multipart/form-data

file: <DXF 파일>
```

**cURL 예시:**
```bash
curl -X POST "http://localhost:7000/api/v1/convert" \
  -F "file=@osong-b1.dxf" \
  -o output.csv
```

**Python 예시:**
```python
import requests

url = "http://localhost:7000/api/v1/convert"
files = {"file": open("osong-b1.dxf", "rb")}

response = requests.post(url, files=files)

if response.status_code == 200:
    with open("output.csv", "wb") as f:
        f.write(response.content)
    print("변환 완료!")
```

**Go 예시:**
```go
package main

import (
    "bytes"
    "io"
    "mime/multipart"
    "net/http"
    "os"
)

func convertDXF(dxfPath, csvPath string) error {
    // 파일 열기
    file, err := os.Open(dxfPath)
    if err != nil {
        return err
    }
    defer file.Close()

    // Multipart form 생성
    body := &bytes.Buffer{}
    writer := multipart.NewWriter(body)
    part, err := writer.CreateFormFile("file", dxfPath)
    if err != nil {
        return err
    }
    io.Copy(part, file)
    writer.Close()

    // API 요청
    req, err := http.NewRequest("POST", "http://localhost:7000/api/v1/convert", body)
    if err != nil {
        return err
    }
    req.Header.Set("Content-Type", writer.FormDataContentType())

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()

    // CSV 파일 저장
    out, err := os.Create(csvPath)
    if err != nil {
        return err
    }
    defer out.Close()

    _, err = io.Copy(out, resp.Body)
    return err
}
```

**응답:**
- Status: 200 OK
- Content-Type: text/csv
- Body: CSV 파일 내용

**에러 응답:**
```json
{
  "detail": "DXF 파일만 업로드 가능합니다. (.dxf 확장자 필요)"
}
```

### 4. DXF 파일 정보 조회

```bash
POST /api/v1/convert/info
Content-Type: multipart/form-data

file: <DXF 파일>
```

**cURL 예시:**
```bash
curl -X POST "http://localhost:7000/api/v1/convert/info" \
  -F "file=@osong-b1.dxf"
```

**응답:**
```json
{
  "filename": "osong-b1.dxf",
  "total_entities": 5706,
  "entity_types": {
    "LINE": 4045,
    "LWPOLYLINE": 1640,
    "ARC": 21
  },
  "layers": {
    "building-outline": 4258,
    "p-parking-basic": 639,
    "p-parking-large": 492,
    "p-parking-large-women": 95,
    "p-parking-small": 93,
    "p-parking-large-electric": 84,
    "p-parking-disable": 45
  },
  "dxf_version": "AC1021"
}
```

## 프로젝트 구조

```
dxf-parser/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 애플리케이션
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API 라우트 정의
│   └── services/
│       ├── __init__.py
│       └── converter.py     # 변환 로직
├── dxf_to_mygeodata_csv.py  # 변환 스크립트 (재사용)
├── Dockerfile               # Docker 이미지 정의
├── docker-compose.yml       # Docker Compose 설정
├── requirements.txt         # Python 의존성
└── FASTAPI_README.md        # 이 문서
```

## 환경 변수

```bash
# 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=info

# 서버 설정 (docker-compose에서 자동 설정)
PYTHONUNBUFFERED=1
```

## Docker 배포

### 프로덕션 배포

```bash
# 이미지 빌드
docker build -t dxf-converter:latest .

# 컨테이너 실행 (프로덕션)
docker run -d \
  --name dxf-converter \
  -p 7000:7000 \
  --restart unless-stopped \
  dxf-converter:latest
```

### Docker Hub 배포

```bash
# 태그 지정
docker tag dxf-converter:latest yourusername/dxf-converter:latest

# 푸시
docker push yourusername/dxf-converter:latest
```

## Go 백엔드 통합

### Go 서버에서 FastAPI 호출

```go
package main

import (
    "bytes"
    "encoding/json"
    "io"
    "mime/multipart"
    "net/http"
)

// DXF 변환 서비스 클라이언트
type DXFConverterClient struct {
    BaseURL string
}

func NewDXFConverterClient(baseURL string) *DXFConverterClient {
    return &DXFConverterClient{BaseURL: baseURL}
}

// DXF를 CSV로 변환
func (c *DXFConverterClient) Convert(dxfData []byte, filename string) ([]byte, error) {
    body := &bytes.Buffer{}
    writer := multipart.NewWriter(body)

    part, err := writer.CreateFormFile("file", filename)
    if err != nil {
        return nil, err
    }

    _, err = io.Copy(part, bytes.NewReader(dxfData))
    if err != nil {
        return nil, err
    }
    writer.Close()

    req, err := http.NewRequest("POST", c.BaseURL+"/api/v1/convert", body)
    if err != nil {
        return nil, err
    }
    req.Header.Set("Content-Type", writer.FormDataContentType())

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    return io.ReadAll(resp.Body)
}

// DXF 파일 정보 조회
func (c *DXFConverterClient) GetInfo(dxfData []byte, filename string) (map[string]interface{}, error) {
    body := &bytes.Buffer{}
    writer := multipart.NewWriter(body)

    part, err := writer.CreateFormFile("file", filename)
    if err != nil {
        return nil, err
    }

    _, err = io.Copy(part, bytes.NewReader(dxfData))
    if err != nil {
        return nil, err
    }
    writer.Close()

    req, err := http.NewRequest("POST", c.BaseURL+"/api/v1/convert/info", body)
    if err != nil {
        return nil, err
    }
    req.Header.Set("Content-Type", writer.FormDataContentType())

    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()

    var info map[string]interface{}
    err = json.NewDecoder(resp.Body).Decode(&info)
    return info, err
}

// 사용 예시
func main() {
    client := NewDXFConverterClient("http://localhost:7000")

    // DXF 파일 읽기
    dxfData, _ := os.ReadFile("input.dxf")

    // CSV로 변환
    csvData, err := client.Convert(dxfData, "input.dxf")
    if err != nil {
        log.Fatal(err)
    }

    // CSV 파일 저장
    os.WriteFile("output.csv", csvData, 0644)
}
```

### Docker Compose에서 Go + Python 함께 실행

```yaml
version: '3.8'

services:
  # Go 백엔드
  go-backend:
    build: ./go-backend
    ports:
      - "3000:3000"
    environment:
      - DXF_CONVERTER_URL=http://dxf-converter:7000
    depends_on:
      - dxf-converter

  # Python DXF 변환 서비스
  dxf-converter:
    build: ./dxf-parser
    expose:
      - "7000"
    restart: unless-stopped
```

## 성능

- **첫 요청**: ~200ms (Python 프로세스 워밍업)
- **이후 요청**: ~50-100ms (파일 크기에 따라)
- **동시 처리**: Uvicorn 워커 수에 따라 조절 가능

### 성능 최적화 옵션

```bash
# 멀티 워커로 실행 (프로덕션)
uvicorn app.main:app --host 0.0.0.0 --port 7000 --workers 4

# Docker Compose에서 워커 설정
services:
  dxf-converter:
    command: uvicorn app.main:app --host 0.0.0.0 --port 7000 --workers 4
```

## 모니터링

### 헬스체크

Docker Compose는 자동으로 헬스체크를 수행합니다:

```bash
# 컨테이너 상태 확인
docker-compose ps

# 헬스체크 로그
docker inspect dxf-converter-api | grep Health
```

### 로그 확인

```bash
# 실시간 로그
docker-compose logs -f dxf-converter

# 최근 100줄
docker-compose logs --tail=100 dxf-converter
```

## 문제 해결

### 포트 충돌

```bash
# 다른 포트 사용
docker-compose up -d -p 8001:7000
```

### 메모리 부족

```bash
# 메모리 제한 설정
docker run -m 512m -p 7000:7000 dxf-converter
```

### 변환 실패

로그를 확인하여 구체적인 오류 메시지를 확인하세요:

```bash
docker-compose logs dxf-converter
```

## 라이선스

이 프로젝트의 라이선스를 따릅니다.

## 참고

- FastAPI 문서: https://fastapi.tiangolo.com/
- Uvicorn 문서: https://www.uvicorn.org/
- Docker 문서: https://docs.docker.com/
