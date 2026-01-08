# 백엔드 구현 가이드

## 개요

DXF 파일 처리 백엔드 API 구현 가이드입니다. Go 채널 기반 Queue를 사용하여 비동기 처리를 구현합니다.

---

## 핵심 기능

### 1단계: DXF 레이어 분석
- DXF 파일 업로드 시 모든 레이어/블록 목록 추출
- 사용자에게 주차면 레이어 선택 UI 제공

### 2단계: 선택된 레이어만 처리
- 사용자가 선택한 레이어만 추출
- Python 스크립트에 레이어 정보 전달
- CSV 생성

### 3단계: 결과 제공
- 처리 완료된 CSV/DXF 다운로드

---

## API 명세

### 1. DXF 파일 업로드 및 레이어 분석

**Endpoint:**
```http
POST /api/v1/dxf/upload
```

**Request:**
```http
Content-Type: multipart/form-data

{
  "file": <DXF binary>
}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "analyzing",
  "layers": {
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
      },
      {
        "name": "#배치도_지하주차장$0$장애인전용주차",
        "count": 68,
        "sample_area": 0.42,
        "suggested_type": "marker"
      }
    ],
    "total_blocks": 59
  },
  "analysis_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000/layers"
}
```

---

### 2. 레이어 선택 및 처리 시작

**Endpoint:**
```http
POST /api/v1/jobs/{job_id}/process
```

**Request:**
```json
{
  "layer_mapping": {
    "#배치도_지하주차장$0$확장형주차": "p-parking-large",
    "#배치도_지하주차장$0$p-일반": "p-parking-basic",
    "#배치도_지하주차장$0$p-경차": "p-parking-small",
    "#배치도_지하주차장$0$전기차 완속": "p-parking-electric",
    "#배치도_지하주차장$0$전기차 급속": "p-parking-electric",
    "#배치도_지하주차장$0$택배주차": "p-parking-delivery",
    "#배치도_지하주차장$0$장애인전용주차": "marker-disabled"
  },
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
  "status": "processing",
  "message": "처리가 시작되었습니다"
}
```

---

### 3. Job 상태 조회 (기존과 동일)

**Endpoint:**
```http
GET /api/v1/jobs/{job_id}
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "statistics": {
    "total_parkings": 2122,
    "layers": {
      "p-parking-basic": 684,
      "p-parking-large": 1081,
      "p-parking-small": 128,
      "p-parking-electric": 114,
      "p-parking-delivery": 20,
      "p-parking-disable": 85
    }
  }
}
```

---

### 4. 결과 다운로드 (기존과 동일)

**Endpoint:**
```http
GET /api/v1/jobs/{job_id}/result
GET /api/v1/files/{filename}
```

---

## 구현 상세

### 프로젝트 구조

```
backend/
├── main.go
├── models/
│   ├── job.go                # Job 모델
│   └── layer.go              # Layer 분석 결과 모델
├── services/
│   ├── queue.go              # 채널 기반 Queue
│   ├── worker.go             # Python 실행 Worker
│   ├── analyzer.go           # DXF 레이어 분석 서비스 (NEW)
│   └── storage.go            # 파일 저장 서비스
├── handlers/
│   ├── dxf.go                # DXF 업로드 + 레이어 분석
│   └── job.go                # Job 상태/결과 조회
└── scripts/
    ├── analyze_layers.py     # 레이어 분석 스크립트 (NEW)
    └── process_central_dxf.py # DXF 처리 스크립트
```

---

### models/layer.go

```go
package models

type LayerInfo struct {
    Name          string  `json:"name"`
    Count         int     `json:"count"`
    SampleArea    float64 `json:"sample_area"`
    SuggestedType string  `json:"suggested_type"`
}

type LayerAnalysis struct {
    Blocks      []LayerInfo       `json:"blocks"`
    TotalBlocks int               `json:"total_blocks"`
}

type ProcessRequest struct {
    LayerMapping map[string]string `json:"layer_mapping"`
    Options      ProcessOptions    `json:"options"`
}

type ProcessOptions struct {
    Normalize bool    `json:"normalize"`
    Tolerance float64 `json:"tolerance"`
}
```

