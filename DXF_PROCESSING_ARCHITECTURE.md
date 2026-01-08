# DXF 파일 처리 백엔드 아키텍처 설계

## 목차
- [개요](#개요)
- [전체 아키텍처](#전체-아키텍처)
- [구현 방식 비교](#구현-방식-비교)
- [API 명세](#api-명세)
- [Go 구현 예시](#go-구현-예시)
- [Python Worker 구성](#python-worker-구성)
- [기술 스택](#기술-스택)
- [단계별 구현 로드맵](#단계별-구현-로드맵)

---

## 개요

건설 도면 DXF 파일을 처리하여 주차면 데이터를 추출하고 맵으로 렌더링하는 시스템의 백엔드 아키텍처입니다.

### 주요 요구사항
- 클라이언트에서 DXF 파일 업로드
- Go 백엔드에서 요청 수신
- Python 스크립트로 DXF 처리 (주차면 추출, CSV 변환)
- CSV 파일 기반 맵 데이터 제공
- 장애인 주차 등 특수 주차면 자동 분류

### 기술적 고려사항
- DXF 파일 처리 시간: 대용량 파일의 경우 10초 ~ 1분 소요
- 동시 요청 처리 필요
- 진행률 표시 필요
- 에러 핸들링 및 재시도 로직

---

## 전체 아키텍처

### 비동기 Job Queue 방식 (권장)

```
┌──────────────┐
│   Client     │
│   (Web/App)  │
└──────┬───────┘
       │ 1. POST /api/dxf/upload
       ↓
┌──────────────────────────────────────────┐
│           Go API Server                   │
│  ┌────────────────────────────────────┐  │
│  │  HTTP Handlers                     │  │
│  │  - Upload DXF                      │  │
│  │  - Get Job Status                  │  │
│  │  - Get Result (CSV/Map Data)      │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │  Services                          │  │
│  │  - Job Manager                     │  │
│  │  - File Manager                    │  │
│  │  - CSV Parser                      │  │
│  └────────────────────────────────────┘  │
└───────────┬──────────────────────────────┘
            │
            │ 2. Enqueue Job
            ↓
    ┌──────────────┐
    │  Job Queue   │
    │   (Redis)    │
    └──────┬───────┘
            │ 3. Dequeue Job
            ↓
    ┌──────────────────────┐
    │  Python Worker       │
    │  (Background Service)│
    │                      │
    │  process_central_dxf.py
    │  - DXF 파싱         │
    │  - 주차면 추출       │
    │  - 좌표 정규화       │
    │  - 장애인 주차 분류  │
    │  - CSV 변환         │
    └──────┬───────────────┘
            │ 4. Save Result
            ↓
    ┌──────────────┐      ┌──────────────┐
    │   Database   │      │ File Storage │
    │ (PostgreSQL) │      │  (S3/Local)  │
    │              │      │              │
    │ - Job Info   │      │ - DXF files  │
    │ - Status     │      │ - CSV files  │
    │ - Metadata   │      │              │
    └──────────────┘      └──────────────┘
```

---

## 구현 방식 비교

### 1. 동기 방식 (Synchronous)

**장점:**
- 구현 간단
- 즉시 결과 반환
- 별도 인프라 불필요

**단점:**
- HTTP 타임아웃 위험 (30초 ~ 60초)
- 동시 요청 처리 제한
- 사용자 대기 시간 김

**적합한 경우:**
- 프로토타입/MVP
- 파일 크기 작음 (< 10MB)
- 동시 사용자 적음 (< 10명)

---

### 2. 비동기 Job Queue 방식 (Asynchronous) ⭐ 권장

**장점:**
- HTTP 타임아웃 회피
- 수평 확장 가능 (Worker 추가)
- 진행률 추적 가능
- 재시도 로직 구현 용이

**단점:**
- 구현 복잡도 증가
- Redis 등 추가 인프라 필요
- 에러 처리 복잡

**적합한 경우:**
- Production 환경
- 대용량 파일 처리
- 동시 사용자 다수

---

### 3. 스트리밍 방식 (WebSocket/SSE)

**장점:**
- 실시간 진행률 업데이트
- 사용자 경험 향상

**단점:**
- 구현 가장 복잡
- 연결 관리 필요

**적합한 경우:**
- 고급 사용자 경험 필요
- 실시간 피드백 중요

---

## API 명세

### 1. DXF 파일 업로드

**Endpoint:**
```
POST /api/v1/dxf/upload
```

**Request:**
```http
Content-Type: multipart/form-data

{
  "file": <DXF binary>,
  "options": {
    "normalize": true,
    "tolerance": 7.0
  }
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "status_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-08T15:30:00Z"
}
```

---

### 2. Job 상태 조회

**Endpoint:**
```
GET /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 65,
  "current_step": "장애인 주차 재분류 중",
  "created_at": "2026-01-08T15:30:00Z",
  "updated_at": "2026-01-08T15:30:25Z",
  "estimated_completion": "2026-01-08T15:31:00Z"
}
```

**Status 값:**
- `pending`: 대기 중
- `processing`: 처리 중
- `completed`: 완료
- `failed`: 실패

---

### 3. 처리 결과 조회

**Endpoint:**
```
GET /api/v1/jobs/{job_id}/result
```

**Response (성공):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "files": {
    "csv": "/api/v1/files/550e8400_processed.csv",
    "dxf": "/api/v1/files/550e8400_processed.dxf"
  },
  "statistics": {
    "total_parkings": 2122,
    "layers": {
      "p-parking-basic": 684,
      "p-parking-delivery": 20,
      "p-parking-disable": 85,
      "p-parking-electric": 114,
      "p-parking-large": 1081,
      "p-parking-small": 128,
      "s-circulation-ramp": 10
    }
  }
}
```

**Response (실패):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "failed",
  "error": {
    "code": "INVALID_DXF_FORMAT",
    "message": "DXF 파일 형식이 올바르지 않습니다",
    "details": "Block A$C3CD3280F not found"
  }
}
```

---

### 4. 맵 데이터 조회 (CSV → JSON)

**Endpoint:**
```
GET /api/v1/jobs/{job_id}/map-data
```

**Query Parameters:**
- `layers`: 필터링할 레이어 (comma-separated)
  - 예: `?layers=p-parking-disable,p-parking-electric`

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "bounds": {
    "min_x": 0.0,
    "min_y": 0.0,
    "max_x": 335.84,
    "max_y": 235.41
  },
  "layers": {
    "p-parking-disable": [
      {
        "id": "57B",
        "type": "polygon",
        "coordinates": [
          [6.20, 117.26],
          [0.70, 117.26],
          [0.70, 119.96],
          [6.20, 119.96],
          [6.20, 117.26]
        ],
        "style": {
          "color": "#FF0000",
          "fill": true
        }
      }
    ],
    "p-parking-basic": [...]
  }
}
```

---

## Go 구현 예시

### 프로젝트 구조

```
backend/
├── cmd/
│   ├── api/
│   │   └── main.go              # API 서버 진입점
│   └── worker/
│       └── main.go              # Worker 진입점
├── internal/
│   ├── api/
│   │   ├── handler/
│   │   │   ├── dxf.go          # DXF 업로드 핸들러
│   │   │   ├── job.go          # Job 상태 핸들러
│   │   │   └── map.go          # 맵 데이터 핸들러
│   │   └── middleware/
│   │       └── auth.go
│   ├── service/
│   │   ├── job.go              # Job 관리 서비스
│   │   ├── storage.go          # 파일 저장소 서비스
│   │   └── parser.go           # CSV 파싱 서비스
│   ├── worker/
│   │   └── processor.go        # Python 실행 Worker
│   ├── repository/
│   │   └── job.go              # Job DB 저장소
│   └── model/
│       ├── job.go
│       └── map_data.go
├── pkg/
│   └── queue/
│       └── redis.go            # Redis Queue 래퍼
├── scripts/
│   └── process_central_dxf.py  # Python 처리 스크립트
└── go.mod
```

---

### main.go (API Server)

```go
package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/hibiken/asynq"
    "github.com/yourusername/dxf-processor/internal/api/handler"
    "github.com/yourusername/dxf-processor/internal/repository"
    "github.com/yourusername/dxf-processor/internal/service"
)

func main() {
    // Redis 연결
    redisAddr := os.Getenv("REDIS_ADDR")
    if redisAddr == "" {
        redisAddr = "localhost:6379"
    }

    // Asynq Client 생성 (Job 전송용)
    client := asynq.NewClient(asynq.RedisClientOpt{Addr: redisAddr})
    defer client.Close()

    // Database 연결
    db := setupDatabase()
    defer db.Close()

    // Repository 초기화
    jobRepo := repository.NewJobRepository(db)

    // Service 초기화
    jobService := service.NewJobService(jobRepo, client)
    storageService := service.NewStorageService("./storage")
    parserService := service.NewParserService()

    // Gin Router 설정
    r := gin.Default()

    // CORS 설정
    r.Use(corsMiddleware())

    // API Routes
    v1 := r.Group("/api/v1")
    {
        // DXF 업로드
        v1.POST("/dxf/upload", handler.NewDXFHandler(jobService, storageService).Upload)

        // Job 관리
        jobHandler := handler.NewJobHandler(jobService, storageService, parserService)
        v1.GET("/jobs/:id", jobHandler.GetStatus)
        v1.GET("/jobs/:id/result", jobHandler.GetResult)
        v1.GET("/jobs/:id/map-data", jobHandler.GetMapData)

        // 파일 다운로드
        v1.GET("/files/:filename", handler.ServeFile)
    }

    // 서버 시작
    srv := &http.Server{
        Addr:    ":8080",
        Handler: r,
    }

    // Graceful Shutdown
    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Failed to start server: %v", err)
        }
    }()

    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal("Server forced to shutdown:", err)
    }
}

func corsMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
        c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }

        c.Next()
    }
}
```

---

### handler/dxf.go

```go
package handler

