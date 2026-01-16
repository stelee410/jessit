"""
Jessit Agent主控模块
"""

import asyncio
from typing import Dict, Any, Optional, Callable
from .llm import LLMProvider, LLMConfig, create_llm_provider
from .context import ConversationContext
from .skill_manager import SkillManager
from .prompts import build_system_prompt
from .safety import is_dangerous_operation


class JessitAgent:
    """Jessit Agent主控"""

    def __init__(
        self,
        llm_config: LLMConfig,
        provider_type: str = "claude",
        skills_dir: str = "skills",
        confirmation_callback: Optional[Callable[[str, str], bool]] = None,
        experience_file: Optional[str] = None,
    ):
        self.llm: LLMProvider = create_llm_provider(provider_type, llm_config)
        self.context: ConversationContext = ConversationContext()
        self.skill_manager: SkillManager = SkillManager(skills_dir)
        self.confirmation_callback: Optional[Callable[[str, str], bool]] = confirmation_callback
        self.system_prompt = build_system_prompt(experience_file)

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
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        """带工具调用的对话"""
        # 添加用户消息到上下文
        self.context.add_message("user", user_message)

        # 构建消息列表
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context.get_messages())

        # 获取可用的 skills
        tools = self.skill_manager.get_skills_for_llm()

        # 初始化进度信息
        progress_info = {
            "analysis": "",
            "plan": [],
            "execution_steps": [],
            "final_result": "",
        }

        try:
            # 第一步：调用 LLM
            if progress_callback:
                progress_callback({"stage": "analyzing", "message": "正在分析任务..."})
            
            response = await self.llm.chat(messages, tools=tools)

            # 如果第一次响应是文本，可能是分析或计划
            if isinstance(response, str):
                progress_info["analysis"] = response
                if progress_callback:
                    progress_callback({
                        "stage": "analysis_complete",
                        "analysis": response,
                    })
            elif isinstance(response, dict) and response.get("type") == "tool_use":
                # 如果第一次响应就是工具调用，记录为分析信息
                tool_calls = response.get("tool_calls", [])
                analysis_text = f"分析完成，将执行以下操作：\n"
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name", "未知工具")
                    analysis_text += f"- 调用工具: {tool_name}\n"
                progress_info["analysis"] = analysis_text
                if progress_callback:
                    progress_callback({
                        "stage": "analysis_complete",
                        "analysis": analysis_text,
                    })

            # 处理工具调用响应
            max_iterations = 10  # 防止无限循环
            iteration = 0

            while isinstance(response, dict) and response.get("type") == "tool_use" and iteration < max_iterations:
                iteration += 1
                tool_calls = response["tool_calls"]

                # 记录计划（工具调用序列）
                step_plan = []
                for tool_call in tool_calls:
                    step_plan.append({
                        "tool_name": tool_call["name"],
                        "tool_args": tool_call["input"],
                    })
                
                if not progress_info["plan"]:
                    progress_info["plan"] = step_plan
                    if progress_callback:
                        progress_callback({
                            "stage": "planning",
                            "plan": step_plan,
                        })

                # 执行每个工具调用
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["input"]

                    # 检测危险操作
                    is_dangerous, danger_description = is_dangerous_operation(tool_name, tool_args)
                    if is_dangerous:
                        # 如果检测到危险操作，先请求用户确认
                        if self.confirmation_callback:
                            # 构建确认消息
                            confirm_message = f"检测到危险操作：{danger_description}\n\n是否确认执行？"
                            # 调用确认回调（这是同步调用，会在UI线程中阻塞等待用户响应）
                            # 注意：由于这是在异步函数中，我们需要使用 asyncio.to_thread 来在主线程中执行
                            # 但实际上，确认回调应该已经在主线程中执行，这里我们直接调用
                            confirmed = self.confirmation_callback(tool_name, danger_description)
                            if not confirmed:
                                # 用户取消，返回取消消息
                                result = {
                                    "success": False,
                                    "error": "用户取消了危险操作",
                                    "tool_name": tool_name,
                                    "tool_args": tool_args,
                                }
                                # 记录执行步骤（取消状态）
                                execution_step = {
                                    "tool_name": tool_name,
                                    "tool_args": tool_args,
                                    "result": result,
                                    "status": "cancelled",
                                }
                                progress_info["execution_steps"].append(execution_step)
                                
                                if progress_callback:
                                    progress_callback({
                                        "stage": "step_complete",
                                        "step": execution_step,
                                    })
                                
                                # 添加工具结果消息到上下文（取消状态）
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
                                continue

                    # 报告执行步骤
                    if progress_callback:
                        progress_callback({
                            "stage": "executing",
                            "step": {
                                "tool_name": tool_name,
                                "tool_args": tool_args,
                                "status": "running",
                            },
                        })

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

                    # 记录执行步骤和结果
                    execution_step = {
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result,
                        "status": "completed" if result.get("success", True) else "failed",
                    }
                    progress_info["execution_steps"].append(execution_step)

                    # 报告执行结果
                    if progress_callback:
                        progress_callback({
                            "stage": "step_complete",
                            "step": execution_step,
                        })

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
                if progress_callback:
                    progress_callback({"stage": "processing_results", "message": "正在处理结果..."})
                
                response = await self.llm.chat(messages, tools=tools)

            # 如果是文本响应，添加到上下文
            if isinstance(response, str):
                progress_info["final_result"] = response
                if progress_callback:
                    progress_callback({
                        "stage": "complete",
                        "final_result": response,
                        "progress_info": progress_info,
                    })
                self.context.add_message("assistant", response)
                return response
            else:
                # 如果仍然是工具调用（超过最大迭代次数），返回错误
                error_msg = "错误：工具调用超过最大迭代次数"
                progress_info["final_result"] = error_msg
                if progress_callback:
                    progress_callback({
                        "stage": "error",
                        "error": error_msg,
                        "progress_info": progress_info,
                    })
                return error_msg

        except Exception as e:
            error_message = f"发生错误: {str(e)}"
            progress_info["final_result"] = error_message
            if progress_callback:
                progress_callback({
                    "stage": "error",
                    "error": error_message,
                    "progress_info": progress_info,
                })
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