---

### scripts/analyze_layers.py

```python
#!/usr/bin/env python3
"""
DXF 파일의 모든 레이어/블록 분석

Usage:
    python3 analyze_layers.py input.dxf --output analysis.json
"""
import sys
import json
import argparse
import ezdxf
from collections import defaultdict

def analyze_dxf_layers(dxf_path):
    """DXF 파일의 모든 블록 분석"""
    doc = ezdxf.readfile(dxf_path)

    # 블록 정보 수집
    block_info = []

    # INSERT 사용 횟수 카운트
    msp = doc.modelspace()
    insert_counts = defaultdict(int)

    for entity in msp:
        if entity.dxftype() == 'INSERT':
            main_block_name = entity.dxf.name
            if main_block_name in doc.blocks:
                main_block = doc.blocks[main_block_name]

                for sub_entity in main_block:
                    if sub_entity.dxftype() == 'INSERT':
                        insert_counts[sub_entity.dxf.name] += 1

    # 각 블록 상세 분석
    for block_name, count in insert_counts.items():
        if block_name not in doc.blocks:
            continue

        block = doc.blocks[block_name]

        # LWPOLYLINE 면적 계산
        max_area = 0
        for entity in block:
            if entity.dxftype() == 'LWPOLYLINE':
                vertices = list(entity.get_points())
                if len(vertices) >= 3:
                    area = 0
                    for i in range(len(vertices)):
                        j = (i + 1) % len(vertices)
                        area += vertices[i][0] * vertices[j][1]
                        area -= vertices[j][0] * vertices[i][1]
                    area = abs(area) / 2.0 / 1000000.0  # mm² → m²
                    if area > max_area:
                        max_area = area

        # 타입 추정
        suggested_type = suggest_layer_type(block_name, max_area)

        block_info.append({
            'name': block_name,
            'count': count,
            'sample_area': round(max_area, 2),
            'suggested_type': suggested_type
        })

    # 정렬 (사용 횟수 많은 순)
    block_info.sort(key=lambda x: x['count'], reverse=True)

    return {
        'blocks': block_info,
        'total_blocks': len(block_info)
    }

def suggest_layer_type(block_name, area):
    """블록 이름과 면적으로 타입 추정"""
    name_lower = block_name.lower()

    # 면적 기준
    if area < 1.0:
        return 'marker'  # 마커/심볼

    # 이름 기준
    if '장애' in name_lower or 'disabled' in name_lower:
        return 'marker-disabled'
    elif '확장' in name_lower or 'large' in name_lower:
        return 'p-parking-large'
    elif '경차' in name_lower or 'small' in name_lower:
        return 'p-parking-small'
    elif '전기' in name_lower or 'electric' in name_lower or 'ev' in name_lower:
        return 'p-parking-electric'
    elif '택배' in name_lower or 'delivery' in name_lower:
        return 'p-parking-delivery'
    elif '일반' in name_lower or 'basic' in name_lower or '주차' in name_lower:
        return 'p-parking-basic'
    elif '램프' in name_lower or 'ramp' in name_lower:
        return 's-circulation-ramp'

    return 'unknown'

def main():
    parser = argparse.ArgumentParser(description='DXF 레이어 분석')
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('--output', help='출력 JSON 파일', default='analysis.json')

    args = parser.parse_args()

    # 분석 실행
    result = analyze_dxf_layers(args.input)

    # JSON 저장
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"분석 완료: {result['total_blocks']}개 블록 발견")
    print(f"결과 저장: {args.output}")

if __name__ == '__main__':
    main()
```

---

### services/analyzer.go

