# Go 채널 기반 간단한 Queue 구현

## 개요

Redis나 별도 인프라 없이 Go의 채널만으로 비동기 Job Queue를 구현합니다.

**장점:**
- ✅ 외부 의존성 없음
- ✅ 구현 단순
- ✅ 빠른 개발 속도

**제약:**
- ⚠️ 서버 재시작 시 Queue 데이터 손실
- ⚠️ 단일 서버만 지원 (수평 확장 불가)

---

## 전체 구조

```
Client
  ↓ POST /api/dxf/upload
Go API Server
  ├─ HTTP Handler (파일 저장 + Job 생성)
  ├─ Channel Queue (메모리)
  └─ Worker Goroutine (Python 실행)
```

---

## 프로젝트 구조

```
backend/
├── main.go                    # API 서버 + Worker 통합
├── models/
│   └── job.go                # Job 모델
├── handlers/
│   ├── dxf.go                # DXF 업로드 핸들러
│   └── job.go                # Job 상태 조회 핸들러
├── services/
│   ├── queue.go              # Channel Queue 서비스
│   └── worker.go             # Python 실행 Worker
└── storage/
    ├── uploads/              # 업로드된 DXF 파일
    └── output/               # 처리 결과 (DXF, CSV)
```

---

## 구현 코드

### 1. models/job.go

```go
package models

import (
    "sync"
    "time"
)

type JobStatus string

const (
    JobStatusPending    JobStatus = "pending"
    JobStatusProcessing JobStatus = "processing"
    JobStatusCompleted  JobStatus = "completed"
    JobStatusFailed     JobStatus = "failed"
)

type Job struct {
    ID          string    `json:"id"`
    Status      JobStatus `json:"status"`
    Progress    int       `json:"progress"`
    InputPath   string    `json:"input_path"`
    OutputDXF   string    `json:"output_dxf,omitempty"`
    OutputCSV   string    `json:"output_csv,omitempty"`
    Error       string    `json:"error,omitempty"`
    CreatedAt   time.Time `json:"created_at"`
    UpdatedAt   time.Time `json:"updated_at"`
}

// JobStore - 메모리 기반 Job 저장소
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

### 2. services/queue.go

```go
package services

import (
    "log"
    "yourproject/models"
)

// JobQueue - Go 채널 기반 Queue
type JobQueue struct {
    queue chan string // Job ID를 전달
    store *models.JobStore
}

func NewJobQueue(bufferSize int, store *models.JobStore) *JobQueue {
    return &JobQueue{
        queue: make(chan string, bufferSize),
        store: store,
    }
}

// Enqueue - Job을 Queue에 추가
func (q *JobQueue) Enqueue(jobID string) error {
    select {
    case q.queue <- jobID:
        log.Printf("Job enqueued: %s", jobID)
        return nil
    default:
        return fmt.Errorf("queue is full")
    }
}

// Dequeue - Queue에서 Job 가져오기 (Blocking)
func (q *JobQueue) Dequeue() string {
    return <-q.queue
}

// Size - 현재 Queue 크기
func (q *JobQueue) Size() int {
    return len(q.queue)
}
```

---

### 3. services/worker.go

```go
package services

