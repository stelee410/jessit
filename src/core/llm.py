"""
LLM接口抽象和实现
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional
from dataclasses import dataclass
import anthropic
import openai
import os


@dataclass
class LLMConfig:
    """LLM配置"""

    api_key: str
    base_url: Optional[str] = None
    model: str = "default"
    temperature: float = 0.7
    max_tokens: int = 4096


class LLMProvider(ABC):
    """LLM提供商抽象基类"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """聊天接口"""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """流式聊天接口"""
        pass

    def _get_temperature(self, temperature: Optional[float]) -> float:
        """获取温度参数"""
        return temperature if temperature is not None else self.config.temperature

    def _get_max_tokens(self, max_tokens: Optional[int]) -> int:
        """获取最大token数"""
        return max_tokens if max_tokens is not None else self.config.max_tokens


class ClaudeProvider(LLMProvider):
    """Claude API实现"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = anthropic.AsyncAnthropic(api_key=config.api_key)
        self.default_model = config.model or "claude-3-5-sonnet-20241022"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """发送聊天请求"""
        try:
            response = await self.client.messages.create(
                model=self.default_model,
                messages=messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature),
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        try:
            async with self.client.messages.stream(
                model=self.default_model,
                messages=messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature),
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise RuntimeError(f"Claude streaming error: {e}")


class OpenAIProvider(LLMProvider):
    """OpenAI API实现"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        kwargs = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = openai.AsyncOpenAI(**kwargs)
        self.default_model = config.model or "gpt-4"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """发送聊天请求"""
        try:
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature),
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.default_model,
                messages=messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature),
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise RuntimeError(f"OpenAI streaming error: {e}")


class OllamaProvider(LLMProvider):
    """Ollama本地模型实现"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"
        self.default_model = config.model or "llama2"

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """发送聊天请求"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.default_model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self._get_temperature(temperature),
                            "num_predict": self._get_max_tokens(max_tokens),
                        },
                    },
                ) as response:
                    data = await response.json()
                    return data.get("message", {}).get("content", "")
        except Exception as e:
            raise RuntimeError(f"Ollama API error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.default_model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": self._get_temperature(temperature),
                            "num_predict": self._get_max_tokens(max_tokens),
                        },
                    },
                ) as response:
                    async for line in response.content:
                        import json
                        if line:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {e}")


def create_llm_provider(provider_type: str, config: LLMConfig) -> LLMProvider:
    """工厂函数：创建LLM提供商"""
    providers = {
        "claude": ClaudeProvider,
        "openai": OpenAIProvider,
        "ollama": OllamaProvider,
    }

    provider_class = providers.get(provider_type.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_type}")

    return provider_class(config)