```go
package services

import (
    "encoding/json"
    "fmt"
    "os/exec"
    "yourproject/models"
)

type AnalyzerService struct{}

func NewAnalyzerService() *AnalyzerService {
    return &AnalyzerService{}
}

// AnalyzeLayers - DXF 파일의 레이어 분석
func (s *AnalyzerService) AnalyzeLayers(inputPath string) (*models.LayerAnalysis, error) {
    // Python 스크립트 실행
    outputJSON := inputPath + "_analysis.json"

    cmd := exec.Command(
        "python3",
        "scripts/analyze_layers.py",
        inputPath,
        "--output", outputJSON,
    )

    output, err := cmd.CombinedOutput()
    if err != nil {
        return nil, fmt.Errorf("layer analysis failed: %v\nOutput: %s", err, string(output))
    }

    // JSON 파싱
    data, err := os.ReadFile(outputJSON)
    if err != nil {
        return nil, err
    }

    var analysis models.LayerAnalysis
    if err := json.Unmarshal(data, &analysis); err != nil {
        return nil, err
    }

    // 임시 파일 삭제
    os.Remove(outputJSON)

    return &analysis, nil
}
```

---

### handlers/dxf.go (수정)

```go
package handlers

import (
    "fmt"
    "net/http"
    "path/filepath"
    "time"

    "github.com/gin-gonic/gin"
    "github.com/google/uuid"
    "yourproject/models"
    "yourproject/services"
)

type DXFHandler struct {
    store    *models.JobStore
    queue    *services.JobQueue
    analyzer *services.AnalyzerService
}

func NewDXFHandler(store *models.JobStore, queue *services.JobQueue, analyzer *services.AnalyzerService) *DXFHandler {
    return &DXFHandler{
        store:    store,
        queue:    queue,
        analyzer: analyzer,
    }
}

// Upload - DXF 파일 업로드 및 레이어 분석
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
    inputPath := fmt.Sprintf("storage/uploads/%s.dxf", jobID)
    if err := c.SaveUploadedFile(file, inputPath); err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": "파일 저장 실패"})
        return
    }

    // 4. Job 생성
    job := &models.Job{
        ID:        jobID,
        Status:    models.JobStatusAnalyzing,
        Progress:  0,
        InputPath: inputPath,
        CreatedAt: time.Now(),
        UpdatedAt: time.Now(),
    }
    h.store.Create(job)

    // 5. 레이어 분석 (백그라운드)
    go func() {
        analysis, err := h.analyzer.AnalyzeLayers(inputPath)

        job, _ := h.store.Get(jobID)
        if err != nil {
            job.Status = models.JobStatusFailed
            job.Error = fmt.Sprintf("레이어 분석 실패: %v", err)
        } else {
            job.Status = models.JobStatusPending
            job.LayerAnalysis = analysis
        }
        h.store.Update(job)
    }()

    // 6. 응답
    c.JSON(http.StatusOK, gin.H{
        "job_id":       jobID,
        "status":       job.Status,
        "analysis_url": fmt.Sprintf("/api/v1/jobs/%s/layers", jobID),
    })
}

// GetLayers - 레이어 분석 결과 조회
func (h *DXFHandler) GetLayers(c *gin.Context) {
    jobID := c.Param("id")

    job, exists := h.store.Get(jobID)
    if !exists {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    if job.Status == models.JobStatusAnalyzing {
        c.JSON(http.StatusAccepted, gin.H{
            "status":  "analyzing",
            "message": "레이어 분석 중입니다",
        })
        return
    }

    if job.Status == models.JobStatusFailed {
        c.JSON(http.StatusInternalServerError, gin.H{
            "error": job.Error,
        })
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "job_id": jobID,
        "layers": job.LayerAnalysis,
    })
}

// ProcessLayers - 선택된 레이어로 처리 시작
func (h *DXFHandler) ProcessLayers(c *gin.Context) {
    jobID := c.Param("id")

    var req models.ProcessRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "잘못된 요청 형식"})
        return
    }

    job, exists := h.store.Get(jobID)
    if !exists {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    // 레이어 매핑 저장
    job.LayerMapping = req.LayerMapping
    job.Options = req.Options
    job.Status = models.JobStatusPending
    h.store.Update(job)

    // Queue에 추가
    if err := h.queue.Enqueue(jobID); err != nil {
        c.JSON(http.StatusServiceUnavailable, gin.H{
            "error": "Queue가 가득 찼습니다",
        })
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "job_id":  jobID,
        "status":  job.Status,
        "message": "처리가 시작되었습니다",
    })
}
```

