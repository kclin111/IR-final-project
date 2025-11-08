"""
LLM generation utilities for creating structured responses
"""
from typing import Dict, Any, List, Optional
import json
import re
from openai import OpenAI
from app.config import settings


class LLMGenerator:
    """
    LLM-based response generator
    Generates responses with proper citations
    """

    def __init__(self, model_name: str = None, temperature: float = None):
        """
        Initialize LLM generator

        Args:
            model_name: OpenAI model name
            temperature: Sampling temperature
        """
        self.model_name = model_name or settings.LLM_MODEL
        self.temperature = temperature or settings.LLM_TEMPERATURE
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def generate_response(
        self,
        system_prompt: str,
        context: str,
        query_text: str
    ) -> str:
        """
        Generate response from context

        Args:
            system_prompt: System instruction
            context: Assembled context
            query_text: Original query

        Returns:
            Generated response text
        """
        user_prompt = f"{context}\n\n請根據以上法條與判例,回答以下問題:\n{query_text}"

        try:
            # Build API call parameters
            api_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }

            # Only add temperature for models that support it (not gpt-5-nano)
            if "gpt-5" not in self.model_name:
                api_params["temperature"] = self.temperature

            # Only add max_completion_tokens for models that support it (not gpt-5-nano)
            if "gpt-5" not in self.model_name:
                api_params["max_completion_tokens"] = settings.LLM_MAX_TOKENS

            response = self.client.chat.completions.create(**api_params)

            # Debug: Print full response
            print(f"\n[LLM DEBUG] Full response object:")
            print(f"  Model: {response.model}")
            print(f"  Finish reason: {response.choices[0].finish_reason}")
            print(f"  Content type: {type(response.choices[0].message.content)}")
            print(f"  Content value: '{response.choices[0].message.content}'")
            print(f"  Content length: {len(response.choices[0].message.content) if response.choices[0].message.content else 0}")

            content = response.choices[0].message.content
            if content is None:
                print("[LLM DEBUG] WARNING: content is None!")
                return ""

            return content

        except Exception as e:
            print(f"Error generating LLM response: {e}")
            return f"抱歉,生成回應時發生錯誤: {str(e)}"

    def generate_structured_response(
        self,
        system_prompt: str,
        context: str,
        query_text: str,
        response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate structured JSON response

        Args:
            system_prompt: System instruction
            context: Assembled context
            query_text: Original query
            response_schema: JSON schema for response

        Returns:
            Structured response dictionary
        """
        user_prompt = f"""{context}

請根據以上法條與判例,以 JSON 格式回答以下問題:
{query_text}

請按照以下格式回應:
{json.dumps(response_schema, ensure_ascii=False, indent=2)}
"""

        try:
            # Build API call parameters
            api_params = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_completion_tokens": settings.LLM_MAX_TOKENS,
                "response_format": {"type": "json_object"}
            }

            # Only add temperature for models that support it (not gpt-5-nano)
            if "gpt-5" not in self.model_name:
                api_params["temperature"] = self.temperature

            response = self.client.chat.completions.create(**api_params)

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            print(f"Error generating structured response: {e}")
            return {
                "answer": f"抱歉,生成回應時發生錯誤: {str(e)}",
                "citations": [],
                "warnings": [str(e)]
            }

    def extract_law_citations(self, text: str) -> List[str]:
        """
        Extract law citations from text

        Args:
            text: Generated text

        Returns:
            List of cited law IDs
        """
        # Pattern: 道路交通管理處罰條例第XX條
        pattern = r'道路交通管理處罰條例第\s*\d+(?:-\d+)?\s*條'
        matches = re.findall(pattern, text)

        # Normalize spacing
        citations = [re.sub(r'\s+', ' ', match) for match in matches]

        return list(set(citations))  # Deduplicate

    def extract_case_citations(self, text: str) -> List[str]:
        """
        Extract case citations from text

        Args:
            text: Generated text

        Returns:
            List of cited case IDs
        """
        # Pattern: [CASE_ID] or 判決 [CASE_ID]
        pattern = r'\[([A-Z]+,\d+,[^,]+,\d+,\d+,\d+)\]'
        matches = re.findall(pattern, text)

        return list(set(matches))  # Deduplicate
