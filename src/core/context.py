"""
对话上下文管理
"""

from typing import List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    """消息数据结构"""

    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConversationContext:
    """对话上下文管理器"""

    def __init__(self, max_history: int = 50):
        self.messages: List[Message] = []
        self.max_history = max_history
        self.metadata: Dict[str, Any] = {}

    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> None:
        """添加消息到上下文"""
        message = Message(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)

        # 限制历史消息数量
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history :]

    def get_messages(self) -> List[Dict[str, str]]:
        """获取消息列表（用于LLM API）"""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def get_last_message(self) -> Message | None:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    def clear(self) -> None:
        """清空上下文"""
        self.messages.clear()
        self.metadata.clear()

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)