---

### services/worker.go (수정)

```go
package services

import (
    "encoding/json"
    "fmt"
    "log"
    "os"
    "os/exec"
    "time"
    "yourproject/models"
)

type Worker struct {
    id    int
    queue *JobQueue
    store *models.JobStore
}

func NewWorker(id int, queue *JobQueue, store *models.JobStore) *Worker {
    return &Worker{
        id:    id,
        queue: queue,
        store: store,
    }
}

func (w *Worker) Start() {
    log.Printf("Worker #%d started", w.id)

    for {
        jobID := w.queue.Dequeue()
        log.Printf("Worker #%d processing job: %s", w.id, jobID)
        w.processJob(jobID)
    }
}

func (w *Worker) processJob(jobID string) {
    job, exists := w.store.Get(jobID)
    if !exists {
        log.Printf("Job not found: %s", jobID)
        return
    }

    // 상태 업데이트: Processing
    job.Status = models.JobStatusProcessing
    job.Progress = 0
    w.store.Update(job)

    // 레이어 매핑을 JSON 파일로 저장
    mappingPath := fmt.Sprintf("storage/temp/%s_mapping.json", jobID)
    mappingData, _ := json.Marshal(job.LayerMapping)
    os.WriteFile(mappingPath, mappingData, 0644)

    // Python 스크립트 실행
    outputDXF := fmt.Sprintf("storage/output/%s_processed.dxf", jobID)
    outputCSV := fmt.Sprintf("storage/output/%s_processed.csv", jobID)

    cmd := exec.Command(
        "python3",
        "scripts/process_central_dxf.py",
        job.InputPath,
        "--output-dxf", outputDXF,
        "--output-csv", outputCSV,
        "--layer-mapping", mappingPath,  // 레이어 매핑 전달
        "--tolerance", fmt.Sprintf("%.1f", job.Options.Tolerance),
    )

    startTime := time.Now()
    output, err := cmd.CombinedOutput()
    duration := time.Since(startTime)

    // 임시 파일 삭제
    os.Remove(mappingPath)

    if err != nil {
        log.Printf("Job %s failed: %v\nOutput: %s", jobID, err, string(output))
        job.Status = models.JobStatusFailed
        job.Error = fmt.Sprintf("처리 실패: %v", err)
        w.store.Update(job)
        return
    }

    log.Printf("Job %s completed in %v", jobID, duration)
    job.Status = models.JobStatusCompleted
    job.Progress = 100
    job.OutputDXF = outputDXF
    job.OutputCSV = outputCSV
    w.store.Update(job)
}
```

---

### models/job.go (수정)