import (
    "fmt"
    "net/http"
    "path/filepath"

    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    "github.com/yourusername/dxf-processor/internal/model"
    "github.com/yourusername/dxf-processor/internal/service"
)

type DXFHandler struct {
    jobService     *service.JobService
    storageService *service.StorageService
}

func NewDXFHandler(js *service.JobService, ss *service.StorageService) *DXFHandler {
    return &DXFHandler{
        jobService:     js,
        storageService: ss,
    }
}

type UploadRequest struct {
    Options struct {
        Normalize bool    `json:"normalize"`
        Tolerance float64 `json:"tolerance"`
    } `json:"options"`
}

func (h *DXFHandler) Upload(c *gin.Context) {
    // 1. 파일 수신
    file, err := c.FormFile("file")
    if err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "파일을 찾을 수 없습니다"})
        return
    }

    // 확장자 검증
    ext := filepath.Ext(file.Filename)
    if ext != ".dxf" && ext != ".DXF" {
        c.JSON(http.StatusBadRequest, gin.H{"error": "DXF 파일만 업로드 가능합니다"})
        return
    }

    // 2. Job ID 생성
    jobID := uuid.New().String()

    // 3. 파일 저장
    inputPath := fmt.Sprintf("uploads/%s.dxf", jobID)
    if err := h.storageService.SaveUploadedFile(file, inputPath); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "파일 저장 실패"})
        return
    }

    // 4. Job 생성
    job := &model.Job{
        ID:        jobID,
        Status:    model.JobStatusPending,
        InputPath: inputPath,
    }

    if err := h.jobService.CreateJob(c.Request.Context(), job); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Job 생성 실패"})
        return
    }

    // 5. Job Queue에 추가
    if err := h.jobService.EnqueueJob(c.Request.Context(), jobID); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "Job 등록 실패"})
        return
    }

    // 6. 응답
    c.JSON(http.StatusOK, gin.H{
        "job_id":     jobID,
        "status":     job.Status,
        "status_url": fmt.Sprintf("/api/v1/jobs/%s", jobID),
        "created_at": job.CreatedAt,
    })
}
```

---

### handler/job.go

```go
package handler

