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

        # 构建消息列表
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context.get_messages())

        # 获取可用的 skills
        tools = self.skill_manager.get_skills_for_llm()

        try:
            # 第一步：调用 LLM
            response = await self.llm.chat(messages, tools=tools)

            # 处理工具调用响应
            max_iterations = 10  # 防止无限循环
            iteration = 0

            while isinstance(response, dict) and response.get("type") == "tool_use" and iteration < max_iterations:
                iteration += 1
                tool_calls = response["tool_calls"]

                # 执行每个工具调用
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["input"]

                    # 添加工具调用消息到上下文
                    messages.append({
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": tool_call["id"],
                                "name": tool_name,
                                "input": tool_args,
                            }
                        ],
                    })

                    # 执行工具
                    result = self.skill_manager.execute_skill(tool_name, tool_args)

                    # 添加工具结果消息到上下文
                    messages.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_call["id"],
                                "content": str(result),
                            }
                        ],
                    })

                    tool_results.append(result)

                # 再次调用 LLM 获取最终响应
                response = await self.llm.chat(messages, tools=tools)

            # 如果是文本响应，添加到上下文
            if isinstance(response, str):
                self.context.add_message("assistant", response)
                return response
            else:
                # 如果仍然是工具调用（超过最大迭代次数），返回错误
                return "错误：工具调用超过最大迭代次数"

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
