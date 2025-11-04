# ✅ **PRD — 智慧交通法規與判例檢索輔助系統**

## 1. 🎯 專題目標（Problem Statement）

一般大眾、學生、保險理賠人員在交通情境中需要查詢：

* **適用之法律條文**
* **相似判例與法院推理邏輯**
* **行為構成要件**
* **不同情境的責任差異**

現有做法須自行閱讀大量 PDF 判決書、散落的網頁資訊，成本高、速度慢。

本系統希望：

* **降低資訊門檻**
* **提升查詢速度**
* **提供可追溯引用**
* **引導使用者查看重點要件**

---

## 2. 💡 產品概述（Solution Overview）

本系統結合：

* 語意向量檢索（ChromaDB）
* 智慧案例對齊（KP↔Case Alignment）
* 法律連動 RAG Context Builder
* 多階段重排 Re-ranking
* 大語言模型生成結論＋引用
* 可選圖片 Captioner（VLM）

使用者可輸入**文字或事故照片**，系統回傳：

* 相關法規
* 相似判決
* 構成要件核對（Checklist）
* 法院引用段落
* 最終結論建議

---

## 3. 👥 使用者族群

| 使用者      | 需求         |
| -------- | ---------- |
| 法律系學生    | 快速比對判決與法條  |
| 一般民眾     | 初步了解事故責任點  |
| 保險業務/理賠  | 查參考範例與法院論述 |
| 新手法律研究助理 | 案件初探線索整理   |

---

## 4. 🌍 使用情境

1. 發生事故後，輸入文字＋照片 → 判斷紅線、雙黃線、斑馬線等責任點。
2. 查詢「路口左轉未停讓」相關法條流程。
3. 以「闖紅燈」檢索近五年法院觀點差異。

---

## 5. 🧩 系統架構（高階）

```
User CLI / Frontend
    │
FastAPI API Server (LangChain Pipeline)
    │
可選 VLM Captioner
    │
Query Builder
    │
ChromaDB: knowledge_points
    │
SQLite: kp_app_mapping (對齊表)
    │
ChromaDB: applications (判決片段)
    │
Re-ranker（相似度＋要件覆蓋＋等級＋對齊信心）
    │
Context Assembler
    │
LLM（生成結論＋引用）
```

---

## 6. 🔧 功能說明（Feature Spec）

### 6.1 文字查詢

* 將 Query 嵌入向量
* 搜尋 Top-K knowledge points (KP)

### 6.2 可選圖片 Captioner（VLM）

輸出：

* 道路標誌
* 交叉路口狀態
* 是否壓線、逆向等語義 token

### 6.3 第 1 階段：向量召回 (Chroma-KP)

* 得到 Top-K 相關法律知識點

### 6.4 Case Mapping（**核心功能**）

* 透過 kp_app_mapping 查詢對齊案例
* 欠缺時補召回（Applications 向量庫）
* 合併去重

### 6.5 多階段重排 Re-rank

排序考慮：

* 文字語義相似度
* 行為構成要件 coverage
* Alignment confidence
* 法院層級/年分質量

### 6.6 上下文組裝 Context Builder

抽取：

* 判決理由段落
* 規範核心重點 span
* 案例 rationale

### 6.7 LLM 生成

保證輸出格式：

```json
{
  "conclusion": "...",
  "checklist": {...},
  "citations": [
    {"type":"statute","id":"...","span":"..."},
    {"type":"case","id":"...","span":"..."}
  ],
  "alignments_used":[...],
  "warnings":[...]
}
```

---

## 7. 📁 離線建構流程（Offline Pipeline）

見你第 2 張流程圖，正式敘述如下：

### 7.1 法律切塊

* 將法條依條段切片
* 建立 knowledge_points collection

### 7.2 判決切段

* 抽取 Fact/Reason 區塊
* 建立 applications collection

### 7.3 Case Alignment（半自動）

* 依 LLM labeling + 規則
* 人工覆核
* 記錄 confidence, rationale_span

### 7.4 圖片 Feature（可選）

* 偵測
* 存入 image_features collection

---

## 8. 🔍 線上 Query Sequence（Runtime）

對應你第三/第四張圖：

1. 使用者輸入文字/圖片
2. API 收到輸入
3. 若有圖片 → Caption 處理
4. Query = Text + Caption Tokens
5. 向量檢索（knowledge_points）
6. 查 kp_app_mapping（對應案例集合）
7. 不足補召回（applications 向量）
8. 合併案例並去重
9. Re-rank（coverage+confidence+quality）
10. 組裝上下文
11. LLM 生成 JSON 結論
12. 回傳顯示

---

## 9. 🧬 資料表 Schema（必交）

### 9.1 `knowledge_points`

| 欄位        | 說明   |
| --------- | ---- |
| id        | 條文識別 |
| content   | 文本片段 |
| embedding | 向量   |

### 9.2 `applications`

| 欄位        | 說明   |
| --------- | ---- |
| id        | 判例識別 |
| fact      | 事實段落 |
| reason    | 理由段落 |
| embedding | 向量   |

### 9.3 `kp_app_mapping`

| 欄位             | 說明                        |
| -------------- | ------------------------- |
| kp_id          | 法律知識點                     |
| case_id        | 判決 ID                     |
| confidence     | alignment 信心              |
| rationale_span | 引用段落                      |
| status         | approved/rejected/pending |

---

## 10. 📡 API 介面

### `POST /query`

Request:

```json
{ "text":"...", "image":"base64?" }
```

Response:
見前述 JSON Structured Output。

### `GET /stats`

回傳 Hit@k 指標統計。

### `POST /alignments/review`

教師/人工覆核。

---

## 11. 🧪 測試計畫（TDD）

### 11.1 Unit Tests

測：

* 切段正確性
* alignment scoring function
* coverage algorithm
* citation 正則驗證

### 11.2 Integration Tests

測：

* Top-K KP → Mapping → Combine → Rank
* Caption fallback path
* 多案例合併去重

### 11.3 Contract Tests

保證：

* citations id 必可追溯
* span 必來自 context
* schema 正確

### 11.4 E2E Tests

流程：

1. query
2. retrieval
3. re-rank
4. context build
5. LLM output

驗證：

* 至少一條正確法條
* 引用不可幻覺

### 11.5 Regression Tests

* alignment mapping 更新不可破壞舊情境

---

## 12. 📊 評測指標（Evaluation Metrics）

| 指標                  | 意義      | 目標     |
| ------------------- | ------- | ------ |
| Hit@5 (Statutes)    | 條文命中率   | ≥ 0.70 |
| Hit@5 (Cases)       | 案例命中率   | ≥ 0.60 |
| Alignment Precision | 召回品質    | ≥ 0.65 |
| 幻覺率                 | 引用不存在資料 | ≤ 5%   |
| 平均延遲                | UX      | ≤ 3s   |

---

## 13. 🧯 降級策略（Degrade Logic）

| 狀況           | 行為                |
| ------------ | ----------------- |
| Caption Fail | Text-only Query   |
| Mapping 不足   | Applications 補召回  |
| LLM Timeout  | 回傳 citations only |

---

## 14. 📐 安全性要求

* 不生成法律效力判決
* 僅作參考提示
* 明確 Disclaimer

---