import (
    "net/http"

    "github.com/gin-gonic/gin"
    "github.com/yourusername/dxf-processor/internal/model"
    "github.com/yourusername/dxf-processor/internal/service"
)

type JobHandler struct {
    jobService     *service.JobService
    storageService *service.StorageService
    parserService  *service.ParserService
}

func NewJobHandler(js *service.JobService, ss *service.StorageService, ps *service.ParserService) *JobHandler {
    return &JobHandler{
        jobService:     js,
        storageService: ss,
        parserService:  ps,
    }
}

// GetStatus - Job 상태 조회
func (h *JobHandler) GetStatus(c *gin.Context) {
    jobID := c.Param("id")

    job, err := h.jobService.GetJob(c.Request.Context(), jobID)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    c.JSON(http.StatusOK, job)
}

// GetResult - Job 처리 결과 조회
func (h *JobHandler) GetResult(c *gin.Context) {
    jobID := c.Param("id")

    job, err := h.jobService.GetJob(c.Request.Context(), jobID)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    if job.Status != model.JobStatusCompleted {
        c.JSON(http.StatusBadRequest, gin.H{
            "error": "처리가 완료되지 않았습니다",
            "status": job.Status,
        })
        return
    }

    // 통계 정보 파싱
    stats, err := h.parserService.ParseStatistics(job.OutputCSV)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "통계 파싱 실패"})
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "job_id": jobID,
        "status": job.Status,
        "files": gin.H{
            "csv": fmt.Sprintf("/api/v1/files/%s_processed.csv", jobID),
            "dxf": fmt.Sprintf("/api/v1/files/%s_processed.dxf", jobID),
        },
        "statistics": stats,
    })
}

