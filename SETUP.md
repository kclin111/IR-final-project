# 交通法規智慧檢索系統 - 安裝與使用指南

## 📋 系統需求

- Python 3.9+
- OpenAI API Key

## 🚀 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

創建 `.env` 檔案:

```bash
cp .env.example .env
```

編輯 `.env` 並設定你的 OpenAI API Key:

```
OPENAI_API_KEY=your-api-key-here
```

### 3. 建立向量資料庫

**首次使用必須執行此步驟!**

```bash
python scripts/build_vector_stores.py
```

這將會:
- 讀取 `data/cleaned_道路交通管理處罰條例.csv`
- 讀取 `data/traffic_cases_chunks.jsonl`
- 建立 ChromaDB 向量資料庫在 `data/chroma_db/`
- 創建兩個 collections: `law_knowledge_points` 和 `case_applications`

如果需要重建資料庫:

```bash
python scripts/build_vector_stores.py --rebuild
```

### 4. 啟動應用程式

```bash
python -m app.main
```

或使用 uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 訪問系統

開啟瀏覽器訪問:

```
http://localhost:8000
```

## 🎯 API 端點

### 查詢端點

```
POST /api/query
```

Request Body:
```json
{
  "query": "闖紅燈會受到什麼處罰?"
}
```

Response:
```json
{
  "success": true,
  "query": "闖紅燈會受到什麼處罰?",
  "answer": "根據道路交通管理處罰條例...",
  "retrieved_laws": 5,
  "retrieved_cases": 3,
  "law_citations": ["道路交通管理處罰條例第53條"],
  "case_citations": ["TCDV,112,訴,717,20250814,1"],
  "processing_time": 2.5,
  "context_preview": "..."
}
```

### 統計資訊

```
GET /api/stats
```

Response:
```json
{
  "success": true,
  "statistics": {
    "total_laws": 93,
    "total_cases": 1500,
    "total_chunks": 15000,
    "avg_cases_per_law": 16.13
  }
}
```

### 健康檢查

```
GET /api/health
```

## 📁 專案結構

```
Final-Project/
├── app/
│   ├── api/
│   │   └── routes.py          # API 路由
│   ├── utils/
│   │   ├── vector_store.py    # 向量資料庫建立器
│   │   ├── mapping.py         # 法條-案例映射
│   │   ├── retrieval.py       # 檢索引擎
│   │   ├── context_builder.py # 上下文構建器
│   │   └── llm_generator.py   # LLM 生成器
│   ├── templates/
│   │   └── index.html         # 前端頁面
│   ├── static/
│   │   ├── css/style.css      # 樣式表
│   │   └── js/main.js         # 前端 JavaScript
│   ├── config.py              # 配置
│   └── main.py                # 主程式
├── data/
│   ├── cleaned_道路交通管理處罰條例.csv
│   ├── law_case_mapping.json
│   ├── traffic_cases_chunks.jsonl
│   └── chroma_db/            # ChromaDB 資料目錄 (自動生成)
├── scripts/
│   └── build_vector_stores.py # 向量庫建立腳本
└── requirements.txt
```

## 🔧 系統架構

### 檢索流程

1. **雙路檢索**: 同時檢索法條和判例 (各 Top-5)
2. **單層擴展**:
   - 從法條擴展到判例 (每個法條最多3個案例)
   - 從判例擴展到法條 (不限制)
3. **去重合併**: 合併並去除重複的法條與判例
4. **上下文構建**: 構建分層關聯結構的上下文
5. **LLM 生成**: 使用 OpenAI API 生成回答

### 向量資料庫設計

#### Law Collection (`law_knowledge_points`)
- **Document**: `{條號} {條文內容}`
- **Metadata**: cited_law, 法規名稱, 章名, 條號, 條文內容

#### Case Collection (`case_applications`)
- **Document**: chunk text
- **Metadata**: case_id, chunk_id, 判決資訊, cited_traffic_laws, chunk_type

## 🎨 前端功能

- 📝 文字輸入查詢
- ⏱️ 即時顯示處理時間
- 📊 檢索統計資訊
- 📚 引用來源追溯
- 🔍 Debug 模式查看上下文

## ⚠️ 注意事項

1. **首次使用必須先執行 `build_vector_stores.py`**
2. 確保 `.env` 中設定了有效的 `OPENAI_API_KEY`
3. 向量資料庫建立可能需要幾分鐘,取決於資料量
4. 系統僅供參考,不構成正式法律意見

## 🐛 故障排除

### 問題: ChromaDB 錯誤

```bash
# 刪除舊的資料庫並重建
rm -rf data/chroma_db
python scripts/build_vector_stores.py
```

### 問題: OpenAI API 錯誤

檢查:
1. `.env` 中的 API key 是否正確
2. API key 是否有足夠的額度
3. 網路連線是否正常

### 問題: 找不到資料檔案

確保以下檔案存在:
- `data/cleaned_道路交通管理處罰條例.csv`
- `data/law_case_mapping.json`
- `data/traffic_cases_chunks.jsonl`

## 📞 支援

如有問題請聯繫專案成員或查看專案文件。
