"""
UI工作线程模块
"""

import asyncio
from PyQt6.QtCore import QThread, pyqtSignal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.agent import JessitAgent


class ChatWorker(QThread):
    """聊天工作线程"""

    response_received = pyqtSignal(str)
    stream_chunk = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, agent: "JessitAgent", user_message: str, stream: bool = False):
        """
        初始化聊天工作线程
        
        Args:
            agent: Jessit Agent实例
            user_message: 用户消息
            stream: 是否使用流式响应
        """
        super().__init__()
        self.agent = agent
        self.user_message = user_message
        self.stream = stream

    def run(self) -> None:
        """执行聊天请求"""
        try:
            asyncio.run(self._execute_chat())
        except Exception as e:
            self.error_occurred.emit(str(e))

    async def _execute_chat(self) -> None:
        """执行异步聊天"""
        if self.stream:
            await self._stream_chat()
        else:
            await self._normal_chat()

    async def _stream_chat(self) -> None:
        """流式聊天"""
        full_response = ""
        async for chunk in self.agent.chat(self.user_message, stream=True):
            full_response += chunk
            self.stream_chunk.emit(chunk)
        self.response_received.emit(full_response)

    async def _normal_chat(self) -> None:
        """普通聊天"""
        response = ""
        async for r in self.agent.chat(self.user_message, stream=False):
            response = r
        self.response_received.emit(response)
