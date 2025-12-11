"""
Simple retrieval script for law and case collections
直接對 law 和 case collection 做向量檢索，不做雙向擴展
"""
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.utils.vector_store import VectorStoreBuilder


class SimpleRetriever:
    """簡單的向量檢索器"""
    
    def __init__(self, persist_directory: str = "data/chroma_db"):
        """
        初始化檢索器
        
        Args:
            persist_directory: ChromaDB 儲存路徑
        """
        print("Loading vector stores...")
        builder = VectorStoreBuilder(persist_directory=persist_directory)
        self.law_collection = builder.load_law_collection()
        self.case_collection = builder.load_case_collection()
        print("✓ Vector stores loaded!")
    
    def search_laws(self, query: str, top_k: int = 5):
        """
        檢索相關法條
        
        Args:
            query: 查詢文字
            top_k: 回傳前 K 個結果
            
        Returns:
            法條列表，包含內容、metadata 和相似度分數
        """
        results = self.law_collection.similarity_search_with_score(query, k=top_k)
        
        laws = []
        for doc, score in results:
            laws.append({
                'cited_law': doc.metadata.get('cited_law', ''),
                '條號': doc.metadata.get('條號', ''),
                '條文內容': doc.metadata.get('條文內容', ''),
                'content': doc.page_content,
                'score': float(score),  # 距離分數，越小越相似
            })
        
        return laws
    
    def search_cases(self, query: str, top_k: int = 10):
        """
        檢索相關案例 chunks
        
        Args:
            query: 查詢文字
            top_k: 回傳前 K 個結果
            
        Returns:
            案例列表，包含內容、metadata、引用法條和相似度分數
        """
        results = self.case_collection.similarity_search_with_score(query, k=top_k)
        
        cases = []
        for doc, score in results:
            # 解析引用的法條
            cited_laws = []
            if 'cited_traffic_laws' in doc.metadata:
                try:
                    cited_laws = json.loads(doc.metadata['cited_traffic_laws'])
                except:
                    cited_laws = []
            
            cases.append({
                'case_id': doc.metadata.get('case_id', ''),
                'chunk_id': doc.metadata.get('chunk_id', ''),
                'court': doc.metadata.get('court', ''),
                'JDATE': doc.metadata.get('JDATE', ''),
                'JTITLE': doc.metadata.get('JTITLE', ''),
                'chunk_type': doc.metadata.get('chunk_type', ''),
                'content': doc.page_content,
                'cited_traffic_laws': cited_laws,  # 該案例引用的法條
                'score': float(score),
            })
        
        return cases
    
    def search_all(self, query: str, law_top_k: int = 5, case_top_k: int = 10):
        """
        同時檢索法條和案例
        
        Args:
            query: 查詢文字
            law_top_k: 法條回傳數量
            case_top_k: 案例回傳數量
            
        Returns:
            (laws, cases) 元組
        """
        laws = self.search_laws(query, top_k=law_top_k)
        cases = self.search_cases(query, top_k=case_top_k)
        
        return laws, cases
    
    def get_laws_from_cases(self, cases: list) -> list:
        """
        從案例結果中提取所有引用的法條（去重）
        
        Args:
            cases: search_cases 的回傳結果
            
        Returns:
            不重複的法條列表
        """
        all_laws = set()
        for case in cases:
            for law in case.get('cited_traffic_laws', []):
                all_laws.add(law)
        
        return sorted(list(all_laws))


def main():
    """測試檢索功能"""
    retriever = SimpleRetriever()
    
    # 測試查詢
    query = "酒駕肇事的罰則是什麼？"
    print(f"\n查詢: {query}")
    print("=" * 60)
    
    # 檢索法條
    print("\n【相關法條】")
    laws = retriever.search_laws(query, top_k=3)
    # output from back
    for i, law in enumerate(laws, 1):
        print(f"\n{i}. {law['條號']} (score: {law['score']:.4f})")
        print(f"   {law['條文內容']}...")
    
    # 檢索案例
    print("\n" + "=" * 60)
    print("\n【相關案例】")
    cases = retriever.search_cases(query, top_k=3)
    for i, case in enumerate(cases, 1):
        print(f"\n{i}. {case['case_id']} (score: {case['score']:.4f})")
        print(f"   法院: {case['court']}")
        print(f"   段落類型: {case['chunk_type']}")
        print(f"   引用法條: {case['cited_traffic_laws']}")
        print(f"   內容: {case['content']}...")
    
    # 從案例提取引用的法條
    print("\n" + "=" * 60)
    print("\n【案例中引用的法條】")
    cited_laws = retriever.get_laws_from_cases(cases)
    for law in cited_laws:
        print(f"  • {law}")


if __name__ == "__main__":
    main()
