"""
Retrieval logic with expansion
Implements single-layer bidirectional expansion with deduplication
"""
import json
from typing import List, Dict, Any, Set, Optional, Tuple
from langchain_chroma import Chroma
from app.utils.mapping import LawCaseMapping
from app.config import settings


class RetrievalEngine:
    """
    Retrieval engine with law-case expansion
    Implements single-layer bidirectional retrieval strategy
    """

    def __init__(
        self,
        law_collection: Chroma,
        case_collection: Chroma,
        mapping: LawCaseMapping,
        law_top_k: int = 5,
        case_top_k: int = 5,
        expand_cases_per_law: int = 3
    ):
        """
        Initialize retrieval engine

        Args:
            law_collection: Law knowledge points vector store
            case_collection: Case applications vector store
            mapping: Law-case mapping
            law_top_k: Number of laws to retrieve
            case_top_k: Number of cases to retrieve
            expand_cases_per_law: Number of cases to expand per law
        """
        self.law_collection = law_collection
        self.case_collection = case_collection
        self.mapping = mapping
        self.law_top_k = law_top_k
        self.case_top_k = case_top_k
        self.expand_cases_per_law = expand_cases_per_law

    def retrieve(self, query: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Main retrieval method with expansion and deduplication

        Args:
            query: User query text

        Returns:
            Tuple of (all_laws, all_cases) dictionaries
        """
        print(f"\n=== Retrieval for query: {query[:50]}... ===")

        # Step 1: Direct retrieval
        retrieved_laws = self._retrieve_laws(query, self.law_top_k)
        retrieved_cases = self._retrieve_cases(query, self.case_top_k)

        print(f"✓ Retrieved {len(retrieved_laws)} laws directly")
        print(f"✓ Retrieved {len(retrieved_cases)} case chunks directly")

        # Step 2: Expand from laws to cases
        expanded_cases_from_law = self._expand_cases_from_laws(retrieved_laws)
        print(f"✓ Expanded {len(expanded_cases_from_law)} case IDs from laws")

        # Step 3: Expand from cases to laws
        expanded_laws_from_case = self._expand_laws_from_cases(retrieved_cases)
        print(f"✓ Expanded {len(expanded_laws_from_case)} laws from cases")

        # Step 4: Deduplicate and merge
        all_laws = self._merge_laws(retrieved_laws, expanded_laws_from_case)
        all_cases = self._merge_cases(retrieved_cases, expanded_cases_from_law)

        print(f"✓ Final: {len(all_laws)} unique laws, {len(all_cases)} unique cases")

        return all_laws, all_cases

    def _retrieve_laws(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Retrieve laws using vector similarity

        Args:
            query: Query text
            top_k: Number of results

        Returns:
            List of law documents with metadata and scores
        """
        results = self.law_collection.similarity_search_with_score(query, k=top_k)

        laws = []
        for doc, score in results:
            laws.append({
                'document': doc,
                'metadata': doc.metadata,
                'score': float(score),
                'content': doc.page_content
            })

        return laws

    def _retrieve_cases(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Retrieve case chunks using vector similarity

        Args:
            query: Query text
            top_k: Number of results

        Returns:
            List of case chunk documents with metadata and scores
        """
        results = self.case_collection.similarity_search_with_score(query, k=top_k)

        cases = []
        for doc, score in results:
            # Parse cited_traffic_laws from JSON string
            cited_laws = []
            if 'cited_traffic_laws' in doc.metadata:
                try:
                    cited_laws = json.loads(doc.metadata['cited_traffic_laws'])
                except:
                    cited_laws = []

            cases.append({
                'document': doc,
                'metadata': doc.metadata,
                'score': float(score),
                'content': doc.page_content,
                'cited_traffic_laws': cited_laws
            })

        return cases

    def _expand_cases_from_laws(
        self,
        laws: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Expand cases from retrieved laws

        Args:
            laws: Retrieved law documents

        Returns:
            Dictionary of case_id -> case info
        """
        expanded_cases = {}

        for law_info in laws:
            law_id = law_info['metadata']['cited_law']

            # Get associated cases (limit to expand_cases_per_law)
            cases = self.mapping.get_cases_for_law(
                law_id,
                limit=self.expand_cases_per_law
            )

            for case_info in cases:
                case_id = case_info['case_id']

                if case_id not in expanded_cases:
                    expanded_cases[case_id] = {
                        'case_id': case_id,
                        'chunk_ids': case_info['chunk_ids'],
                        'sources': ['law_expansion'],
                        'via_laws': [law_id]
                    }
                else:
                    # Already exists, add source
                    if 'law_expansion' not in expanded_cases[case_id]['sources']:
                        expanded_cases[case_id]['sources'].append('law_expansion')
                    expanded_cases[case_id]['via_laws'].append(law_id)

        return expanded_cases

    def _expand_laws_from_cases(
        self,
        cases: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Expand laws from retrieved cases

        Args:
            cases: Retrieved case chunk documents

        Returns:
            Dictionary of law_id -> law info
        """
        expanded_laws = {}

        for case_info in cases:
            case_id = case_info['metadata']['case_id']
            cited_laws = case_info.get('cited_traffic_laws', [])

            for law_id in cited_laws:
                if law_id not in expanded_laws:
                    expanded_laws[law_id] = {
                        'law_id': law_id,
                        'sources': ['case_expansion'],
                        'via_cases': [case_id]
                    }
                else:
                    # Already exists, add source
                    if 'case_expansion' not in expanded_laws[law_id]['sources']:
                        expanded_laws[law_id]['sources'].append('case_expansion')
                    expanded_laws[law_id]['via_cases'].append(case_id)

        return expanded_laws

    def _merge_laws(
        self,
        retrieved_laws: List[Dict[str, Any]],
        expanded_laws: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Merge and deduplicate laws

        Args:
            retrieved_laws: Directly retrieved laws
            expanded_laws: Laws expanded from cases

        Returns:
            Deduplicated dictionary of law_id -> law data
        """
        all_laws = {}

        # Add directly retrieved laws
        for law_info in retrieved_laws:
            law_id = law_info['metadata']['cited_law']
            all_laws[law_id] = {
                'law_id': law_id,
                'metadata': law_info['metadata'],
                'content': law_info['metadata']['條文內容'],
                'sources': ['direct_retrieval'],
                'score': law_info['score'],
                'via_cases': []
            }

        # Add/merge expanded laws
        for law_id, law_data in expanded_laws.items():
            if law_id in all_laws:
                # Already exists from direct retrieval, add sources
                all_laws[law_id]['sources'].extend(law_data['sources'])
                all_laws[law_id]['via_cases'] = law_data.get('via_cases', [])
            else:
                # New law from expansion, need to load content
                law_content = self._load_law_by_id(law_id)
                if law_content:
                    all_laws[law_id] = {
                        'law_id': law_id,
                        'metadata': law_content,
                        'content': law_content.get('條文內容', ''),
                        'sources': law_data['sources'],
                        'score': None,  # No similarity score
                        'via_cases': law_data.get('via_cases', [])
                    }

        return all_laws

    def _merge_cases(
        self,
        retrieved_cases: List[Dict[str, Any]],
        expanded_cases: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Merge and deduplicate cases (complete cases, not chunks)

        Args:
            retrieved_cases: Directly retrieved case chunks
            expanded_cases: Cases expanded from laws

        Returns:
            Deduplicated dictionary of case_id -> full case data
        """
        all_cases = {}

        # Add directly retrieved cases (group by case_id)
        for case_chunk in retrieved_cases:
            case_id = case_chunk['metadata']['case_id']

            if case_id not in all_cases:
                # Load complete case
                full_case = self._load_complete_case(case_id)
                all_cases[case_id] = {
                    'case_id': case_id,
                    'metadata': full_case['metadata'],
                    'chunks': full_case['chunks'],
                    'sources': ['direct_retrieval'],
                    'score': case_chunk['score'],
                    'via_laws': [],
                    'retrieved_chunk_id': case_chunk['metadata']['chunk_id']
                }
            # If already exists, we don't need to do anything (same case)

        # Add/merge expanded cases
        for case_id, case_data in expanded_cases.items():
            if case_id in all_cases:
                # Already exists from direct retrieval, add sources
                all_cases[case_id]['sources'].extend(case_data['sources'])
                all_cases[case_id]['via_laws'] = case_data.get('via_laws', [])
            else:
                # New case from expansion
                full_case = self._load_complete_case(case_id)
                if full_case:
                    all_cases[case_id] = {
                        'case_id': case_id,
                        'metadata': full_case['metadata'],
                        'chunks': full_case['chunks'],
                        'sources': case_data['sources'],
                        'score': None,  # No similarity score
                        'via_laws': case_data.get('via_laws', []),
                        'retrieved_chunk_id': None
                    }

        return all_cases

    def _load_law_by_id(self, law_id: str) -> Optional[Dict[str, Any]]:
        """
        Load law metadata by ID from vector store

        Args:
            law_id: Law identifier

        Returns:
            Law metadata dictionary or None
        """
        # Query vector store by metadata filter
        results = self.law_collection.get(
            where={"cited_law": law_id},
            limit=1
        )

        if results and results['metadatas']:
            return results['metadatas'][0]

        return None

    def _load_complete_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Load complete case with all chunks from vector store

        Args:
            case_id: Case identifier

        Returns:
            Complete case data with all chunks
        """
        # Query all chunks for this case
        results = self.case_collection.get(
            where={"case_id": case_id}
        )

        if not results or not results['metadatas']:
            return None

        # Extract metadata from first chunk (case-level info is same across chunks)
        first_metadata = results['metadatas'][0]

        # Parse cited_traffic_laws
        cited_laws = []
        if 'cited_traffic_laws' in first_metadata:
            try:
                cited_laws = json.loads(first_metadata['cited_traffic_laws'])
            except:
                cited_laws = []

        # Collect all chunks
        chunks = []
        for i, chunk_text in enumerate(results['documents']):
            chunk_metadata = results['metadatas'][i]
            chunks.append({
                'chunk_id': chunk_metadata['chunk_id'],
                'text': chunk_text,
                'chunk_type': chunk_metadata.get('chunk_type', 'unknown')
            })

        # Sort chunks by chunk_id to maintain order
        chunks.sort(key=lambda x: x['chunk_id'])

        return {
            'case_id': case_id,
            'metadata': {
                'JID': first_metadata['JID'],
                'JYEAR': first_metadata['JYEAR'],
                'JCASE': first_metadata['JCASE'],
                'JNO': first_metadata['JNO'],
                'JDATE': first_metadata['JDATE'],
                'JTITLE': first_metadata['JTITLE'],
                'court': first_metadata['court'],
                'JPDF': first_metadata['JPDF'],
                'cited_traffic_laws': cited_laws
            },
            'chunks': chunks
        }
