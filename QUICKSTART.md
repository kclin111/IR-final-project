# 🚀 快速啟動指南

## 第一次使用 (完整步驟)

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 設定 OpenAI API Key
```bash
# 複製範例環境變數檔案
cp .env.example .env

# 編輯 .env 並填入你的 OpenAI API Key
# OPENAI_API_KEY=sk-...
```

### 3. 建立向量資料庫 (重要!)
```bash
python scripts/build_vector_stores.py
```

等待建立完成 (約 2-5 分鐘)

### 4. 啟動服務
```bash
python -m app.main
```

### 5. 開啟瀏覽器
```
http://localhost:8000
```

---

## 已經建立過資料庫?

直接啟動服務即可:

```bash
python -m app.main
```

---

## 重建資料庫

如果需要重新建立向量資料庫:

```bash
python scripts/build_vector_stores.py --rebuild
```

---

## 範例查詢

試試以下問題:

- "闖紅燈會受到什麼處罰?"
- "未領駕照駕駛汽車的罰則是什麼?"
- "在人行道停車違法嗎?"
- "酒駕的處罰規定為何?"
- "路口左轉未停讓的責任歸屬"

---

## 故障排除

### 問題: 找不到 data 目錄下的檔案

確保以下檔案存在:
- `data/cleaned_道路交通管理處罰條例.csv`
- `data/law_case_mapping.json`
- `data/traffic_cases_chunks.jsonl`

### 問題: OpenAI API 錯誤

檢查 `.env` 中的 `OPENAI_API_KEY` 是否正確設定

### 問題: ChromaDB 錯誤

```bash
# 刪除舊資料庫並重建
rm -rf data/chroma_db/
python scripts/build_vector_stores.py
```

---

## 系統架構簡介

```
使用者查詢
    ↓
雙路向量檢索 (法條 + 判例)
    ↓
單層擴展 (透過 mapping)
    ↓
去重合併
    ↓
構建關聯式上下文
    ↓
LLM 生成回答
    ↓
返回結果 + 引用來源
```

---

詳細文件請參考 [SETUP.md](SETUP.md)