// GetMapData - 맵 렌더링용 JSON 데이터 반환
func (h *JobHandler) GetMapData(c *gin.Context) {
    jobID := c.Param("id")

    job, err := h.jobService.GetJob(c.Request.Context(), jobID)
    if err != nil {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    if job.Status != model.JobStatusCompleted {
        c.JSON(http.StatusBadRequest, gin.H{"error": "처리가 완료되지 않았습니다"})
        return
    }

    // 레이어 필터링 (옵션)
    layerFilter := c.Query("layers")

    // CSV → Map Data 변환
    mapData, err := h.parserService.ParseCSVToMapData(job.OutputCSV, layerFilter)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "맵 데이터 파싱 실패"})
        return
    }

    c.JSON(http.StatusOK, mapData)
}
```

---

### worker/processor.go (Python 실행)

```go
package worker

import (
    "context"
    "encoding/json"
    "fmt"
    "os/exec"
    "time"

    "github.com/hibiken/asynq"
    "github.com/yourusername/dxf-processor/internal/repository"
    "github.com/yourusername/dxf-processor/internal/model"
)

const TypeDXFProcessing = "dxf:process"

type DXFProcessTask struct {
    JobID string
}

type Processor struct {
    jobRepo *repository.JobRepository
}

func NewProcessor(jobRepo *repository.JobRepository) *Processor {
    return &Processor{jobRepo: jobRepo}
}