```go
package models

import (
    "sync"
    "time"
)

type JobStatus string

const (
    JobStatusAnalyzing  JobStatus = "analyzing"   // 레이어 분석 중
    JobStatusPending    JobStatus = "pending"     // 대기 중
    JobStatusProcessing JobStatus = "processing"  // 처리 중
    JobStatusCompleted  JobStatus = "completed"   // 완료
    JobStatusFailed     JobStatus = "failed"      // 실패
)

type Job struct {
    ID            string                 `json:"id"`
    Status        JobStatus              `json:"status"`
    Progress      int                    `json:"progress"`
    InputPath     string                 `json:"input_path"`
    OutputDXF     string                 `json:"output_dxf,omitempty"`
    OutputCSV     string                 `json:"output_csv,omitempty"`
    Error         string                 `json:"error,omitempty"`
    LayerAnalysis *LayerAnalysis         `json:"layer_analysis,omitempty"`
    LayerMapping  map[string]string      `json:"layer_mapping,omitempty"`
    Options       ProcessOptions         `json:"options,omitempty"`
    CreatedAt     time.Time              `json:"created_at"`
    UpdatedAt     time.Time              `json:"updated_at"`
}

type ProcessOptions struct {
    Normalize bool    `json:"normalize"`
    Tolerance float64 `json:"tolerance"`
}

type JobStore struct {
    mu   sync.RWMutex
    jobs map[string]*Job
}

func NewJobStore() *JobStore {
    return &JobStore{
        jobs: make(map[string]*Job),
    }
}

func (s *JobStore) Create(job *Job) {
    s.mu.Lock()
    defer s.mu.Unlock()
    s.jobs[job.ID] = job
}

func (s *JobStore) Get(id string) (*Job, bool) {
    s.mu.RLock()
    defer s.mu.RUnlock()
    job, exists := s.jobs[id]
    return job, exists
}

func (s *JobStore) Update(job *Job) {
    s.mu.Lock()
    defer s.mu.Unlock()
    job.UpdatedAt = time.Now()
    s.jobs[job.ID] = job
}
```

---

### main.go (라우트 추가)

```go
package main

import (
    "context"
    "log"
    "net/http"
    "os"
    "os/signal"
    "syscall"
    "time"

    "github.com/gin-gonic/gin"
    "yourproject/handlers"
    "yourproject/models"
    "yourproject/services"
)

func main() {
    // 디렉토리 생성
    os.MkdirAll("storage/uploads", 0755)
    os.MkdirAll("storage/output", 0755)
    os.MkdirAll("storage/temp", 0755)

    // 서비스 초기화
    jobStore := models.NewJobStore()
    jobQueue := services.NewJobQueue(100, jobStore)
    analyzer := services.NewAnalyzerService()

    // Worker 시작
    numWorkers := 3
    for i := 1; i <= numWorkers; i++ {
        worker := services.NewWorker(i, jobQueue, jobStore)
        go worker.Start()
    }
    log.Printf("Started %d workers", numWorkers)

    // Gin Router
    r := gin.Default()

    // CORS
    r.Use(func(c *gin.Context) {
        c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
        c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type")
        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }
        c.Next()
    })

    // API Routes
    v1 := r.Group("/api/v1")
    {
        // DXF 업로드 및 레이어 분석
        dxfHandler := handlers.NewDXFHandler(jobStore, jobQueue, analyzer)
        v1.POST("/dxf/upload", dxfHandler.Upload)
        v1.GET("/jobs/:id/layers", dxfHandler.GetLayers)
        v1.POST("/jobs/:id/process", dxfHandler.ProcessLayers)

        // Job 관리
        jobHandler := handlers.NewJobHandler(jobStore)
        v1.GET("/jobs/:id", jobHandler.GetStatus)
        v1.GET("/jobs/:id/result", jobHandler.GetResult)
        v1.GET("/files/:filename", jobHandler.DownloadFile)
    }

    // Health Check
    r.GET("/health", func(c *gin.Context) {
        c.JSON(200, gin.H{
            "status":     "ok",
            "queue_size": jobQueue.Size(),
        })
    })

    // 서버 시작
    srv := &http.Server{
        Addr:    ":8080",
        Handler: r,
    }

    go func() {
        if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
            log.Fatalf("Failed to start server: %v", err)
        }
    }()

    log.Println("Server started on :8080")

    // Graceful Shutdown
    quit := make(chan os.Signal, 1)
    signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
    <-quit

    log.Println("Shutting down server...")

    ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
    defer cancel()

    if err := srv.Shutdown(ctx); err != nil {
        log.Fatal("Server forced to shutdown:", err)
    }

    log.Println("Server exited")
}
```

