import os
import csv
import json
import re
import unicodedata
from collections import defaultdict

BASE_DIR = os.path.dirname(__file__)

# 路徑設定：依照你目前說的結構
LAW_CSV = os.path.join(BASE_DIR, "..", "data", "cleaned_道路交通管理處罰條例.csv")
CASES_JSONL = os.path.join(BASE_DIR, "..", "data", "traffic_cases_chunks.jsonl")
OUTPUT_JSON = os.path.join(BASE_DIR, "..", "data", "law_case_mapping.json")

# ========== 基本工具 ==========

def norm(s: str) -> str:
    """基本正規化：全形轉半形、去掉零寬空白、trim。"""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u200b", "").replace("\u00A0", " ")
    return s.strip()

def normalize_law_id(raw: str) -> str:
    """
    統一 law key 格式：
    - 全形轉半形
    - 去空白
    例如：
      '道路交通管理處罰條例第 1 條' -> '道路交通管理處罰條例第1條'
    """
    s = norm(raw)
    s = s.replace(" ", "")
    return s

# 強化版 regex：抓判決文字中出現的「道路交通管理處罰條例第X條...」
LAW_REF_PATTERN = re.compile(
    r"(道路交通管理處罰條例第\s*\d+(?:-\d+)?\s*條"
    r"(?:之\s*\d+)?"
    r"(?:第\s*\d+\s*項)?"
    r"(?:第\s*\d+\s*款)?)"
)

# ========== 讀取法條 CSV ==========

def load_laws(csv_path: str):
    """
    讀取 cleaned_道路交通管理處罰條例.csv
    回傳 dict:
      key = normalized law id (ex: '道路交通管理處罰條例第1條')
      value = {
        'cited_law': 原始欄位,
        '法規名稱': ...,
        '章名': ...,
        '節名': ...,
        '條號': ...,
        '條文內容': ...,
        'cases': []  # 之後填
      }
    """
    laws = {}
    if not os.path.exists(csv_path):
        print(f"[ERROR] 找不到法條 CSV：{csv_path}")
        return laws

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_cited = row.get("cited_law") or ""
            key = normalize_law_id(raw_cited)
            if not key:
                continue
            if key in laws:
                # 同一條多次出現（多行情況）可以選擇合併，先簡單跳過或覆蓋
                continue

            laws[key] = {
                "cited_law": norm(raw_cited),
                "法規名稱": norm(row.get("法規名稱", "")),
                "章名": norm(row.get("章名", "")),
                "節名": norm(row.get("節名", "")),
                "條號": norm(row.get("條號", "")),
                "條文內容": norm(row.get("條文內容", "")),
                "cases": []  # 之後填入 {case_id, chunk_ids}
            }

    print(f"[INFO] 載入法條 {len(laws)} 條。")
    return laws

# ========== 掃描判例 JSONL，建立 mapping ==========

def build_mapping(laws: dict, cases_jsonl: str):
    """
    將判例中的「道路交通管理處罰條例第X條...」對應到 laws dict。
    - 從每個 chunk 的 text 掃描
    - 找到對應法條 key → 將 case 加入 laws[key]['cases']
    """
    if not os.path.exists(cases_jsonl):
        print(f"[WARN] 找不到判例 JSONL：{cases_jsonl}")
        return laws

    # 為了避免重複，對每個 law key 用 set 暫存 (case_id, chunk_id)
    law_case_links = defaultdict(set)

    with open(cases_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
            except Exception as e:
                print(f"[WARN] JSON parse error: {e}")
                continue

            case_id = case.get("id") or case.get("JID")
            chunks = case.get("chunks", [])
            if not case_id or not chunks:
                continue

            for ch in chunks:
                chunk_id = ch.get("chunk_id")
                text = norm(ch.get("text", ""))
                if not text:
                    continue

                for m in LAW_REF_PATTERN.finditer(text):
                    raw_ref = m.group(1)
                    key = normalize_law_id(raw_ref)

                    # 嘗試對齊到「條」層級：只拿到「...第X條」當 key
                    # 例如 "道路交通管理處罰條例第82條第1項第1款" -> "道路交通管理處罰條例第82條"
                    base_key = re.sub(r"(第\s*\d+\s*條).*", r"\1", key)
                    base_key = base_key.replace(" ", "")

                    # 優先匹配完整 key，其次 base_key
                    candidate_keys = []
                    if key in laws:
                        candidate_keys.append(key)
                    if base_key in laws and base_key not in candidate_keys:
                        candidate_keys.append(base_key)

                    for k in candidate_keys:
                        law_case_links[k].add((case_id, chunk_id))

    # 寫回到 laws 結構
    for k, links in law_case_links.items():
        if k not in laws:
            continue
        # 轉成 {case_id, chunk_ids: [...]} 的結構
        grouped = defaultdict(list)
        for case_id, chunk_id in links:
            if chunk_id:
                grouped[case_id].append(chunk_id)
            else:
                grouped[case_id]  # 至少確保 key 存在

        laws[k]["cases"] = [
            {"case_id": cid, "chunk_ids": sorted(set(cids))}
            for cid, cids in grouped.items()
        ]

    return laws

# ========== 主程式 ==========

def main():
    laws = load_laws(LAW_CSV)
    if not laws:
        return

    laws_with_mapping = build_mapping(laws, CASES_JSONL)

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(laws_with_mapping, f, ensure_ascii=False, indent=2)

    # 簡單統計
    total_laws = len(laws_with_mapping)
    with_cases = sum(1 for v in laws_with_mapping.values() if v["cases"])
    print(f"[INFO] 總條文數: {total_laws}")
    print(f"[INFO] 有至少一個判例連結的條文數: {with_cases}")
    print(f"[INFO] 已輸出 mapping 至: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
