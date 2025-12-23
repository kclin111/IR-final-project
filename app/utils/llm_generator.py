"""
LLM generation utilities for creating structured responses
"""
from typing import Dict, Any, List, Optional
import json
import re
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
            model_name: Model name (OpenAI or HuggingFace)
            temperature: Sampling temperature
        """
        self.model_name = model_name or settings.LLM_MODEL
        self.temperature = temperature or settings.LLM_TEMPERATURE
        self.provider = settings.LLM_PROVIDER
        
        if self.provider == "huggingface":
            self._init_huggingface()
        else:
            self._init_openai()
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        from openai import OpenAI
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _init_huggingface(self):
        """Initialize HuggingFace model"""
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
        
        print(f"Loading HuggingFace model: {self.model_name}...")
        
        # Force CPU to avoid GPU memory issues
        self.device = "cpu"
        
        print(f"Using device: {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True
        )
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float32,  # Use float32 for CPU
            device_map=None,  # Disable auto device mapping
            trust_remote_code=True
        ).to(self.device)  # Explicitly move to CPU
        
        print(f"Model loaded successfully!")

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
        if self.provider == "huggingface":
            return self._generate_huggingface(system_prompt, context, query_text)
        else:
            return self._generate_openai(system_prompt, context, query_text)
    
    def _generate_huggingface(
        self,
        system_prompt: str,
        context: str,
        query_text: str
    ) -> str:
        """Generate response using HuggingFace model"""
        user_prompt = f"{context}\n\n請根據以上法條與判例,回答以下問題:\n{query_text}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            # Apply chat template
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=settings.LLM_MAX_TOKENS,
                temperature=self.temperature if self.temperature > 0 else None,
                do_sample=self.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            # Remove input tokens from output
            generated_ids = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return response.strip()
            
        except Exception as e:
            print(f"Error generating HuggingFace response: {e}")
            return f"抱歉,生成回應時發生錯誤: {str(e)}"
    
    def _generate_openai(
        self,
        system_prompt: str,
        context: str,
        query_text: str
    ) -> str:
        """Generate response using OpenAI API"""
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
        schema_str = json.dumps(response_schema, ensure_ascii=False, indent=2)
        user_prompt = f"""{context}

請根據以上法條與判例,以 JSON 格式回答以下問題:
{query_text}

請按照以下格式回應:
{schema_str}
"""

        if self.provider == "huggingface":
            return self._generate_structured_huggingface(system_prompt, user_prompt, response_schema)
        else:
            return self._generate_structured_openai(system_prompt, user_prompt)
    
    def _generate_structured_huggingface(
        self,
        system_prompt: str,
        user_prompt: str,
        response_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate structured JSON response using HuggingFace"""
        messages = [
            {"role": "system", "content": system_prompt + "\n請務必以有效的 JSON 格式回應。"},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=settings.LLM_MAX_TOKENS,
                temperature=self.temperature if self.temperature > 0 else None,
                do_sample=self.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id
            )
            
            generated_ids = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {
                    "answer": response.strip(),
                    "citations": [],
                    "warnings": ["無法解析為 JSON 格式"]
                }
                
        except json.JSONDecodeError as e:
            return {
                "answer": response.strip() if 'response' in locals() else "",
                "citations": [],
                "warnings": [f"JSON 解析錯誤: {str(e)}"]
            }
        except Exception as e:
            print(f"Error generating structured response: {e}")
            return {
                "answer": f"抱歉,生成回應時發生錯誤: {str(e)}",
                "citations": [],
                "warnings": [str(e)]
            }
    
    def _generate_structured_openai(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Dict[str, Any]:
        """Generate structured JSON response using OpenAI"""
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
