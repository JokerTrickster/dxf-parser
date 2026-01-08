# 프론트엔드 구현 가이드

## 개요

DXF 파일 업로드 및 레이어 선택 UI 구현 가이드입니다. React를 사용하여 구현합니다.

---

## 화면 구성

### 1. 파일 업로드 화면
- DXF 파일 드래그 앤 드롭 또는 파일 선택
- 업로드 버튼

### 2. 레이어 선택 화면
- 분석된 레이어 목록 표시
- 각 레이어의 주차면 타입 선택
- AI 추천 타입 표시
- 처리 옵션 설정 (좌표 정규화, tolerance)
- 처리 시작 버튼

### 3. 처리 진행 화면
- 진행률 표시
- 현재 상태 메시지
- 취소 버튼 (옵션)

### 4. 결과 화면
- 처리 완료 통계
- CSV/DXF 다운로드 버튼
- 새로운 파일 업로드 버튼

---

## 기술 스택

### 필수
- **React** 18+ - UI 프레임워크
- **Axios** - HTTP 클라이언트
- **React Router** - 라우팅

### 권장
- **Tailwind CSS** - 스타일링
- **React Query** - 서버 상태 관리
- **Zustand** - 클라이언트 상태 관리

---

## 프로젝트 구조

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── FileUpload.jsx          # 파일 업로드 컴포넌트
│   │   ├── LayerSelector.jsx       # 레이어 선택 컴포넌트
│   │   ├── ProcessingStatus.jsx    # 진행 상태 컴포넌트
│   │   └── ResultView.jsx          # 결과 화면 컴포넌트
│   ├── api/
│   │   └── dxfApi.js               # API 클라이언트
│   ├── hooks/
│   │   └── useDXFProcessor.js      # 커스텀 훅
│   ├── App.jsx
│   └── main.jsx
├── package.json
└── vite.config.js
```

---

## API 클라이언트

### src/api/dxfApi.js

```javascript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const dxfApi = {
  // 1. DXF 파일 업로드
  uploadDXF: async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/dxf/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  // 2. 레이어 분석 결과 조회
  getLayers: async (jobId) => {
    const response = await api.get(`/jobs/${jobId}/layers`);
    return response.data;
  },

  // 3. 선택한 레이어로 처리 시작
  processLayers: async (jobId, layerMapping, options) => {
    const response = await api.post(`/jobs/${jobId}/process`, {
      layer_mapping: layerMapping,
      options,
    });

    return response.data;
  },

  // 4. Job 상태 조회
  getJobStatus: async (jobId) => {
    const response = await api.get(`/jobs/${jobId}`);
    return response.data;
  },

  // 5. 결과 조회
  getJobResult: async (jobId) => {
    const response = await api.get(`/jobs/${jobId}/result`);
    return response.data;
  },

  // 6. 파일 다운로드 URL 생성
  getFileUrl: (filename) => {
    return `${API_BASE_URL}/files/${filename}`;
  },
};
```

---

## 커스텀 훅

### src/hooks/useDXFProcessor.js

```javascript
import { useState, useCallback } from 'react';
import { dxfApi } from '../api/dxfApi';

export const useDXFProcessor = () => {
  const [state, setState] = useState({
    step: 'upload', // upload, layers, processing, completed, error
    jobId: null,
    layers: null,
    job: null,
    error: null,
  });

  // 1. 파일 업로드
  const uploadFile = useCallback(async (file) => {
    try {
      setState(prev => ({ ...prev, step: 'upload', error: null }));

      const data = await dxfApi.uploadDXF(file);

      setState(prev => ({
        ...prev,
        jobId: data.job_id,
      }));

      // 레이어 분석 대기
      await pollLayerAnalysis(data.job_id);
    } catch (error) {
      setState(prev => ({
        ...prev,
        step: 'error',
        error: error.message,
      }));
    }
  }, []);

  // 2. 레이어 분석 Polling
  const pollLayerAnalysis = async (jobId) => {
    const maxAttempts = 30; // 최대 30초
    let attempts = 0;

    const poll = async () => {
      try {
        const data = await dxfApi.getLayers(jobId);

        if (data.layers) {
          // 분석 완료
          setState(prev => ({
            ...prev,
            step: 'layers',
            layers: data.layers,
          }));
        } else if (data.status === 'analyzing') {
          // 아직 분석 중
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(poll, 1000); // 1초 후 재시도
          } else {
            throw new Error('레이어 분석 타임아웃');
          }
        }
      } catch (error) {
        setState(prev => ({
          ...prev,
          step: 'error',
          error: error.message,
        }));
      }
    };

    poll();
  };

  // 3. 레이어 선택 및 처리 시작
  const startProcessing = useCallback(async (layerMapping, options) => {
    try {
      setState(prev => ({ ...prev, step: 'processing', error: null }));

      await dxfApi.processLayers(state.jobId, layerMapping, options);

      // 처리 상태 Polling 시작
      pollJobStatus(state.jobId);
    } catch (error) {
      setState(prev => ({
        ...prev,
        step: 'error',
        error: error.message,
      }));
    }
  }, [state.jobId]);

  // 4. Job 상태 Polling
  const pollJobStatus = async (jobId) => {
    const poll = async () => {
      try {
        const data = await dxfApi.getJobStatus(jobId);

        setState(prev => ({
          ...prev,
          job: data,
        }));

        if (data.status === 'completed') {
          // 완료
          const result = await dxfApi.getJobResult(jobId);
          setState(prev => ({
            ...prev,
            step: 'completed',
            job: { ...data, result },
          }));
        } else if (data.status === 'failed') {
          // 실패
          setState(prev => ({
            ...prev,
            step: 'error',
            error: data.error,
          }));
        } else {
          // 계속 처리 중
          setTimeout(poll, 2000); // 2초 후 재시도
        }
      } catch (error) {
        setState(prev => ({
          ...prev,
          step: 'error',
          error: error.message,
        }));
      }
    };

    poll();
  };

  // 5. 리셋
  const reset = useCallback(() => {
    setState({
      step: 'upload',
      jobId: null,
      layers: null,
      job: null,
      error: null,
    });
  }, []);

  return {
    state,
    uploadFile,
    startProcessing,
    reset,
  };
};
```

---

## 컴포넌트

### 1. FileUpload.jsx

```jsx
import { useState } from 'react';