// ProcessDXF - DXF 처리 Task Handler
func (p *Processor) ProcessDXF(ctx context.Context, t *asynq.Task) error {
    var task DXFProcessTask
    if err := json.Unmarshal(t.Payload(), &task); err != nil {
        return fmt.Errorf("json.Unmarshal failed: %v", err)
    }

    jobID := task.JobID

    // 1. Job 조회
    job, err := p.jobRepo.GetByID(ctx, jobID)
    if err != nil {
        return fmt.Errorf("failed to get job: %v", err)
    }

    // 2. 상태 업데이트: Processing
    job.Status = model.JobStatusProcessing
    job.UpdatedAt = time.Now()
    if err := p.jobRepo.Update(ctx, job); err != nil {
        return fmt.Errorf("failed to update job status: %v", err)
    }

    // 3. Python 스크립트 실행
    outputDXF := fmt.Sprintf("output/%s_processed.dxf", jobID)
    outputCSV := fmt.Sprintf("output/%s_processed.csv", jobID)

    cmd := exec.CommandContext(
        ctx,
        "python3",
        "scripts/process_central_dxf.py",
        job.InputPath,
        "--output-dxf", outputDXF,
        "--output-csv", outputCSV,
    )

    // stdout/stderr 캡처
    output, err := cmd.CombinedOutput()

    // 4. 결과 처리
    if err != nil {
        // 실패
        job.Status = model.JobStatusFailed
        job.Error = fmt.Sprintf("Python script failed: %v\nOutput: %s", err, string(output))
        p.jobRepo.Update(ctx, job)
        return fmt.Errorf("python script failed: %v", err)
    }

    // 성공
    job.Status = model.JobStatusCompleted
    job.OutputDXF = outputDXF
    job.OutputCSV = outputCSV
    job.Progress = 100
    job.UpdatedAt = time.Now()

    if err := p.jobRepo.Update(ctx, job); err != nil {
        return fmt.Errorf("failed to update job: %v", err)
    }

    return nil
}
```

---

### service/parser.go (CSV 파싱)

```go
package service

import (
    "encoding/csv"
    "fmt"
    "os"
    "strconv"
    "strings"
)

type ParserService struct{}

func NewParserService() *ParserService {
    return &ParserService{}
}

type MapData struct {
    JobID  string                 `json:"job_id"`
    Bounds Bounds                 `json:"bounds"`
    Layers map[string][]Polygon   `json:"layers"`
}

type Bounds struct {
    MinX float64 `json:"min_x"`
    MinY float64 `json:"min_y"`
    MaxX float64 `json:"max_x"`
    MaxY float64 `json:"max_y"`
}

type Polygon struct {
    ID          string      `json:"id"`
    Type        string      `json:"type"`
    Coordinates [][]float64 `json:"coordinates"`
    Style       Style       `json:"style"`
}

type Style struct {
    Color string `json:"color"`
    Fill  bool   `json:"fill"`
}

var layerColors = map[string]string{
    "p-parking-basic":    "#000000",
    "p-parking-delivery": "#FFA500",
    "p-parking-disable":  "#FF0000",
    "p-parking-electric": "#00FF00",
    "p-parking-large":    "#00FF00",
    "p-parking-small":    "#0000FF",
    "s-circulation-ramp": "#FFFF00",
}

func (s *ParserService) ParseCSVToMapData(csvPath string, layerFilter string) (*MapData, error) {
    file, err := os.Open(csvPath)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    reader := csv.NewReader(file)
    records, err := reader.ReadAll()
    if err != nil {
        return nil, err
    }

    // 레이어 필터 파싱
    filters := make(map[string]bool)
    if layerFilter != "" {
        for _, layer := range strings.Split(layerFilter, ",") {
            filters[strings.TrimSpace(layer)] = true
        }
    }

    // 데이터 구조 초기화
    mapData := &MapData{
        Layers: make(map[string][]Polygon),
        Bounds: Bounds{
            MinX: 1e9,
            MinY: 1e9,
            MaxX: -1e9,
            MaxY: -1e9,
        },
    }

    // CSV 파싱 (vertex-per-row 형식)
    polygons := make(map[string]*Polygon) // EntityHandle -> Polygon

    for i, row := range records {
        if i == 0 { // Skip header
            continue
        }

        x, _ := strconv.ParseFloat(row[0], 64)
        y, _ := strconv.ParseFloat(row[1], 64)
        layer := row[3]
        entityHandle := row[7]

        // 레이어 필터 적용
        if len(filters) > 0 && !filters[layer] {
            continue
        }

        // Bounds 업데이트
        if x < mapData.Bounds.MinX {
            mapData.Bounds.MinX = x
        }
        if x > mapData.Bounds.MaxX {
            mapData.Bounds.MaxX = x
        }
        if y < mapData.Bounds.MinY {
            mapData.Bounds.MinY = y
        }
        if y > mapData.Bounds.MaxY {
            mapData.Bounds.MaxY = y
        }

        // 폴리곤 그룹핑
        key := fmt.Sprintf("%s_%s", layer, entityHandle)
        if _, exists := polygons[key]; !exists {
            polygons[key] = &Polygon{
                ID:          entityHandle,
                Type:        "polygon",
                Coordinates: [][]float64{},
                Style: Style{
                    Color: layerColors[layer],
                    Fill:  true,
                },
            }
        }

        polygons[key].Coordinates = append(polygons[key].Coordinates, []float64{x, y})
    }

    // 레이어별로 분류
    for key, polygon := range polygons {
        layer := strings.Split(key, "_")[0]
        mapData.Layers[layer] = append(mapData.Layers[layer], *polygon)
    }

    return mapData, nil
}