---

## 테스트 시나리오

### 1. DXF 업로드 및 레이어 분석

```bash
# 1. 파일 업로드
curl -X POST http://localhost:8080/api/v1/dxf/upload \
  -F "file=@central.dxf"

# 응답
{
  "job_id": "abc-123",
  "status": "analyzing",
  "analysis_url": "/api/v1/jobs/abc-123/layers"
}

# 2. 레이어 분석 결과 조회 (Polling)
curl http://localhost:8080/api/v1/jobs/abc-123/layers

# 응답
{
  "job_id": "abc-123",
  "layers": {
    "blocks": [
      {
        "name": "#배치도_지하주차장$0$확장형주차",
        "count": 1091,
        "sample_area": 13.52,
        "suggested_type": "p-parking-large"
      },
      ...
    ],
    "total_blocks": 59
  }
}
```

### 2. 레이어 선택 및 처리 시작

```bash
# 3. 선택한 레이어로 처리 시작
curl -X POST http://localhost:8080/api/v1/jobs/abc-123/process \
  -H "Content-Type: application/json" \
  -d '{
    "layer_mapping": {
      "#배치도_지하주차장$0$확장형주차": "p-parking-large",
      "#배치도_지하주차장$0$p-일반": "p-parking-basic",
      "#배치도_지하주차장$0$장애인전용주차": "marker-disabled"
    },
    "options": {
      "normalize": true,
      "tolerance": 7.0
    }
  }'

# 응답
{
  "job_id": "abc-123",
  "status": "processing",
  "message": "처리가 시작되었습니다"
}
```

### 3. 상태 조회 및 결과 다운로드

```bash
# 4. 상태 조회 (Polling)
curl http://localhost:8080/api/v1/jobs/abc-123

# 응답 (완료)
{
  "job_id": "abc-123",
  "status": "completed",
  "progress": 100,
  "statistics": {
    "total_parkings": 2122,
    "layers": {
      "p-parking-basic": 684,
      "p-parking-large": 1081,
      ...
    }
  }
}

# 5. 파일 다운로드
curl -O http://localhost:8080/api/v1/files/abc-123_processed.csv
```

---

## Python 스크립트 수정

`process_central_dxf.py`에 레이어 매핑 옵션 추가:

```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='입력 DXF 파일')
    parser.add_argument('--output-dxf', default='output.dxf')
    parser.add_argument('--output-csv', default='output.csv')
    parser.add_argument('--layer-mapping', help='레이어 매핑 JSON 파일')
    parser.add_argument('--tolerance', type=float, default=7.0)

    args = parser.parse_args()

    # 레이어 매핑 로드
    layer_mapping = {}
    if args.layer_mapping:
        with open(args.layer_mapping, 'r') as f:
            layer_mapping = json.load(f)

    # 프로세서 초기화
    processor = CentralDXFProcessor(args.input, layer_mapping=layer_mapping)

    # ... 나머지 처리
```

---

## 배포

### 1. 빌드

```bash
go build -o dxf-api main.go
```

### 2. 실행

```bash
# Python 가상환경 활성화
source venv/bin/activate

# Go 서버 실행
./dxf-api
```

### 3. Docker (옵션)

```dockerfile
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN go build -o dxf-api main.go

FROM python:3.9
WORKDIR /app
COPY --from=builder /app/dxf-api .
COPY scripts/ scripts/
COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 8080
CMD ["./dxf-api"]
```

---

## 다음 단계

- [ ] 레이어 분석 기능 구현
- [ ] 레이어 선택 API 구현
- [ ] Python 스크립트 수정
- [ ] 테스트 및 디버깅
- [ ] 프론트엔드 연동
