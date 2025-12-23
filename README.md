# 智慧交通法規與判例檢索輔助系統

Traffic Law and Case Retrieval System with RAG and KP-Case Alignment

## 專案概述

本系統結合語意向量檢索、智慧案例對齊、法律連動 RAG Context Builder、多階段重排與大語言模型，提供交通法規與判例的智慧檢索服務。

## 功能特色

- 語意向量檢索 (ChromaDB)
- KP-Case 智慧對齊
- 多階段重排 Re-ranking
- LLM 生成結構化結論
- 引用追溯與驗證

## 專案架構

```
Final-Project/
├── app/
│   ├── main.py                    # FastAPI 主程式
│   ├── config.py                  # 配置
│   ├── api/                       # API 路由
│   │   ├── routes.py
│   │   └── dependencies.py
│   ├── models/                    # 資料模型
│   │   ├── schemas.py
│   │   └── database.py
│   ├── utils/                     # 核心功能
│   │   ├── vector_search.py
│   │   ├── captioner.py
│   │   ├── alignment.py
│   │   ├── reranker.py
│   │   ├── context_builder.py
│   │   └── llm_generator.py
│   └── preprocessing/             # 前處理
│       ├── law_chunker.py
│       ├── case_parser.py
│       └── alignment_builder.py
├── tests/                         # 單元測試
└── requirements.txt
```

## 安裝

### 1. 建立虛擬環境

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 安裝依賴

```bash
pip install -r requirements.txt
```

### 3. 配置環境變數

```bash
cp .env.example .env
# 編輯 .env 並填入必要的 API keys
```

## 使用方式

### 啟動 API 服務

```bash
python app/main.py
```

或使用 uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API 文檔

啟動後訪問: http://localhost:8000/docs

### 主要 API 端點

- `POST /api/v1/query` - 查詢法規與判例
- `GET /api/v1/stats` - 系統統計資料
- `POST /api/v1/alignments/review` - 對齊審核
- `GET /api/v1/health` - 健康檢查

## 測試

### 執行所有測試

```bash
pytest
```

### 執行特定測試檔案

```bash
pytest tests/test_vector_search.py
```

### 測試覆蓋率

```bash
pytest --cov=app --cov-report=html
```

## 開發指南

### 程式碼風格

```bash
# 格式化
black app/ tests/

# 檢查
flake8 app/ tests/
mypy app/
```

## 資料結構

### ChromaDB Collections

- `knowledge_points` - 法律知識點
- `applications` - 判決片段
- `image_features` - 圖片特徵 (可選)

### SQLite Tables

- `kp_app_mapping` - KP-Case 對齊表