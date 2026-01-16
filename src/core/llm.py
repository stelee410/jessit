"""
LLM接口抽象和实现
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator, Optional, Union
from dataclasses import dataclass
import anthropic
import openai
import os


@dataclass
class LLMConfig:
    """LLM配置"""

    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096


class LLMProvider(ABC):
    """LLM提供商抽象基类"""

    def __init__(self, config: LLMConfig):
        self.config = config

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """
        聊天接口
        
        Args:
            messages: 消息列表，支持文本和图片混合内容
            temperature: 温度参数
            max_tokens: 最大token数
            tools: 工具定义列表
            images: base64编码的图片列表（可选，用于视觉输入）
        """
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
        kwargs = {"api_key": config.api_key}
        if config.base_url:
            kwargs["base_url"] = config.base_url
        self.client = anthropic.AsyncAnthropic(**kwargs)
        self.default_model = config.model or "claude-3-5-sonnet-20241022"

    def _diagnostics(self) -> str:
        """构造诊断信息（不包含敏感信息）"""
        base_url = self.config.base_url or "default"
        model = self.default_model or "unknown"
        return f"model={model}, base_url={base_url}"

    def _process_messages(self, messages: List[Dict[str, Any]], images: Optional[List[str]] = None) -> tuple[str, List[Dict[str, Any]]]:
        """处理消息列表，提取system消息，支持图片输入
        返回: (system_message, filtered_messages)
        """
        system_messages = []
        filtered_messages = []
        
        for msg in messages:
            if msg.get("role") == "system":
                system_messages.append(msg.get("content", ""))
            else:
                # 只保留user和assistant角色的消息
                if msg.get("role") in ("user", "assistant"):
                    # 如果是user消息且有图片，构建包含图片的content
                    if msg.get("role") == "user" and images:
                        content = []
                        # 添加文本内容（如果有）
                        msg_content = msg.get("content", "")
                        if isinstance(msg_content, str) and msg_content:
                            content.append({"type": "text", "text": msg_content})
                        elif isinstance(msg_content, list):
                            # 如果content已经是列表，合并进去
                            content.extend(msg_content)
                        # 添加图片
                        for img_base64 in images:
                            content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": img_base64
                                }
                            })
                        msg_copy = msg.copy()
                        msg_copy["content"] = content
                        filtered_messages.append(msg_copy)
                    else:
                        filtered_messages.append(msg)
        
        # 合并所有system消息
        system_content = "\n".join(system_messages) if system_messages else ""
        
        return system_content, filtered_messages

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """发送聊天请求"""
        try:
            system_content, filtered_messages = self._process_messages(messages, images)

            kwargs = {
                "model": self.default_model,
                "messages": filtered_messages,
                "max_tokens": self._get_max_tokens(max_tokens),
                "temperature": self._get_temperature(temperature),
            }

            if system_content:
                kwargs["system"] = system_content

            if tools:
                kwargs["tools"] = tools

            response = await self.client.messages.create(**kwargs)

            # 检查是否有 tool_use 响应
            tool_use_blocks = [block for block in response.content if block.type == "tool_use"]
            if tool_use_blocks:
                # 返回工具调用信息
                tool_calls = []
                for block in tool_use_blocks:
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })
                return {
                    "type": "tool_use",
                    "tool_calls": tool_calls,
                }

            # 返回文本响应
            return response.content[0].text
        except Exception as e:
            print(f"Claude API error: {e}; {self._diagnostics()}")
            raise RuntimeError(f"Claude API error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        try:
            system_content, filtered_messages = self._process_messages(messages, images)
            
            kwargs = {
                "model": self.default_model,
                "messages": filtered_messages,
                "max_tokens": self._get_max_tokens(max_tokens),
                "temperature": self._get_temperature(temperature),
            }
            
            if system_content:
                kwargs["system"] = system_content
            
            async with self.client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            print(f"Claude streaming error: {e}; {self._diagnostics()}")
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
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """发送聊天请求"""
        try:
            # OpenAI 的视觉模型需要特殊处理消息格式
            processed_messages = messages
            if images:
                # 对于 OpenAI，图片需要作为 base64 数据 URI 嵌入到消息中
                # 这里简化处理，只支持文本消息
                pass
            
            response = await self.client.chat.completions.create(
                model=self.default_model,
                messages=processed_messages,
                max_tokens=self._get_max_tokens(max_tokens),
                temperature=self._get_temperature(temperature),
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {e}")

    async def stream_chat(
        self,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        try:
            processed_messages = messages
            if images:
                # OpenAI 视觉模型处理（简化）
                pass
            
            stream = await self.client.chat.completions.create(
                model=self.default_model,
                messages=processed_messages,
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
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        images: Optional[List[str]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """发送聊天请求"""
        import aiohttp

        try:
            # Ollama 可能不支持视觉输入，这里简化处理
            processed_messages = messages
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.default_model,
                        "messages": processed_messages,
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
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        import aiohttp

        try:
            processed_messages = messages
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.default_model,
                        "messages": processed_messages,
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
