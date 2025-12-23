import sys
import json
import csv
import random
import re
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.vector_store import VectorStoreBuilder


class GroundTruthGenerator:
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        print("Loading vector stores...")
        builder = VectorStoreBuilder(persist_directory=persist_directory)
        self.case_collection = builder.load_case_collection()
        print("✓ Loaded!")
    
    def generate_synthetic_queries(
        self,
        law_csv_path: str = "data/cleaned_道路交通管理處罰條例.csv",
        queries_per_law: int = 2
    ) -> List[Dict]:
        csv_path = project_root / law_csv_path
        
        if not csv_path.exists():
            print(f"Law CSV not found: {csv_path}")
            return []
        
        laws = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            reader = csv.DictReader(content.splitlines())
            laws = list(reader)
        
        item_pattern = re.compile(r'([一二三四五六七八九十]+)、([^一二三四五六七八九十]+?)(?=[一二三四五六七八九十]+、|$)')
        
        samples = []
        
        for law in laws:
            cited_law = law['cited_law']
            條號 = law['條號']
            條文內容 = law['條文內容']
            
            items = item_pattern.findall(條文內容)
            
            if items:
                for item_num, item_content in items:
                    item_content = item_content.strip()
                    
                    item_snippet = item_content[:100] if len(item_content) > 100 else item_content
                    
                    query = f"{item_snippet}會受到什麼處罰？"
                    
                    samples.append({
                        'query_id': f"synthetic_{cited_law}_penalty_{item_num}",
                        'query': query,
                        'relevant_laws': [cited_law],
                        'source': 'synthetic',
                        'template_type': 'penalty',
                        '條號': 條號,
                        '項目編號': f"{item_num}、"
                    })
        
        return samples
    
    def generate_from_cases(
            self, 
            case_path: str = "data/traffic_cases_chunks_evaluation.jsonl"
            ) -> List[Dict]:
        jsonl_path = project_root / case_path
        if not jsonl_path.exists():
            print(f"Cases JSONL not found: {jsonl_path}")
            return []
        
        samples = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for j, line in enumerate(f):
                case = json.loads(line)
                cited_laws = case.get('cited_traffic_laws', [])
                if not cited_laws:
                    continue
                
                chunks = case.get('chunks', [])[0]
                if not chunks:
                    continue
                query_text = chunks.get('text', '').strip()

                samples.append({
                    'query_id': f"case_{j}",
                    'query': query_text,
                    'relevant_laws': cited_laws,
                    'source': 'case'
                })
        return samples

    
    def export_for_annotation(
        self,
        samples: List[Dict],
        output_path: str,
        include_candidates: bool = True,
        num_candidates: int = 10
    ):
        if include_candidates:
            print("正在為每個樣本生成候選法條...")
            builder = VectorStoreBuilder(persist_directory="data/chroma_db")
            law_collection = builder.load_law_collection()
            
            for i, sample in enumerate(samples):
                results = law_collection.similarity_search_with_score(
                    sample['query'], k=num_candidates
                )
                
                sample['candidate_laws'] = [
                    {
                        'cited_law': doc.metadata.get('cited_law', ''),
                        '條號': doc.metadata.get('條號', ''),
                        '條文內容': doc.metadata.get('條文內容', '')[:100] + '...',
                        'score': float(score),
                        'is_relevant': doc.metadata.get('cited_law', '') in sample['relevant_laws']
                    }
                    for doc, score in results
                ]
                
                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i+1}/{len(samples)}")
        
        output_file = project_root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        export_data = {
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'num_samples': len(samples),
                'include_candidates': include_candidates
            },
            'samples': samples
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 匯出 {len(samples)} 個樣本到 {output_file}")
    
    def export_to_csv(self, samples: List[Dict], output_path: str):
        output_file = project_root / output_path
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'query_id',
                'query',
                'relevant_laws (自動標註)',
                'relevant_laws (人工修正)',
                'source',
                'notes'
            ])
            
            for sample in samples:
                writer.writerow([
                    sample.get('query_id', ''),
                    sample.get('query', ''),
                    '|'.join(sample.get('relevant_laws', [])),
                    '',  # 留空供人工填寫
                    sample.get('source', ''),
                    ''   # 留空供備註
                ])
        
        print(f"✓ 匯出 {len(samples)} 個樣本到 {output_file}")


def main():
    generator = GroundTruthGenerator()
    
    synthetic_samples = generator.generate_synthetic_queries(queries_per_law=2)
    print(f"{len(synthetic_samples)} samples generated from synthetic queries.")

    generator.export_for_annotation(
        synthetic_samples,
        output_path="evaluation/ground_truth_synthetic.json",
        include_candidates=True,
        num_candidates=10
    )
    
    generator.export_to_csv(
        synthetic_samples,
        output_path="evaluation/ground_truth_synthetic.csv"
    )

    case_samples = generator.generate_from_cases()
    print(f"{len(case_samples)} samples generated from real cases.")

    generator.export_for_annotation(
        case_samples,
        output_path="evaluation/ground_truth_case.json",
        include_candidates=True,
        num_candidates=10
    )

    generator.export_to_csv(
        case_samples,
        output_path="evaluation/ground_truth_case.csv"
    )

if __name__ == "__main__":
    main()