import (
    "fmt"
    "log"
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

// Start - Worker 시작 (Goroutine으로 실행)
func (w *Worker) Start() {
    log.Printf("Worker #%d started", w.id)

    for {
        // Queue에서 Job 가져오기 (Blocking)
        jobID := w.queue.Dequeue()
        log.Printf("Worker #%d processing job: %s", w.id, jobID)

        // Job 처리
        w.processJob(jobID)
    }
}

func (w *Worker) processJob(jobID string) {
    // 1. Job 조회
    job, exists := w.store.Get(jobID)
    if !exists {
        log.Printf("Job not found: %s", jobID)
        return
    }

    // 2. 상태 업데이트: Processing
    job.Status = models.JobStatusProcessing
    job.Progress = 0
    w.store.Update(job)

    // 3. Python 스크립트 실행
    outputDXF := fmt.Sprintf("storage/output/%s_processed.dxf", jobID)
    outputCSV := fmt.Sprintf("storage/output/%s_processed.csv", jobID)

    cmd := exec.Command(
        "python3",
        "scripts/process_central_dxf.py",
        job.InputPath,
        "--output-dxf", outputDXF,
        "--output-csv", outputCSV,
    )

    // 실행 시작
    startTime := time.Now()
    output, err := cmd.CombinedOutput()
    duration := time.Since(startTime)

    // 4. 결과 처리
    if err != nil {
        // 실패
        log.Printf("Job %s failed: %v\nOutput: %s", jobID, err, string(output))
        job.Status = models.JobStatusFailed
        job.Error = fmt.Sprintf("Python execution failed: %v", err)
        w.store.Update(job)
        return
    }

    // 성공
    log.Printf("Job %s completed in %v", jobID, duration)
    job.Status = models.JobStatusCompleted
    job.Progress = 100
    job.OutputDXF = outputDXF
    job.OutputCSV = outputCSV
    w.store.Update(job)
}
```

---

### 4. handlers/dxf.go

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
    store *models.JobStore
    queue *services.JobQueue
}

func NewDXFHandler(store *models.JobStore, queue *services.JobQueue) *DXFHandler {
    return &DXFHandler{
        store: store,
        queue: queue,
    }
}

// Upload - DXF 파일 업로드 및 Job 생성
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

    // 파일 크기 제한 (예: 100MB)
    if file.Size > 100*1024*1024 {
        c.JSON(http.StatusBadRequest, gin.H{"error": "파일 크기는 100MB 이하여야 합니다"})
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
        Status:    models.JobStatusPending,
        Progress:  0,
        InputPath: inputPath,
        CreatedAt: time.Now(),
        UpdatedAt: time.Now(),
    }
    h.store.Create(job)

    // 5. Queue에 추가
    if err := h.queue.Enqueue(jobID); err != nil {
        c.JSON(http.StatusServiceUnavailable, gin.H{
            "error": "Queue가 가득 찼습니다. 잠시 후 다시 시도해주세요",
        })
        return
    }

    // 6. 응답
    c.JSON(http.StatusOK, gin.H{
        "job_id":     jobID,
        "status":     job.Status,
        "status_url": fmt.Sprintf("/api/v1/jobs/%s", jobID),
        "created_at": job.CreatedAt,
        "queue_size": h.queue.Size(),
    })
}
```

---

### 5. handlers/job.go

```go
package handlers

import (
    "net/http"

    "github.com/gin-gonic/gin"
    "yourproject/models"
)

type JobHandler struct {
    store *models.JobStore
}

func NewJobHandler(store *models.JobStore) *JobHandler {
    return &JobHandler{store: store}
}

// GetStatus - Job 상태 조회
func (h *JobHandler) GetStatus(c *gin.Context) {
    jobID := c.Param("id")

    job, exists := h.store.Get(jobID)
    if !exists {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    c.JSON(http.StatusOK, job)
}

// GetResult - Job 결과 조회
func (h *JobHandler) GetResult(c *gin.Context) {
    jobID := c.Param("id")

    job, exists := h.store.Get(jobID)
    if !exists {
        c.JSON(http.StatusNotFound, gin.H{"error": "Job을 찾을 수 없습니다"})
        return
    }

    if job.Status != models.JobStatusCompleted {
        c.JSON(http.StatusBadRequest, gin.H{
            "error":  "처리가 완료되지 않았습니다",
            "status": job.Status,
        })
        return
    }

    c.JSON(http.StatusOK, gin.H{
        "job_id": jobID,
        "status": job.Status,
        "files": gin.H{
            "csv": fmt.Sprintf("/api/v1/files/%s_processed.csv", jobID),
            "dxf": fmt.Sprintf("/api/v1/files/%s_processed.dxf", jobID),
        },
    })
}

// DownloadFile - 파일 다운로드
func (h *JobHandler) DownloadFile(c *gin.Context) {
    filename := c.Param("filename")
    filepath := fmt.Sprintf("storage/output/%s", filename)

    // 파일 존재 확인
    if _, err := os.Stat(filepath); os.IsNotExist(err) {
        c.JSON(http.StatusNotFound, gin.H{"error": "파일을 찾을 수 없습니다"})
        return
    }

    c.File(filepath)
}
```

---

### 6. main.go (전체 통합)

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
    // 1. 디렉토리 생성
    os.MkdirAll("storage/uploads", 0755)
    os.MkdirAll("storage/output", 0755)

    // 2. Job Store 초기화
    jobStore := models.NewJobStore()

    // 3. Job Queue 초기화 (버퍼 크기: 100)
    jobQueue := services.NewJobQueue(100, jobStore)

    // 4. Worker 시작 (3개의 Worker Goroutine)
    numWorkers := 3
    for i := 1; i <= numWorkers; i++ {
        worker := services.NewWorker(i, jobQueue, jobStore)
        go worker.Start()
    }
    log.Printf("Started %d workers", numWorkers)

    // 5. Gin Router 설정
    r := gin.Default()

    // CORS 미들웨어
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
        // DXF 업로드
        dxfHandler := handlers.NewDXFHandler(jobStore, jobQueue)
        v1.POST("/dxf/upload", dxfHandler.Upload)

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

    // 6. HTTP 서버 시작
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

    log.Println("Server started on :8080")

    // 종료 시그널 대기
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

## 사용 방법

### 1. 의존성 설치

```bash
go mod init yourproject
go get github.com/gin-gonic/gin
go get github.com/google/uuid
```

### 2. 서버 실행

```bash
# Python 가상환경 활성화
source venv/bin/activate

# Go 서버 실행
go run main.go
```

**출력:**
```
Started 3 workers
Worker #1 started
Worker #2 started
Worker #3 started
Server started on :8080
```

### 3. API 테스트

#### DXF 파일 업로드

```bash
curl -X POST http://localhost:8080/api/v1/dxf/upload \
  -F "file=@central.dxf"
```

**응답:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "status_url": "/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2026-01-08T15:30:00Z",
  "queue_size": 1
}
```

#### Job 상태 조회

```bash
curl http://localhost:8080/api/v1/jobs/550e8400-e29b-41d4-a716-446655440000
```

**응답 (처리 중):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 50,
  "input_path": "storage/uploads/550e8400-e29b-41d4-a716-446655440000.dxf",
  "created_at": "2026-01-08T15:30:00Z",
  "updated_at": "2026-01-08T15:30:15Z"
}
```