func (s *ParserService) ParseStatistics(csvPath string) (map[string]interface{}, error) {
    file, err := os.Open(csvPath)
    if err != nil {
        return nil, err
    }
    defer file.Close()

    reader := csv.NewReader(file)
    records, err := reader.ReadAll()
    if err != nil {
        return nil, err
    }

    layerCounts := make(map[string]int)
    entityHandles := make(map[string]bool)

    for i, row := range records {
        if i == 0 { // Skip header
            continue
        }

        layer := row[3]
        entityHandle := row[7]

        key := fmt.Sprintf("%s_%s", layer, entityHandle)
        if !entityHandles[key] {
            entityHandles[key] = true
            layerCounts[layer]++
        }
    }

    total := 0
    for _, count := range layerCounts {
        total += count
    }

    return map[string]interface{}{
        "total_parkings": total,
        "layers":         layerCounts,
    }, nil
}
```

---

## Python Worker 구성

### 독립 실행 방식 (현재 구조 유지)

```python
#!/usr/bin/env python3
"""
process_central_dxf.py - DXF 파일 처리 스크립트

Usage:
    python3 process_central_dxf.py input.dxf --output-dxf out.dxf --output-csv out.csv
"""
import sys
import argparse
from pathlib import Path

# 기존 CentralDXFProcessor 클래스 사용
# (현재 코드 그대로 유지)

if __name__ == '__main__':
    main()
```

**Go에서 호출:**
```go
cmd := exec.Command(
    "python3",
    "scripts/process_central_dxf.py",
    inputPath,
    "--output-dxf", outputDXF,
    "--output-csv", outputCSV,
)
```

---

### Queue Worker 방식 (고급)

Python에서 직접 Queue를 읽어서 처리:

```python
# worker.py
import asynq
from process_central_dxf import CentralDXFProcessor

def process_dxf_task(job_id, input_path, output_dxf, output_csv):
    """DXF 처리 Task"""
    processor = CentralDXFProcessor(input_path)

    # 1. 주차면 추출
    processor.extract_all()

    # 2. DXF 생성
    processor.create_clean_dxf(output_dxf, normalize=True)

    # 3. CSV 변환
    processor.convert_to_csv(output_dxf, output_csv)

    return {
        "job_id": job_id,
        "status": "completed",
        "output_csv": output_csv,
        "output_dxf": output_dxf
    }

if __name__ == '__main__':
    # Asynq Worker 시작
    worker = asynq.Worker(
        redis_addr="localhost:6379",
        queue_name="dxf_processing"
    )

    worker.register("dxf:process", process_dxf_task)
    worker.run()
