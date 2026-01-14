"""
Jessit Agent主控模块
"""

import asyncio
from typing import Dict, Any, Optional
from .llm import LLMProvider, LLMConfig, create_llm_provider
from .context import ConversationContext
from .skill_manager import SkillManager


class JessitAgent:
    """Jessit Agent主控"""

    def __init__(
        self,
        llm_config: LLMConfig,
        provider_type: str = "claude",
        skills_dir: str = "skills",
    ):
        self.llm: LLMProvider = create_llm_provider(provider_type, llm_config)
        self.context: ConversationContext = ConversationContext()
        self.skill_manager: SkillManager = SkillManager(skills_dir)
        self._initialize_system_prompt()

    def _initialize_system_prompt(self) -> None:
        """初始化系统提示"""
        self.system_prompt = """你是Jessit，一个运行在Windows系统上的AI桌面助手。

你的能力包括：
1. 执行PowerShell命令
2. 操作本地文件系统
3. 处理Excel文件
4. 通过Chrome扩展抓取网页数据
5. 控制鼠标和键盘（在必要时）
6. 调用各种预定义的skills

请使用自然语言与用户交流，根据用户的需求选择最合适的方式完成任务。
当需要执行危险操作时（如删除文件），请先向用户确认。"""

    async def chat(
        self, user_message: str, stream: bool = False
    ) -> str:
        """与Agent对话"""
        # 添加用户消息到上下文
        self.context.add_message("user", user_message)

        # 构建消息列表
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context.get_messages())

        try:
            if stream:
                # 流式响应
                response_content = ""
                async for chunk in self.llm.stream_chat(messages):
                    response_content += chunk
                    yield chunk

                # 添加助手响应到上下文
                self.context.add_message("assistant", response_content)
            else:
                # 非流式响应
                response_content = await self.llm.chat(messages)
                self.context.add_message("assistant", response_content)
                yield response_content

        except Exception as e:
            error_message = f"发生错误: {str(e)}"
            self.context.add_message("assistant", error_message)
            yield error_message

    async def chat_with_tools(
        self,
        user_message: str,
        available_tools: Optional[Dict[str, Any]] = None,
    ) -> str:
        """带工具调用的对话"""
        # 添加用户消息到上下文
        self.context.add_message("user", user_message)

        # 构建消息列表，包含可用的tools
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context.get_messages())

        # 添加可用工具信息
        if available_tools:
            tools_info = "\n\n可用工具:\n"
            for tool_name, tool_desc in available_tools.items():
                tools_info += f"- {tool_name}: {tool_desc}\n"
            messages[-1]["content"] += tools_info

        try:
            response = await self.llm.chat(messages)
            self.context.add_message("assistant", response)
            return response

        except Exception as e:
            error_message = f"发生错误: {str(e)}"
            self.context.add_message("assistant", error_message)
            return error_message

    def clear_context(self) -> None:
        """清空对话上下文"""
        self.context.clear()

    def get_context_messages(self) -> list:
        """获取当前对话历史"""
        return self.context.get_messages()

    def reload_skills(self) -> None:
        """重新加载skills"""
        self.skill_manager.reload()
