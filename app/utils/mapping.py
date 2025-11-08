"""
Law-Case mapping utilities
Handles loading and querying law-case relationships
"""
import json
from typing import Dict, List, Set, Optional
from pathlib import Path


class LawCaseMapping:
    """Manages law-case mapping relationships"""

    def __init__(self, mapping_path: str = None):
        """
        Initialize mapping

        Args:
            mapping_path: Path to law_case_mapping.json
        """
        self.mapping_path = mapping_path or "data/law_case_mapping.json"
        self.law_to_cases: Dict[str, Dict] = {}
        self.chunk_to_laws: Dict[str, List[str]] = {}
        self.case_to_laws: Dict[str, List[str]] = {}
        self._load_mapping()

    def _load_mapping(self):
        """Load mapping from JSON file"""
        print(f"Loading law-case mapping from {self.mapping_path}...")

        with open(self.mapping_path, 'r', encoding='utf-8') as f:
            self.law_to_cases = json.load(f)

        # Build reverse indices
        self._build_reverse_indices()

        print(f"✓ Loaded {len(self.law_to_cases)} law-case mappings")
        print(f"✓ Built reverse index for {len(self.chunk_to_laws)} chunks")

    def _build_reverse_indices(self):
        """Build reverse indices for efficient lookup"""
        self.chunk_to_laws = {}
        self.case_to_laws = {}

        for law_id, law_data in self.law_to_cases.items():
            for case_info in law_data.get('cases', []):
                case_id = case_info['case_id']

                # Case to laws mapping
                if case_id not in self.case_to_laws:
                    self.case_to_laws[case_id] = []
                if law_id not in self.case_to_laws[case_id]:
                    self.case_to_laws[case_id].append(law_id)

                # Chunk to laws mapping
                for chunk_id in case_info['chunk_ids']:
                    if chunk_id not in self.chunk_to_laws:
                        self.chunk_to_laws[chunk_id] = []
                    if law_id not in self.chunk_to_laws[chunk_id]:
                        self.chunk_to_laws[chunk_id].append(law_id)

    def get_cases_for_law(
        self,
        law_id: str,
        limit: int = None
    ) -> List[Dict[str, any]]:
        """
        Get cases associated with a law

        Args:
            law_id: Law identifier (e.g., "道路交通管理處罰條例第21條")
            limit: Maximum number of cases to return

        Returns:
            List of case info dicts with case_id and chunk_ids
        """
        if law_id not in self.law_to_cases:
            return []

        cases = self.law_to_cases[law_id].get('cases', [])

        if limit:
            return cases[:limit]
        return cases

    def get_chunk_ids_for_law(
        self,
        law_id: str,
        limit_cases: int = None,
        limit_chunks_per_case: int = None
    ) -> List[str]:
        """
        Get chunk IDs associated with a law

        Args:
            law_id: Law identifier
            limit_cases: Maximum number of cases to retrieve
            limit_chunks_per_case: Maximum chunks per case

        Returns:
            List of chunk IDs
        """
        cases = self.get_cases_for_law(law_id, limit=limit_cases)

        chunk_ids = []
        for case_info in cases:
            case_chunks = case_info['chunk_ids']
            if limit_chunks_per_case:
                case_chunks = case_chunks[:limit_chunks_per_case]
            chunk_ids.extend(case_chunks)

        return chunk_ids

    def get_laws_for_chunk(self, chunk_id: str) -> List[str]:
        """
        Get laws associated with a chunk

        Args:
            chunk_id: Chunk identifier

        Returns:
            List of law IDs
        """
        return self.chunk_to_laws.get(chunk_id, [])

    def get_laws_for_case(self, case_id: str) -> List[str]:
        """
        Get laws associated with a case

        Args:
            case_id: Case identifier

        Returns:
            List of law IDs
        """
        return self.case_to_laws.get(case_id, [])

    def get_all_law_ids(self) -> List[str]:
        """
        Get all law IDs in mapping

        Returns:
            List of law IDs
        """
        return list(self.law_to_cases.keys())

    def get_all_case_ids(self) -> List[str]:
        """
        Get all case IDs in mapping

        Returns:
            List of case IDs
        """
        return list(self.case_to_laws.keys())

    def has_law(self, law_id: str) -> bool:
        """Check if law exists in mapping"""
        return law_id in self.law_to_cases

    def has_case(self, case_id: str) -> bool:
        """Check if case exists in mapping"""
        return case_id in self.case_to_laws

    def get_statistics(self) -> Dict[str, int]:
        """
        Get mapping statistics

        Returns:
            Dictionary with statistics
        """
        total_chunks = len(self.chunk_to_laws)
        total_cases = len(self.case_to_laws)
        total_laws = len(self.law_to_cases)

        # Average cases per law
        avg_cases_per_law = sum(
            len(data.get('cases', []))
            for data in self.law_to_cases.values()
        ) / total_laws if total_laws > 0 else 0

        return {
            "total_laws": total_laws,
            "total_cases": total_cases,
            "total_chunks": total_chunks,
            "avg_cases_per_law": round(avg_cases_per_law, 2)
        }