```

---

## 기술 스택

### Backend (Go)

#### Core
- **Web Framework**: [Gin](https://github.com/gin-gonic/gin) - 빠르고 가벼운 HTTP 프레임워크
- **Job Queue**: [Asynq](https://github.com/hibiken/asynq) - Redis 기반 분산 Task Queue
- **Database ORM**: [GORM](https://gorm.io/) - PostgreSQL ORM
- **UUID**: [Google UUID](https://github.com/google/uuid)

#### Storage
- **File Storage**: 로컬 파일 시스템 또는 [MinIO](https://min.io/) (S3 호환)
- **Database**: PostgreSQL 13+
- **Cache/Queue**: Redis 6+

---

### Processing (Python)

- **DXF 파싱**: [ezdxf](https://ezdxf.readthedocs.io/)
- **수치 계산**: NumPy (좌표 변환, 거리 계산)
- **환경**: Python 3.9+
- **가상환경**: venv

---

### 인프라

#### Development
```yaml
services:
  - Go API (localhost:8080)
  - Redis (localhost:6379)
  - PostgreSQL (localhost:5432)
  - Python Worker (subprocess)
```

#### Production
```yaml
services:
  api:
    image: dxf-api:latest
    replicas: 3
    ports:
      - "8080:8080"

  worker:
    image: dxf-worker:latest
    replicas: 5

  redis:
    image: redis:7-alpine

  postgres:
    image: postgres:15

  minio:
    image: minio/minio:latest
```

---

## 단계별 구현 로드맵

### Phase 1: MVP (1주일)

**목표**: 기본 DXF 처리 기능 구현

**작업:**
- [x] DXF 업로드 API
- [x] 동기 Python 실행
- [x] 파일 로컬 저장
- [x] Job ID 반환
- [x] 상태 조회 API (Polling)

**기술 스택:**
- Go + Gin
- SQLite (Job 메타데이터)
- Local File Storage
- Python subprocess

**성공 기준:**
- 10MB 이하 DXF 파일 처리 가능
- 30초 내 처리 완료
- 동시 요청 3개까지 처리

---

### Phase 2: Production Ready (2주일)

**목표**: 비동기 처리 및 확장성 확보

**작업:**
- [ ] Redis Job Queue 구현 (Asynq)
- [ ] PostgreSQL 마이그레이션
- [ ] Worker 프로세스 분리
- [ ] 에러 핸들링 + Retry 로직
- [ ] 파일 정리 (TTL 설정)
- [ ] 로깅 시스템

**기술 스택:**
- Go + Asynq
- PostgreSQL
- Redis
- Structured Logging (Zap)

**성공 기준:**
- 100MB 파일 처리 가능
- HTTP 타임아웃 없음
- 동시 요청 50개 처리
- Worker 수평 확장 가능

---

### Phase 3: Scale & Optimize (1개월)

**목표**: 대규모 트래픽 대응 및 사용자 경험 향상

**작업:**
- [ ] S3/MinIO 파일 저장소
- [ ] Multiple Workers (Auto Scaling)
- [ ] WebSocket 실시간 진행률
- [ ] 모니터링 + 로깅 (Prometheus, Grafana)
- [ ] CDN 연동 (파일 다운로드)
- [ ] Rate Limiting
- [ ] API 문서 (Swagger)

**기술 스택:**
- MinIO (S3 Compatible)
- WebSocket
- Prometheus + Grafana
- Docker + Kubernetes

**성공 기준:**
- 동시 요청 500개 처리
- 99.9% Uptime
- P95 응답 시간 < 100ms
- 자동 스케일링

---

## 참고 자료

### Go 라이브러리
- [Gin Web Framework](https://github.com/gin-gonic/gin)
- [Asynq Task Queue](https://github.com/hibiken/asynq)
- [GORM](https://gorm.io/docs/)
- [Zap Logger](https://github.com/uber-go/zap)

### Python
- [ezdxf Documentation](https://ezdxf.readthedocs.io/)
- [process_central_dxf.py](./process_central_dxf.py) - 프로젝트 내 DXF 처리 스크립트

### 아키텍처 패턴
- [12 Factor App](https://12factor.net/)
- [Microservices Pattern](https://microservices.io/patterns/index.html)

---

## 라이센스

MIT License

---

## Contact

문의사항은 이슈로 남겨주세요.
