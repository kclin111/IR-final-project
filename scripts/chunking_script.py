import os
import json
import re

# ========== 基本設定 ==========
script_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(script_dir, "../data/filtered_cases_evaluation")          # 你的原始 JSON 根目錄
OUTPUT_JSONL = os.path.join(script_dir, "../data/traffic_cases_chunks_evaluation.jsonl")
KEYWORD = "道路交通管理處罰條例"

# chunk 長度與 overlap 設定
MAX_CHARS = 600      # 每個 chunk 目標最大字數
MIN_CHARS = 150      # 最後一段太短就併回前一段
OVERLAP_RATIO = 0.4  # 兩段之間保留前一段尾巴的比例（0.1~0.2 建議）

# ========== regex：抓段落標題 ==========
# 調整為常見段落標題，避免過度嚴格（包含「事實」、「事實及理由」等）
SECTION_PATTERN = re.compile(
    r"(主文|理由要領|理由|事實及理由|事實|程序|本院之判斷|判斷|結論|上訴教示)"
)

# 抓「道路交通管理處罰條例」相關法條（含條/項/款）
TRAFFIC_LAW_PATTERN = re.compile(
    r"道路交通管理處罰條例第[^\s，。、；：\n]*條"
    r"(第[^\s，。、；：\n]*項)?"
    r"(第[^\s，。、；：\n]*款)?"
)

# ========== 工具函數們 ==========

def iter_json_files(root_dir: str):
    """遞迴走訪資料夾，取得所有 .json 檔路徑。"""
    for dirpath, _, filenames in os.walk(root_dir):
        for fn in filenames:
            if fn.lower().endswith(".json"):
                yield os.path.join(dirpath, fn)


def extract_traffic_laws(text: str):
    """從全文中抽出《道路交通管理處罰條例》相關條文（去重後保留順序）。"""
    seen = set()
    results = []
    for m in TRAFFIC_LAW_PATTERN.finditer(text):
        law = m.group(0)
        if law not in seen:
            seen.add(law)
            results.append(law)
    return results


def line_based_split_with_overlap(
    text: str,
    max_chars: int = MAX_CHARS,
    min_chars: int = MIN_CHARS,
    overlap_ratio: float = OVERLAP_RATIO,
):
    """
    逐行累積 + overlap 切 chunk：
    - 以非空白行為單位累積
    - 超過 max_chars 則切段
    - 下一段會帶入前一段尾端 overlap_ratio 的內容，避免語意斷裂
    - 最後一段太短則併回前一段
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    chunks = []
    buf = []

    for line in lines:
        candidate = " ".join(buf + [line]) if buf else line

        if len(candidate) >= max_chars:
            if buf:
                full_chunk = " ".join(buf).strip()
                if full_chunk:
                    chunks.append(full_chunk)

                    # 計算 overlap 內容
                    if overlap_ratio > 0 and len(full_chunk) > 0:
                        overlap_len = int(len(full_chunk) * overlap_ratio)
                        overlap_text = full_chunk[-overlap_len:]
                        # 新一段從 overlap_text + 當前這行開始
                        buf = [overlap_text, line]
                    else:
                        buf = [line]
                else:
                    buf = [line]
            else:
                # 單行就超長，直接當一段
                chunks.append(line.strip())
                buf = []
        else:
            buf.append(line)

    # 收尾
    if buf:
        last = " ".join(buf).strip()
        if last:
            if chunks and len(last) < min_chars:
                chunks[-1] = (chunks[-1] + " " + last).strip()
            else:
                chunks.append(last)

    # 過濾空字串
    return [c for c in chunks if c]


def section_based_chunks(jfull: str):
    """
    結構導向 + 逐行切 + overlap：
    - 若有主文/理由/事實等標題，依標題區塊分段，再對每個區塊做 line-based overlap 切割
    - 若沒有找到標題，則直接對全文做 line-based overlap 切割
    """
    matches = list(SECTION_PATTERN.finditer(jfull))
    if not matches:
        return line_based_split_with_overlap(jfull)

    chunks = []

    for i, m in enumerate(matches):
        title = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(jfull)
        content = jfull[start:end].strip()
        if not content:
            continue

        # 保留段落標題，讓 chunk 有語意錨點
        section_text = f"{title}：{content}"
        section_chunks = line_based_split_with_overlap(section_text)
        chunks.extend(section_chunks)

    return chunks


def guess_court(jfull: str):
    """
    嘗試從第一行猜法院名稱。
    多數裁判書第一行為「○○法院○○判決」。
    """
    first_line = jfull.splitlines()[0].strip()
    return first_line if "法院" in first_line else None


def process_case(path: str):
    """
    處理單一 JSON：
    - 若未提及「道路交通管理處罰條例」則略過
    - 抽取相關法條
    - 以結構導向 + overlap 切成 chunks
    - 回傳 {meta, chunks}，失敗或不符則回傳 None
    """
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except Exception as e:
            print(f"[WARN] JSON parse error: {path}: {e}")
            return None

    jfull = data.get("JFULL") or data.get("jfull")
    if not jfull:
        return None

    # 僅保留與道路交通管理處罰條例相關案件
    if KEYWORD not in jfull:
        return None

    # 抽取條文（僅交通管理處罰條例）
    cited_traffic_laws = extract_traffic_laws(jfull)

    if not cited_traffic_laws:
        return None

    jid = data.get("JID") or data.get("jid") or os.path.basename(path)

    # 切 chunks
    chunk_texts = section_based_chunks(jfull)
    if not chunk_texts:
        return None

    # 組 metadata
    meta = {
        "id": jid,
        "JID": jid,
        "JYEAR": data.get("JYEAR"),
        "JCASE": data.get("JCASE"),
        "JNO": data.get("JNO"),
        "JDATE": data.get("JDATE"),
        "JTITLE": data.get("JTITLE"),
        "court": guess_court(jfull),
        "JPDF": data.get("JPDF"),
        "is_traffic_case": True,
        "cited_traffic_laws": cited_traffic_laws,
    }

    # 組 chunks
    chunks = []
    for idx, txt in enumerate(chunk_texts, start=1):
        chunks.append(
            {
                "chunk_id": f"{jid}-{idx}",
                "text": txt,
            }
        )

    return {"meta": meta, "chunks": chunks}


# ========== 主流程：輸出 JSONL ==========
def main():
    count_cases = 0
    count_chunks = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
        for path in iter_json_files(INPUT_DIR):
            result = process_case(path)
            if not result:
                continue

            record = {
                **result["meta"],
                "chunks": result["chunks"],
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

            count_cases += 1
            count_chunks += len(result["chunks"])

    print(f"完成：共保留 {count_cases} 筆交通相關案件，產生 {count_chunks} 個 chunks。")
    print(f"輸出檔案：{OUTPUT_JSONL}")


if __name__ == "__main__":
    main()