**응답 (완료):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100,
  "input_path": "storage/uploads/550e8400-e29b-41d4-a716-446655440000.dxf",
  "output_dxf": "storage/output/550e8400-e29b-41d4-a716-446655440000_processed.dxf",
  "output_csv": "storage/output/550e8400-e29b-41d4-a716-446655440000_processed.csv",
  "created_at": "2026-01-08T15:30:00Z",
  "updated_at": "2026-01-08T15:30:45Z"
}
```

#### 결과 다운로드

```bash
# CSV 다운로드
curl -O http://localhost:8080/api/v1/files/550e8400-e29b-41d4-a716-446655440000_processed.csv

# DXF 다운로드
curl -O http://localhost:8080/api/v1/files/550e8400-e29b-41d4-a716-446655440000_processed.dxf
```

---

## 클라이언트 예시 (JavaScript)

```javascript
// 1. 파일 업로드
async function uploadDXF(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch('http://localhost:8080/api/v1/dxf/upload', {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();
  return data.job_id;
}

// 2. 상태 조회 (Polling)
async function pollJobStatus(jobId) {
  while (true) {
    const response = await fetch(`http://localhost:8080/api/v1/jobs/${jobId}`);
    const job = await response.json();

    console.log(`Status: ${job.status}, Progress: ${job.progress}%`);

    if (job.status === 'completed') {
      console.log('처리 완료!');
      return job;
    } else if (job.status === 'failed') {
      console.error('처리 실패:', job.error);
      throw new Error(job.error);
    }

    // 2초마다 재확인
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// 3. 사용 예시
const fileInput = document.getElementById('dxf-file');
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];

  // 업로드
  const jobId = await uploadDXF(file);
  console.log('Job created:', jobId);

  // 상태 추적
  const result = await pollJobStatus(jobId);

  // 결과 다운로드
  window.location.href = `http://localhost:8080/api/v1/files/${jobId}_processed.csv`;
});
```

---

## 개선 사항 (선택)

### 1. 진행률 업데이트

Python 스크립트에서 진행률 출력:

```python
# process_central_dxf.py
print("PROGRESS:10")  # 10% 완료
print("PROGRESS:50")  # 50% 완료
print("PROGRESS:100") # 100% 완료
```

Go에서 파싱:

```go
// Worker에서 stdout 스캔
scanner := bufio.NewScanner(cmd.Stdout)
go func() {
    for scanner.Scan() {
        line := scanner.Text()
        if strings.HasPrefix(line, "PROGRESS:") {
            progress, _ := strconv.Atoi(strings.TrimPrefix(line, "PROGRESS:"))
            job.Progress = progress
            w.store.Update(job)
        }
    }
}()
```

### 2. 자동 파일 정리

```go
// 24시간 후 파일 자동 삭제
func CleanupOldFiles() {
    ticker := time.NewTicker(1 * time.Hour)
    for range ticker.C {
        cutoff := time.Now().Add(-24 * time.Hour)

        files, _ := ioutil.ReadDir("storage/output")
        for _, file := range files {
            if file.ModTime().Before(cutoff) {
                os.Remove(filepath.Join("storage/output", file.Name()))
            }
        }
    }
}

// main.go에서 시작
go CleanupOldFiles()
```

### 3. Queue 크기 모니터링

```go
// /metrics 엔드포인트
r.GET("/metrics", func(c *gin.Context) {
    c.JSON(200, gin.H{
        "queue_size": jobQueue.Size(),
        "queue_capacity": 100,
        "total_jobs": len(jobStore.jobs),
    })
})
```

---

## 제한 사항 및 해결책

### 문제 1: 서버 재시작 시 Queue 손실

**해결책:** 주기적으로 pending jobs를 디스크에 저장

```go
func (s *JobStore) SaveToDisk() error {
    data, _ := json.Marshal(s.jobs)
    return ioutil.WriteFile("jobs.json", data, 0644)
}

func (s *JobStore) LoadFromDisk() error {
    data, _ := ioutil.ReadFile("jobs.json")
    return json.Unmarshal(data, &s.jobs)
}

// main.go에서 주기적 저장
ticker := time.NewTicker(10 * time.Second)
go func() {
    for range ticker.C {
        jobStore.SaveToDisk()
    }
}()
```

### 문제 2: 메모리 제한

**해결책:** Job 보관 기간 제한

```go
// 완료된 Job은 1시간 후 삭제
func (s *JobStore) CleanupCompleted() {
    s.mu.Lock()
    defer s.mu.Unlock()

    cutoff := time.Now().Add(-1 * time.Hour)
    for id, job := range s.jobs {
        if job.Status == JobStatusCompleted && job.UpdatedAt.Before(cutoff) {
            delete(s.jobs, id)
        }
    }
}
```

---

## 요약

**구현 단계:**
1. ✅ models/job.go - Job 모델 및 메모리 저장소
2. ✅ services/queue.go - Go 채널 기반 Queue
3. ✅ services/worker.go - Python 실행 Worker
4. ✅ handlers/ - API 핸들러
5. ✅ main.go - 전체 통합

**실행 명령:**
```bash
go run main.go
```

**테스트:**
```bash
curl -X POST http://localhost:8080/api/v1/dxf/upload -F "file=@central.dxf"
```

간단하고 빠르게 시작할 수 있습니다! 🚀
