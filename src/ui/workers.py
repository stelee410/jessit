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
    progress_updated = pyqtSignal(dict)  # 进度更新信号
    confirmation_requested = pyqtSignal(str, str, object)  # 请求确认信号 (tool_name, description, callback)

    def __init__(self, agent: "JessitAgent", user_message: str, stream: bool = False, chat_window=None):
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
        self.chat_window = chat_window
        self.progress_info = {
            "analysis": "",
            "plan": [],
            "execution_steps": [],
            "final_result": "",
        }

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
        """流式聊天（使用工具调用，失去实时流式效果但支持工具）"""
        # 定义进度回调函数
        def progress_callback(progress_data: dict):
            """进度回调函数，在主线程中发射信号"""
            # 更新本地进度信息
            if "progress_info" in progress_data:
                self.progress_info = progress_data["progress_info"]
            elif "analysis" in progress_data:
                self.progress_info["analysis"] = progress_data["analysis"]
            elif "plan" in progress_data:
                self.progress_info["plan"] = progress_data["plan"]
            elif "step" in progress_data:
                if progress_data["stage"] == "step_complete":
                    self.progress_info["execution_steps"].append(progress_data["step"])
            elif "final_result" in progress_data:
                self.progress_info["final_result"] = progress_data["final_result"]
            
            # 发射进度更新信号
            self.progress_updated.emit(progress_data)
        
        # 由于工具调用需要完整响应，这里使用 chat_with_tools
        response = await self.agent.chat_with_tools(
            self.user_message,
            progress_callback=progress_callback
        )

        # 模拟流式输出（一次性发送完整响应）
        full_response = response
        # 可以将响应分块发送来模拟流式效果
        for chunk in self._chunk_text(response, chunk_size=2):
            self.stream_chunk.emit(chunk)
            # 短暂延迟模拟流式效果
            import asyncio
            await asyncio.sleep(0.01)

        self.response_received.emit(full_response)

    def _chunk_text(self, text: str, chunk_size: int = 2) -> list:
        """将文本分块用于模拟流式输出"""
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    async def _normal_chat(self) -> None:
        """普通聊天（带工具调用）"""
        # 定义进度回调函数
        def progress_callback(progress_data: dict):
            """进度回调函数，在主线程中发射信号"""
            # 更新本地进度信息
            if "progress_info" in progress_data:
                self.progress_info = progress_data["progress_info"]
            elif "analysis" in progress_data:
                self.progress_info["analysis"] = progress_data["analysis"]
            elif "plan" in progress_data:
                self.progress_info["plan"] = progress_data["plan"]
            elif "step" in progress_data:
                if progress_data["stage"] == "step_complete":
                    self.progress_info["execution_steps"].append(progress_data["step"])
            elif "final_result" in progress_data:
                self.progress_info["final_result"] = progress_data["final_result"]
            
            # 发射进度更新信号
            self.progress_updated.emit(progress_data)
        
        # 使用 chat_with_tools 支持工具调用
        response = await self.agent.chat_with_tools(
            self.user_message,
            progress_callback=progress_callback
        )
        self.response_received.emit(response)