export const FileUpload = ({ onUpload }) => {
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.name.endsWith('.dxf')) {
      setFile(selectedFile);
    } else {
      alert('DXF 파일만 업로드 가능합니다');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.name.endsWith('.dxf')) {
      setFile(droppedFile);
    } else {
      alert('DXF 파일만 업로드 가능합니다');
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleUpload = () => {
    if (file) {
      onUpload(file);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">DXF 파일 업로드</h1>

      <div
        className={`border-2 border-dashed rounded-lg p-12 text-center ${
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          accept=".dxf"
          onChange={handleFileChange}
          className="hidden"
          id="file-input"
        />

        <label htmlFor="file-input" className="cursor-pointer">
          <div className="text-6xl mb-4">📁</div>
          <p className="text-lg mb-2">
            DXF 파일을 드래그 앤 드롭하거나 클릭하여 선택하세요
          </p>
          <p className="text-sm text-gray-500">
            최대 100MB까지 업로드 가능합니다
          </p>
        </label>

        {file && (
          <div className="mt-6 p-4 bg-gray-100 rounded">
            <p className="font-medium">{file.name}</p>
            <p className="text-sm text-gray-600">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        )}
      </div>

      <button
        onClick={handleUpload}
        disabled={!file}
        className="mt-6 w-full bg-blue-500 text-white py-3 rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-blue-600"
      >
        업로드 및 레이어 분석
      </button>
    </div>
  );
};
```

---

### 2. LayerSelector.jsx

```jsx
import { useState } from 'react';

const PARKING_TYPES = {
  'p-parking-basic': '일반 주차',
  'p-parking-large': '확장형 주차',
  'p-parking-small': '경차 주차',
  'p-parking-electric': '전기차 주차',
  'p-parking-delivery': '택배 주차',
  'p-parking-disable': '장애인 주차',
  'marker-disabled': '장애인 마크',
  's-circulation-ramp': '램프',
  'ignore': '무시',
};

export const LayerSelector = ({ layers, onConfirm }) => {
  const [layerMapping, setLayerMapping] = useState(() => {
    // 초기값: AI 추천 타입 사용
    const initial = {};
    layers.blocks.forEach((block) => {
      initial[block.name] = block.suggested_type;
    });
    return initial;
  });

  const [options, setOptions] = useState({
    normalize: true,
    tolerance: 7.0,
  });

  const handleTypeChange = (blockName, newType) => {
    setLayerMapping((prev) => ({
      ...prev,
      [blockName]: newType,
    }));
  };

  const handleConfirm = () => {
    // 'ignore' 타입 제거
    const filteredMapping = Object.fromEntries(
      Object.entries(layerMapping).filter(([_, type]) => type !== 'ignore')
    );

    onConfirm(filteredMapping, options);
  };

  const selectedCount = Object.values(layerMapping).filter(
    (type) => type !== 'ignore'
  ).length;

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-4">레이어 선택</h1>
      <p className="text-gray-600 mb-8">
        총 {layers.total_blocks}개 블록 발견, {selectedCount}개 선택됨
      </p>

      {/* 옵션 */}
      <div className="mb-8 p-6 bg-gray-50 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">처리 옵션</h2>

        <div className="flex items-center mb-4">
          <input
            type="checkbox"
            id="normalize"
            checked={options.normalize}
            onChange={(e) =>
              setOptions({ ...options, normalize: e.target.checked })
            }
            className="mr-2"
          />
          <label htmlFor="normalize">좌표 정규화 (원점 기준)</label>
        </div>

        <div className="flex items-center">
          <label htmlFor="tolerance" className="mr-4">
            장애인 주차 재분류 거리:
          </label>
          <input
            type="number"
            id="tolerance"
            value={options.tolerance}
            onChange={(e) =>
              setOptions({ ...options, tolerance: parseFloat(e.target.value) })
            }
            step="0.5"
            min="1"
            max="20"
            className="border rounded px-3 py-1 w-20"
          />
          <span className="ml-2">m</span>
        </div>
      </div>

      {/* 레이어 목록 */}
      <div className="space-y-4 mb-8">
        {layers.blocks.map((block) => (
          <div
            key={block.name}
            className="border rounded-lg p-4 hover:shadow-md transition"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 mr-4">
                <h3 className="font-medium mb-2 break-all">{block.name}</h3>
                <div className="flex gap-4 text-sm text-gray-600">
                  <span>개수: {block.count}개</span>
                  <span>면적: {block.sample_area}m²</span>
                </div>
              </div>

              <div className="w-64">
                <select
                  value={layerMapping[block.name]}
                  onChange={(e) =>
                    handleTypeChange(block.name, e.target.value)
                  }
                  className="w-full border rounded px-3 py-2"
                >
                  {Object.entries(PARKING_TYPES).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                      {value === block.suggested_type && ' (추천)'}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 버튼 */}
      <div className="flex gap-4">
        <button
          onClick={handleConfirm}
          className="flex-1 bg-blue-500 text-white py-3 rounded-lg font-medium hover:bg-blue-600"
        >
          처리 시작 ({selectedCount}개 레이어)
        </button>
      </div>
    </div>
  );
};
```

---

### 3. ProcessingStatus.jsx

```jsx
export const ProcessingStatus = ({ job }) => {
  const getStatusText = (status) => {
    const statusMap = {
      pending: '대기 중...',
      processing: '처리 중...',
      analyzing: '분석 중...',
    };
    return statusMap[status] || status;
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">처리 진행 중</h1>

      <div className="bg-white rounded-lg shadow-md p-8">
        {/* 진행률 바 */}
        <div className="mb-6">
          <div className="flex justify-between mb-2">
            <span className="font-medium">{getStatusText(job.status)}</span>
            <span className="text-gray-600">{job.progress}%</span>
          </div>

          <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
            <div
              className="bg-blue-500 h-full transition-all duration-300"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        </div>

        {/* 상태 메시지 */}
        <div className="text-center py-12">
          <div className="text-6xl mb-4 animate-bounce">⚙️</div>
          <p className="text-lg text-gray-600">
            DXF 파일을 처리하고 있습니다...
          </p>
          <p className="text-sm text-gray-500 mt-2">
            대용량 파일의 경우 1-2분 소요될 수 있습니다
          </p>
        </div>
      </div>
    </div>
  );
};
```

---

### 4. ResultView.jsx

```jsx
import { dxfApi } from '../api/dxfApi';

export const ResultView = ({ job, onReset }) => {
  const handleDownload = (filename) => {
    const url = dxfApi.getFileUrl(filename);
    window.open(url, '_blank');
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <h1 className="text-3xl font-bold mb-8">처리 완료</h1>

      <div className="bg-white rounded-lg shadow-md p-8 mb-6">
        <div className="text-center mb-8">
          <div className="text-6xl mb-4">✅</div>
          <p className="text-xl font-semibold">처리가 완료되었습니다!</p>
        </div>

        {/* 통계 */}
        {job.statistics && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold mb-4">추출 결과</h2>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-blue-50 rounded">
                <p className="text-sm text-gray-600">총 주차면</p>
                <p className="text-2xl font-bold">
                  {job.statistics.total_parkings}개
                </p>
              </div>

              {Object.entries(job.statistics.layers || {}).map(
                ([layer, count]) => (
                  <div key={layer} className="p-4 bg-gray-50 rounded">
                    <p className="text-sm text-gray-600">{layer}</p>
                    <p className="text-xl font-semibold">{count}개</p>
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* 다운로드 버튼 */}
        <div className="space-y-3">
          <button
            onClick={() =>
              handleDownload(`${job.id}_processed.csv`)
            }
            className="w-full bg-green-500 text-white py-3 rounded-lg font-medium hover:bg-green-600"
          >
            📥 CSV 다운로드
          </button>

          <button
            onClick={() =>
              handleDownload(`${job.id}_processed.dxf`)
            }
            className="w-full bg-blue-500 text-white py-3 rounded-lg font-medium hover:bg-blue-600"
          >
            📥 DXF 다운로드
          </button>
        </div>
      </div>

      {/* 새 파일 업로드 */}
      <button
        onClick={onReset}
        className="w-full bg-gray-200 text-gray-700 py-3 rounded-lg font-medium hover:bg-gray-300"
      >
        새로운 파일 업로드
      </button>
    </div>
  );
};
```

---

### 5. App.jsx (통합)

```jsx
import { FileUpload } from './components/FileUpload';
import { LayerSelector } from './components/LayerSelector';
import { ProcessingStatus } from './components/ProcessingStatus';
import { ResultView } from './components/ResultView';
import { useDXFProcessor } from './hooks/useDXFProcessor';

function App() {
  const { state, uploadFile, startProcessing, reset } = useDXFProcessor();

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      {state.step === 'upload' && <FileUpload onUpload={uploadFile} />}

      {state.step === 'layers' && (
        <LayerSelector layers={state.layers} onConfirm={startProcessing} />
      )}

      {state.step === 'processing' && <ProcessingStatus job={state.job} />}

      {state.step === 'completed' && (
        <ResultView job={state.job} onReset={reset} />
      )}

      {state.step === 'error' && (
        <div className="max-w-2xl mx-auto p-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-700 mb-2">오류 발생</h2>
            <p className="text-red-600">{state.error}</p>
            <button
              onClick={reset}
              className="mt-4 bg-red-500 text-white px-6 py-2 rounded hover:bg-red-600"
            >
              다시 시도
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
```

---

## 설치 및 실행

### 1. 프로젝트 생성

```bash
# Vite + React 프로젝트 생성
npm create vite@latest dxf-frontend -- --template react
cd dxf-frontend
```

### 2. 의존성 설치

```bash
npm install axios
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

### 3. Tailwind 설정

`tailwind.config.js`:
```javascript
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

`src/index.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 4. 환경 변수

`.env`:
```
VITE_API_URL=http://localhost:8080/api/v1
```

### 5. 개발 서버 실행

```bash
npm run dev
```

http://localhost:5173 접속

---

## 테스트 시나리오

### 1. 파일 업로드
1. 브라우저에서 http://localhost:5173 접속
2. DXF 파일 드래그 앤 드롭 또는 선택
3. "업로드 및 레이어 분석" 버튼 클릭
4. 레이어 분석 완료 대기 (1-5초)

### 2. 레이어 선택
1. 분석된 레이어 목록 확인
2. 각 레이어의 타입 선택 (AI 추천 기본값)
3. 필요시 옵션 조정 (좌표 정규화, tolerance)
4. "처리 시작" 버튼 클릭

### 3. 처리 진행
1. 진행률 바 확인
2. 상태 메시지 확인
3. 완료 대기 (10-60초)

### 4. 결과 확인
1. 추출 통계 확인
2. CSV 다운로드 버튼 클릭
3. DXF 다운로드 버튼 클릭
4. "새로운 파일 업로드" 버튼으로 리셋

---

## 배포

### Vercel 배포

```bash
# Vercel CLI 설치
npm i -g vercel

# 배포
vercel
```

### Netlify 배포

```bash
# Netlify CLI 설치
npm i -g netlify-cli

# 빌드
npm run build

# 배포
netlify deploy --prod --dir=dist
```

---

## 추가 기능 (옵션)

### 1. 파일 검증

```jsx
const validateFile = (file) => {
  // 크기 검증
  if (file.size > 100 * 1024 * 1024) {
    throw new Error('파일 크기는 100MB 이하여야 합니다');
  }

  // 확장자 검증
  if (!file.name.toLowerCase().endsWith('.dxf')) {
    throw new Error('DXF 파일만 업로드 가능합니다');
  }

  return true;
};
```

### 2. 진행률 표시 개선

WebSocket 사용 시:
```javascript
const ws = new WebSocket(`ws://localhost:8080/ws/jobs/${jobId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  setProgress(data.progress);
  setMessage(data.message);
};
```

### 3. 에러 바운더리

```jsx
import { ErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error, resetErrorBoundary }) {
  return (
    <div className="p-8 bg-red-50 rounded">
      <h2 className="text-xl font-bold text-red-700">오류 발생</h2>
      <pre className="mt-2 text-sm">{error.message}</pre>
      <button onClick={resetErrorBoundary}>다시 시도</button>
    </div>
  );
}

// App.jsx에서
<ErrorBoundary FallbackComponent={ErrorFallback}>
  <App />
</ErrorBoundary>
```

---

## 다음 단계

- [ ] React 프로젝트 생성
- [ ] API 클라이언트 구현
- [ ] 컴포넌트 구현
- [ ] 스타일링
- [ ] 백엔드 API 연동 테스트
- [ ] 배포
