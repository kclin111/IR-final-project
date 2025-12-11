import sys
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import math
import unicodedata

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.vector_store import VectorStoreBuilder
from generate_ground_truth import GroundTruthGenerator
from simple_retrieval import SimpleRetriever


class RetrievalEvaluator:
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        print("Loading vector stores...")
        builder = VectorStoreBuilder(persist_directory=persist_directory)
        self.law_collection = builder.load_law_collection()
        self.case_collection = builder.load_case_collection()
        print("Vector stores loaded!")
        
        self.law_data = self._load_law_data()
    
    def _load_law_data(self) -> Dict[str, Dict]:
        import csv
        law_data = {}
        csv_path = project_root / "data" / "cleaned_道路交通管理處罰條例.csv"
        
        if csv_path.exists():
            with open(csv_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.startswith('\ufeff'):
                    content = content[1:]
                reader = csv.DictReader(content.splitlines())
                for row in reader:
                    law_data[row['cited_law']] = row
        
        return law_data
    
    
    def precision_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """計算 Precision@K"""
        retrieved_k = retrieved[:k]
        relevant_set = set(relevant)
        hits = sum(1 for r in retrieved_k if r in relevant_set)
        return hits / k if k > 0 else 0.0
    
    def recall_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """計算 Recall@K"""
        retrieved_k = set(retrieved[:k])
        relevant_set = set(relevant)
        hits = len(retrieved_k & relevant_set)
        return hits / len(relevant_set) if relevant_set else 0.0
    
    def mrr(self, retrieved: List[str], relevant: List[str]) -> float:
        """計算 MRR (Mean Reciprocal Rank)"""
        relevant_set = set(relevant)
        for i, r in enumerate(retrieved):
            if r in relevant_set:
                return 1.0 / (i + 1)
        return 0.0
    
    def ndcg_at_k(self, retrieved: List[str], relevant: List[str], k: int) -> float:
        """計算 NDCG@K"""
        import math
        
        relevant_set = set(relevant)
        
        # DCG
        dcg = 0.0
        for i, r in enumerate(retrieved[:k]):
            if r in relevant_set:
                dcg += 1.0 / math.log2(i + 2)  # i+2 因為 log2(1) = 0
        
        # IDCG (理想情況)
        idcg = sum(1.0 / math.log2(i + 2) for i in range(min(len(relevant_set), k)))
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def norm(self, s: str) -> str:
        """基本正規化：全形轉半形、去掉零寬空白、trim。"""
        if not isinstance(s, str):
            return ""
        s = unicodedata.normalize("NFKC", s)
        s = s.replace("\u200b", "").replace("\u00A0", " ")
        return s.strip()

    def normalize_law_id(self, raw: str) -> str:
        s = self.norm(raw)
        s = s.replace(" ", "")
        return s
    
    
    def evaluate_law_retrieval(
        self,
        test_samples: List[Dict],
        top_k_values: List[int] = [1, 3, 5, 10]
    ) -> Dict[str, Any]:
        print(f"\n評估法條檢索效能 (n={len(test_samples)})...")
        
        results = {k: {'precision': [], 'recall': [], 'mrr': [], 'ndcg': []} 
                   for k in top_k_values}
        
        max_k = max(top_k_values)
        
        for i, sample in enumerate(test_samples):
            query = sample['query']
            ground_truth = sample.get('ground_truth_laws') or sample.get('relevant_laws', [])
            
            search_results = self.law_collection.similarity_search_with_score(
                query, k=max_k
            )
            
            retrieved_laws = [
                doc.metadata.get('cited_law', '') 
                for doc, score in search_results
            ]
            
            for k in top_k_values:
                results[k]['precision'].append(
                    self.precision_at_k(retrieved_laws, ground_truth, k)
                )
                results[k]['recall'].append(
                    self.recall_at_k(retrieved_laws, ground_truth, k)
                )
                results[k]['mrr'].append(
                    self.mrr(retrieved_laws[:k], ground_truth)
                )
                results[k]['ndcg'].append(
                    self.ndcg_at_k(retrieved_laws, ground_truth, k)
                )
        
        summary = {}
        for k in top_k_values:
            summary[f'P@{k}'] = sum(results[k]['precision']) / len(results[k]['precision'])
            summary[f'R@{k}'] = sum(results[k]['recall']) / len(results[k]['recall'])
            summary[f'MRR@{k}'] = sum(results[k]['mrr']) / len(results[k]['mrr'])
            summary[f'NDCG@{k}'] = sum(results[k]['ndcg']) / len(results[k]['ndcg'])
        
        return summary
    
    def evaluate_case_to_law_retrieval(
        self,
        test_samples: List[Dict],
        top_k_values: List[int] = [1, 3, 5, 10],
        law_case_mapping_path: str = "data/law_case_mapping.json"
    ) -> Dict[str, Any]:
        """
        評估 法條→案例→法條 的檢索效能
        
        流程：
        1. Query → 檢索法條
        2. 法條 → 透過 law_case_mapping 找到相關判例
        3. 判例 → 提取判例中引用的法條
        4. 與 ground truth 比對
        """
        print(f"\n評估 法條→案例→法條 檢索效能 (n={len(test_samples)})...")
        
        # 載入 law_case_mapping
        mapping_path = project_root / law_case_mapping_path
        if not mapping_path.exists():
            print(f"Warning: {mapping_path} not found, skipping this evaluation")
            return {}
        
        with open(mapping_path, 'r', encoding='utf-8') as f:
            law_case_mapping = json.load(f)
        
        results = {k: {'precision': [], 'recall': [], 'mrr': [], 'ndcg': []} 
                   for k in top_k_values}
        
        max_k = max(top_k_values)
        
        for i, sample in enumerate(test_samples):
            query = sample['query']
            ground_truth = sample.get('ground_truth_laws') or sample.get('relevant_laws', [])
            
            # Step 1: Query → 檢索法條
            law_search_results = self.law_collection.similarity_search_with_score(
                query, k=max_k
            )
            
            # 提取檢索到的法條
            retrieved_law_ids = [
                doc.metadata.get('cited_law', '') 
                for doc, score in law_search_results
            ]

            # 正規化法條 ID
            retrieved_law_ids = [self.normalize_law_id(law_id) for law_id in retrieved_law_ids]

            # Step 2: 法條 → 透過 law_case_mapping 找到相關判例的 chunk_ids
            related_case_chunk_ids = set()
            for law_id in retrieved_law_ids:
                if law_id in law_case_mapping:
                    cases = law_case_mapping[law_id].get('cases', [])
                    for case in cases:
                        for chunk_id in case.get('chunk_ids', []):
                            related_case_chunk_ids.add(chunk_id)
            
            # Step 3: 從判例 chunks 中提取引用的法條
            # 從 case_collection 取得這些 chunk_ids 的 metadata
            final_retrieved_laws = []
            seen = set()
            
            if related_case_chunk_ids:
                # 使用 chunk_id 查詢 case_collection
                case_results = self.case_collection.get(
                    ids=list(related_case_chunk_ids)[:100]  # 限制數量避免太慢
                )
                
                if case_results and case_results.get('metadatas'):
                    for meta in case_results['metadatas']:
                        cited = meta.get('cited_traffic_laws', '[]')
                        try:
                            laws = json.loads(cited)
                            for law in laws:
                                if law not in seen:
                                    seen.add(law)
                                    final_retrieved_laws.append(law)
                        except:
                            continue

            # 正規化 ground truth 法條 ID
            ground_truth = [self.normalize_law_id(law_id) for law_id in ground_truth]

            # 計算各 K 值的指標
            for k in top_k_values:
                results[k]['precision'].append(
                    self.precision_at_k(final_retrieved_laws, ground_truth, k)
                )
                results[k]['recall'].append(
                    self.recall_at_k(final_retrieved_laws, ground_truth, k)
                )
                results[k]['mrr'].append(
                    self.mrr(final_retrieved_laws[:k], ground_truth)
                )
                results[k]['ndcg'].append(
                    self.ndcg_at_k(final_retrieved_laws, ground_truth, k)
                )
        
        # 計算平均值
        summary = {}
        for k in top_k_values:
            summary[f'P@{k}'] = sum(results[k]['precision']) / len(results[k]['precision'])
            summary[f'R@{k}'] = sum(results[k]['recall']) / len(results[k]['recall'])
            summary[f'MRR@{k}'] = sum(results[k]['mrr']) / len(results[k]['mrr'])
            summary[f'NDCG@{k}'] = sum(results[k]['ndcg']) / len(results[k]['ndcg'])
        
        return summary
    
    def print_results(self, results: Dict[str, float], title: str):
        """印出評估結果"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print('='*60)
        
        # 整理成表格
        metrics = ['P', 'R', 'MRR', 'NDCG']
        k_values = sorted(set(int(k.split('@')[1]) for k in results.keys()))
        
        # 印出表頭
        header = f"{'Metric':<10}" + "".join(f"{'@'+str(k):>10}" for k in k_values)
        print(header)
        print("-" * len(header))
        
        for metric in metrics:
            row = f"{metric:<10}"
            for k in k_values:
                key = f"{metric}@{k}"
                if key in results:
                    row += f"{results[key]:>10.4f}"
                else:
                    row += f"{'N/A':>10}"
            print(row)


def main():
    evaluator = RetrievalEvaluator()
    gt_generator = GroundTruthGenerator()

    synthetic_samples = gt_generator.generate_synthetic_queries(queries_per_law=2)

    synthetic_results = evaluator.evaluate_law_retrieval(synthetic_samples)
    evaluator.print_results(synthetic_results, "RAG 檢索法條")

    synthetic_results2 = evaluator.evaluate_case_to_law_retrieval(synthetic_samples)
    evaluator.print_results(synthetic_results2, "RAG 檢索法條＋案例擴充")

    print("""
評估指標說明：
- P@K (Precision@K): 前 K 個結果中相關的比例
- R@K (Recall@K): 找到的相關結果佔所有相關結果的比例  
- MRR@K: 第一個正確結果的排名倒數（越高越好）
- NDCG@K: 考慮排名位置的相關性評估（越高越好）

建議：
- P@1 > 0.5: 檢索準確度良好
- R@5 > 0.7: 召回率良好
- MRR > 0.5: 排序品質良好
""")


if __name__ == "__main__":
    main()
