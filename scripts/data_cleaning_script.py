import os
import json
import shutil
from tqdm import tqdm

script_dir = os.path.dirname(os.path.abspath(__file__))
root_folder = os.path.join(script_dir, "../data/202508")
output_folder = os.path.join(script_dir, "../data/filtered_cases")
keyword = "道路交通管理處罰條例"

for dirpath, _, filenames in os.walk(root_folder):
    for filename in tqdm(filenames, desc=f"掃描中: {os.path.basename(dirpath)}"):
        if not filename.endswith(".json"):
            continue
        file_path = os.path.join(dirpath, filename)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            print(f"❌ 讀取錯誤: {file_path}, {e}")
            continue

        # 檢查是否含有關鍵字
        if keyword in text:
            # 保留資料夾層級 (例如「三重簡易庭刑事」)
            rel_dir = os.path.relpath(dirpath, root_folder)
            target_dir = os.path.join(output_folder, rel_dir)
            os.makedirs(target_dir, exist_ok=True)

            shutil.copy(file_path, os.path.join(target_dir, filename))
