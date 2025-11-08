"""
Context assembly utilities for LLM prompt construction
Builds structured context with law-case relationships
"""
from typing import List, Dict, Any, Optional


class ContextBuilder:
    """
    Assembles context from laws and cases for LLM generation
    Uses relational structure to preserve law-case connections
    """

    def __init__(self, max_context_tokens: int = 10000):
        """
        Initialize context builder

        Args:
            max_context_tokens: Maximum context size in tokens (approximate)
        """
        self.max_context_tokens = max_context_tokens

    def build_context(
        self,
        laws: Dict[str, Dict[str, Any]],
        cases: Dict[str, Dict[str, Any]],
        query_text: str,
    ) -> str:
        """
        Build complete context for LLM with relational structure

        Args:
            laws: Dictionary of law_id -> law data
            cases: Dictionary of case_id -> case data
            query_text: Original query

        Returns:
            Formatted context string
        """
        context_parts = []

        # Add query
        context_parts.append(f"# 使用者查詢\n{query_text}\n")

        # Separate laws by source
        direct_laws = {k: v for k, v in laws.items() if 'direct_retrieval' in v['sources']}
        expanded_laws = {k: v for k, v in laws.items() if 'direct_retrieval' not in v['sources']}

        # Separate cases by source
        direct_cases = {k: v for k, v in cases.items() if 'direct_retrieval' in v['sources']}
        expanded_cases = {k: v for k, v in cases.items() if 'direct_retrieval' not in v['sources']}

        # Build law groups (relational structure)
        context_parts.append("\n# 相關法條與判例\n")

        # Group 1: Directly retrieved laws with their expanded cases
        if direct_laws:
            context_parts.append("\n## 核心相關法條 (直接檢索)\n")
            for law_id, law_data in direct_laws.items():
                law_section = self._format_law_with_cases(law_data, cases)
                context_parts.append(law_section)

        # Group 2: Expanded laws from cases
        if expanded_laws:
            context_parts.append("\n## 擴展相關法條 (來自判例引用)\n")
            for law_id, law_data in expanded_laws.items():
                law_section = self._format_law_simple(law_data)
                context_parts.append(law_section)

        # Group 3: Directly retrieved cases (if not already shown under laws)
        context_parts.append("\n\n# 相關判決案例\n")

        if direct_cases:
            context_parts.append("\n## 核心相關判例 (直接檢索)\n")
            for case_id, case_data in direct_cases.items():
                case_section = self._format_case_complete(case_data)
                context_parts.append(case_section)

        # Group 4: Expanded cases from laws (if not already shown)
        shown_case_ids = set(direct_cases.keys())
        remaining_expanded = {k: v for k, v in expanded_cases.items() if k not in shown_case_ids}

        if remaining_expanded:
            context_parts.append("\n## 擴展相關判例 (來自法條關聯)\n")
            for case_id, case_data in remaining_expanded.items():
                case_section = self._format_case_complete(case_data)
                context_parts.append(case_section)

        full_context = "\n".join(context_parts)

        # Truncate if needed
        if len(full_context) > self.max_context_tokens * 4:  # Rough char to token ratio
            full_context = self._truncate_context(full_context)

        return full_context

    def _format_law_with_cases(
        self,
        law_data: Dict[str, Any],
        all_cases: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Format law with associated cases in relational structure

        Args:
            law_data: Law information
            all_cases: All available cases

        Returns:
            Formatted law section with cases
        """
        sections = []

        # Law header
        metadata = law_data['metadata']
        score_str = f" (相似度: {law_data['score']:.3f})" if law_data['score'] else ""

        sections.append(f"\n### {metadata['cited_law']}{score_str}")
        sections.append(f"**{metadata['章名']}**")
        sections.append(f"\n{metadata['條文內容']}\n")

        return "\n".join(sections)

    def _format_law_simple(self, law_data: Dict[str, Any]) -> str:
        """
        Format law without associated cases (for expanded laws)

        Args:
            law_data: Law information

        Returns:
            Formatted law section
        """
        metadata = law_data['metadata']
        via_cases = law_data.get('via_cases', [])
        via_str = f" (來自判例: {', '.join(via_cases[:2])}{'...' if len(via_cases) > 2 else ''})" if via_cases else ""

        sections = [
            f"\n### {metadata['cited_law']}{via_str}",
            f"**{metadata['章名']}**",
            f"\n{metadata['條文內容']}\n"
        ]

        return "\n".join(sections)

    def _format_case_complete(self, case_data: Dict[str, Any]) -> str:
        """
        Format complete case with all chunks

        Args:
            case_data: Complete case information

        Returns:
            Formatted case section
        """
        sections = []

        # Case header
        metadata = case_data['metadata']
        score_str = f" (相似度: {case_data['score']:.3f})" if case_data['score'] else ""
        via_laws = case_data.get('via_laws', [])
        via_str = f" (來自法條: {', '.join(via_laws[:2])})" if via_laws and 'direct_retrieval' not in case_data['sources'] else ""

        sections.append(f"\n### 判決 [{case_data['case_id']}]{score_str}{via_str}")
        sections.append(f"**{metadata['JTITLE']}** - {metadata['court']}")
        sections.append(f"判決日期: {metadata['JDATE']}")

        if metadata.get('cited_traffic_laws'):
            laws_str = ", ".join(metadata['cited_traffic_laws'])
            sections.append(f"引用法條: {laws_str}")

        sections.append("")  # Blank line

        # Add chunks grouped by type
        chunks_by_type = {}
        for chunk in case_data['chunks']:
            chunk_type = chunk.get('chunk_type', 'unknown')
            if chunk_type not in chunks_by_type:
                chunks_by_type[chunk_type] = []
            chunks_by_type[chunk_type].append(chunk['text'])

        # Prioritize important chunk types
        priority_types = ['事實', '理由要領', '本院之判斷', '理由', '主文']

        for chunk_type in priority_types:
            if chunk_type in chunks_by_type:
                sections.append(f"**{chunk_type}:**")
                for text in chunks_by_type[chunk_type]:
                    sections.append(text)
                sections.append("")

        # Add remaining chunk types
        for chunk_type, texts in chunks_by_type.items():
            if chunk_type not in priority_types:
                sections.append(f"**{chunk_type}:**")
                for text in texts:
                    sections.append(text)
                sections.append("")

        return "\n".join(sections)

    def _truncate_context(self, context: str) -> str:
        """
        Truncate context to fit within token limits
        Prioritizes keeping directly retrieved content

        Args:
            context: Full context string

        Returns:
            Truncated context
        """
        # Simple character-based truncation
        # More sophisticated approach would use tiktoken
        max_chars = self.max_context_tokens * 4

        if len(context) <= max_chars:
            return context

        # Truncate and add warning
        truncated = context[:max_chars]
        truncated += "\n\n[注意: 內容已截斷以符合長度限制]"

        return truncated

    def build_system_prompt(self) -> str:
        """
        Build system prompt for LLM

        Returns:
            System prompt string
        """
        return """你是一個專業的交通法規與判例檢索助理。

你的任務是根據提供的法條與判例,回答使用者關於交通法規的問題。

請注意:
1. 僅基於提供的法條與判例回答,不要編造內容
2. 引用時請明確標註法條編號或判決編號
3. 若提供的資訊不足以回答問題,請誠實說明
4. 說明法律適用時,要考慮具體情境與構成要件
5. 提供的建議僅供參考,不構成正式法律意見

請以清晰、結構化的方式回答問題。"""
