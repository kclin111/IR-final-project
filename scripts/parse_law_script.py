import os
import fitz  # PyMuPDF
import re
import csv
import unicodedata

# ========= 基本設定 =========
# 單一要 parsing 的 PDF 檔案名稱（跟本程式放同一層，或改成你的實際路徑）
script_dir = os.path.dirname(os.path.abspath(__file__))
INPUT_PDF = os.path.join(script_dir, "../data/道路交通管理處罰條例.pdf")
# 輸出資料夾與檔名
OUTPUT_DIR = os.path.join(script_dir, "../data")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "cleaned_道路交通管理處罰條例.csv")

def norm(s: str) -> str:
    """將字串正規化：全形轉半形、移除特殊空白、去除頭尾空白。"""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u200b", "").replace("\u00A0", " ").replace("\u3127", "\u4E00")
    return s.strip()

def clean_article_data(pdf_path):
    """
    解析單一 PDF 檔案，抽取出法規條文。
    支援「章」、「節」、條文，多行標題等。
    回傳 regulation_name, data_rows
    data_rows 每筆結構：
      {
        'cited_law': '道路交通管理處罰條例第X條(之X...)',
        '法規名稱': ...,
        '章名': ...,
        '節名': ...,
        '條號': ...,
        '條文內容': ...
      }
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = "".join(page.get_text("text") for page in doc)
        doc.close()
    except Exception as e:
        print(f"錯誤：無法開啟或讀取 {pdf_path}: {e}")
        return None, []

    regulation_name = norm(os.path.basename(pdf_path).replace(".pdf", ""))
    lines = full_text.split("\n")

    data_rows = []

    current_chapter = ""
    current_section = ""
    current_article_num = ""
    current_article_content_parts = []
    parsing_started = False

    def save_previous_article():
        nonlocal current_article_num, current_article_content_parts, data_rows
        nonlocal current_chapter, current_section

        if current_article_num:
            # 合併條文內容
            full_content = " ".join(current_article_content_parts)
            full_content = re.sub(r"\s+", " ", full_content).strip()

            # 條號正規化
            art_num = norm(current_article_num)
            # 第一欄：跟 cited law 一樣的格式
            cited_law = f"{regulation_name}{art_num}"

            data_rows.append({
                "cited_law": cited_law,
                "法規名稱": regulation_name,
                "章名": current_chapter,
                "節名": current_section,
                "條號": art_num,
                "條文內容": full_content,
            })

        # 清空目前累積
        current_article_num = ""
        current_article_content_parts = []

    # 正規表達式
    CHAPTER_RE = re.compile(r"^(第\s*[一二三四五六七八九十百千〇零\d]+\s*章.*)")
    SECTION_RE = re.compile(r"^(第\s*[一二三四五六七八九十百千〇零\d]+\s*節.*)")
    ARTICLE_RE = re.compile(
        r"^(第\s*\d+(?:-\d+)?\s*條(?:之\d+)*)\s*(.*)"
    )


    i = 0
    while i < len(lines):
        cleaned_line = norm(lines[i])

        if not cleaned_line:
            i += 1
            continue

        match_chapter = CHAPTER_RE.match(cleaned_line)
        match_section = SECTION_RE.match(cleaned_line)
        match_article = ARTICLE_RE.match(cleaned_line)

        # 還沒開始解析，直到遇到章/節/條才開始
        if not parsing_started:
            if match_chapter or match_section or match_article:
                parsing_started = True
            else:
                i += 1
                continue

        # ========== 章 ==========
        if match_chapter:
            save_previous_article()

            # 合併多行章標題
            temp_title_parts = [cleaned_line]
            j = i + 1
            while j < len(lines):
                next_line = norm(lines[j])
                if (not next_line or
                    CHAPTER_RE.match(next_line) or
                    SECTION_RE.match(next_line) or
                    ARTICLE_RE.match(next_line)):
                    break
                temp_title_parts.append(next_line)
                j += 1

            current_chapter = " ".join(temp_title_parts)
            current_section = ""  # 新章重置節
            i = j
            continue

        # ========== 節 ==========
        if match_section:
            save_previous_article()

            temp_title_parts = [cleaned_line]
            j = i + 1
            while j < len(lines):
                next_line = norm(lines[j])
                if (not next_line or
                    CHAPTER_RE.match(next_line) or
                    SECTION_RE.match(next_line) or
                    ARTICLE_RE.match(next_line)):
                    break
                temp_title_parts.append(next_line)
                j += 1

            current_section = " ".join(temp_title_parts)
            i = j
            continue

        # ========== 條（新條開始）==========
        if match_article:
            save_previous_article()
            current_article_num = match_article.group(1)
            same_line_content = match_article.group(2).strip()
            if same_line_content:
                current_article_content_parts.append(same_line_content)

        # ========== 條文內容（延續上一條）==========
        elif current_article_num:
            current_article_content_parts.append(cleaned_line)

        i += 1

    # 最後一條
    save_previous_article()

    return regulation_name, data_rows

def write_to_csv(output_path, data_rows):
    if not data_rows:
        print("沒有可輸出的資料。")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 第一欄就是 cited_law
    fieldnames = ["cited_law", "法規名稱", "章名", "節名", "條號", "條文內容"]

    try:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_rows)
        print(f"成功建立 CSV 檔案: {output_path}")
    except Exception as e:
        print(f"錯誤：寫入 {output_path} 失敗: {e}")

def main():
    if not os.path.exists(INPUT_PDF):
        print(f"找不到 PDF 檔案: {INPUT_PDF}")
        return

    print(f"正在處理：{INPUT_PDF}")
    _, rows = clean_article_data(INPUT_PDF)

    if not rows:
        print("未解析到任何條文資料。")
        return

    write_to_csv(OUTPUT_CSV, rows)
    print("處理完成！")

if __name__ == "__main__":
    main()
