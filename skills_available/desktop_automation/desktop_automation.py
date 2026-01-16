"""
桌面自动化技能实现
通过截图和鼠标键盘模拟操作桌面应用程序
"""

import json
import time
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List
from PyQt6.QtWidgets import QApplication

from .window_manager import WindowManager
from .screenshot_service import ScreenshotService
from .mouse_keyboard_controller import MouseKeyboardController

# 配置日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# 全局变量：用于存储聊天窗口引用和LLM提供者（由应用初始化时设置）
_chat_window_ref = None
_llm_provider_ref = None


def set_chat_window(window):
    """设置聊天窗口引用（由应用初始化时调用）"""
    global _chat_window_ref
    _chat_window_ref = window


def get_chat_window():
    """获取聊天窗口引用"""
    return _chat_window_ref


def set_llm_provider(llm_provider):
    """设置LLM提供者引用（由agent初始化时调用）"""
    global _llm_provider_ref
    _llm_provider_ref = llm_provider


def get_llm_provider():
    """获取LLM提供者引用"""
    return _llm_provider_ref


def desktop_automation(
    task_description: str,
    application_name: Optional[str] = None,
    max_steps: int = 10,
    verify_result: bool = False,
    llm_provider=None,
) -> Dict[str, Any]:
    """
    执行桌面自动化任务
    
    Args:
        task_description: 任务描述
        application_name: 目标应用程序名称（可选）
        max_steps: 最大操作步骤数
        verify_result: 是否验证结果
        llm_provider: LLM提供者（可选，如果为None则无法调用LLM）
    
    Returns:
        执行结果字典
    """
    logger.info("=" * 80)
    logger.info(f"开始执行桌面自动化任务: {task_description}")
    if application_name:
        logger.info(f"目标应用程序: {application_name}")
    logger.info(f"最大步骤数: {max_steps}, 验证结果: {verify_result}")
    
    try:
        # 1. 截取桌面（不最小化窗口，保持聊天窗口正常显示）
        logger.info("[步骤 1/6] 截取桌面...")
        screenshot_service = ScreenshotService()
        screenshot_img = screenshot_service.capture_desktop()
        logger.info(f"✓ 桌面截图完成，原始尺寸: {screenshot_img.size}")
        
        # 压缩截图以减少数据量（使用JPEG格式，最大宽度1920px）
        logger.info("正在压缩截图以优化传输速度...")
        screenshot_base64 = screenshot_service.capture_to_base64(
            screenshot_img, 
            format="JPEG", 
            max_width=1920, 
            quality=85
        )
        
        # 2. 获取LLM提供者
        logger.info("[步骤 2/6] 获取LLM提供者...")
        if llm_provider is None:
            llm_provider = get_llm_provider()
            logger.info("从全局引用获取LLM提供者")
        
        if llm_provider is None:
            logger.error("✗ LLM提供者未找到")
            return {
                "success": False,
                "error": "桌面自动化需要LLM支持，但未找到LLM提供者",
            }
        
        logger.info(f"✓ LLM提供者已获取: {type(llm_provider).__name__}")
        
        # 3. 调用LLM分析截图并生成操作步骤
        logger.info("[步骤 3/6] 调用LLM分析截图并生成操作步骤...")
        logger.info("正在压缩截图并发送给LLM（可能需要10-30秒，请稍候）...")
        operation_steps = _analyze_screenshot_with_llm(
            llm_provider,
            task_description,
            screenshot_base64,
            application_name,
            max_steps
        )
        
        if not operation_steps or not operation_steps.get("success"):
            error_msg = operation_steps.get('error', '未知错误') if operation_steps else 'operation_steps为空'
            logger.error(f"✗ LLM分析失败: {error_msg}")
            if operation_steps and 'raw_response' in operation_steps:
                logger.debug(f"LLM原始响应: {operation_steps['raw_response']}")
            return {
                "success": False,
                "error": f"LLM分析失败: {error_msg}",
            }
        
        steps = operation_steps.get("steps", [])
        if not steps:
            logger.error("✗ LLM未返回任何操作步骤")
            return {
                "success": False,
                "error": "LLM未返回任何操作步骤",
            }
        
        logger.info(f"✓ LLM分析完成，生成 {len(steps)} 个操作步骤:")
        for i, step in enumerate(steps, 1):
            step_type = step.get("type", "unknown")
            step_desc = f"  {i}. {step_type}"
            if step_type == "click":
                step_desc += f" at ({step.get('x')}, {step.get('y')})"
            elif step_type == "type":
                text = step.get("text", "")[:30]
                step_desc += f" text: '{text}...'"
            elif step_type == "key":
                step_desc += f" key: {step.get('key')}"
            logger.info(step_desc)
        
        # 4. 执行操作步骤
        logger.info("[步骤 4/6] 执行鼠标键盘操作...")
        controller = MouseKeyboardController(use_direct_input=False, delay=0.5)
        execution_result = controller.execute_steps(steps)
        
        success_steps = execution_result.get('success_steps', 0)
        total_steps = execution_result.get('total_steps', 0)
        logger.info(f"✓ 操作执行完成: {success_steps}/{total_steps} 步骤成功")
        
        # 5. 可选：验证结果
        verification_result = None
        if verify_result:
            logger.info("[步骤 5/6] 验证操作结果...")
            time.sleep(1)  # 等待操作完成
            verification_img = screenshot_service.capture_desktop()
            logger.info("截取验证截图并压缩...")
            verification_base64 = screenshot_service.capture_to_base64(
                verification_img,
                format="JPEG",
                max_width=1920,
                quality=85
            )
            logger.info("发送验证截图给LLM分析...")
            verification_result = _verify_result_with_llm(
                llm_provider,
                task_description,
                verification_base64
            )
            if verification_result:
                success = verification_result.get("success", False)
                message = verification_result.get("message", "")
                logger.info(f"✓ 验证完成: {'成功' if success else '失败'} - {message}")
        else:
            logger.info("[步骤 5/6] 跳过结果验证")
        
        # 6. 清理资源
        screenshot_service.close()
        
        # 7. 返回结果
        final_success = execution_result.get("success", False)
        logger.info("=" * 80)
        logger.info(f"桌面自动化任务完成: {'成功' if final_success else '部分成功'}")
        logger.info(f"执行了 {execution_result.get('success_steps', 0)}/{execution_result.get('total_steps', 0)} 个步骤")
        logger.info("=" * 80)
        
        return {
            "success": final_success,
            "message": f"执行了 {execution_result.get('success_steps', 0)}/{execution_result.get('total_steps', 0)} 个步骤",
            "execution_result": execution_result,
            "verification": verification_result,
            "steps_executed": len(steps),
        }
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"桌面自动化执行失败: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        
        return {
            "success": False,
            "error": f"桌面自动化执行失败: {str(e)}",
        }


def _analyze_screenshot_with_llm(
    llm_provider,
    task_description: str,
    screenshot_base64: str,
    application_name: Optional[str] = None,
    max_steps: int = 10,
) -> Dict[str, Any]:
    """
    使用LLM分析截图并生成操作步骤
    
    Args:
        llm_provider: LLM提供者
        task_description: 任务描述
        screenshot_base64: 截图的base64编码
        application_name: 应用程序名称
        max_steps: 最大步骤数
    
    Returns:
        包含操作步骤的字典
    """
    logger.info("开始调用LLM分析截图...")
    try:
        # 构建提示词
        system_prompt = """你是一个桌面自动化助手。分析用户提供的桌面截图，理解用户的任务需求，然后返回具体的鼠标和键盘操作步骤。

操作步骤必须以JSON格式返回，格式如下：
{
    "steps": [
        {"type": "click", "x": 100, "y": 200, "button": "left"},
        {"type": "type", "text": "hello world"},
        {"type": "key", "key": "enter"},
        {"type": "scroll", "x": 500, "y": 300, "dy": -100}
    ]
}

支持的操作类型：
- click: 点击操作，需要x, y坐标，可选button（left/right/middle），可选clicks（点击次数）
- type: 输入文本，需要text参数
- key: 按键操作，需要key参数（如"enter", "tab", "ctrl+c"等）
- scroll: 滚动操作，需要x, y坐标和dy（垂直滚动距离，正数向下，负数向上）
- drag: 拖拽操作，需要x1, y1（起始）和x2, y2（结束）坐标

请仔细分析截图，确定需要操作的元素位置，然后返回精确的操作步骤。"""

        user_prompt = f"""任务：{task_description}
{f"目标应用程序：{application_name}" if application_name else ""}
最大步骤数：{max_steps}

请分析截图，返回完成此任务所需的操作步骤。"""

        # 构建消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 调用LLM（同步调用，因为我们在同步函数中）
        # 由于可能在已有事件循环的上下文中运行，使用线程来避免冲突
        logger.info(f"正在调用LLM API（发送 {len(messages)} 条消息，1 张图片）...")
        logger.info("提示：LLM处理图片需要一些时间，请耐心等待...")
        
        import time
        start_time = time.time()
        
        response = None
        exception = None
        
        def run_in_thread():
            """在线程中运行异步代码"""
            nonlocal response, exception
            try:
                # 创建新的事件循环（在线程中）
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    response = new_loop.run_until_complete(
                        llm_provider.chat(
                            messages=messages,
                            images=[screenshot_base64],
                            temperature=0.3,  # 降低温度以获得更确定性的操作步骤
                            max_tokens=2000,
                        )
                    )
                finally:
                    new_loop.close()
            except Exception as e:
                exception = e
        
        # 在线程中运行
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()  # 等待线程完成
        
        elapsed_time = time.time() - start_time
        logger.info(f"LLM API调用完成，耗时: {elapsed_time:.1f} 秒")
        
        # 检查是否有异常
        if exception:
            raise exception
        
        logger.info(f"✓ LLM响应接收完成，类型: {type(response).__name__}")
        if isinstance(response, str):
            logger.debug(f"LLM响应长度: {len(response)} 字符")
        
        # 解析响应
        logger.info("解析LLM响应...")
        if isinstance(response, str):
            # 尝试从响应中提取JSON
            json_str = _extract_json_from_response(response)
            if json_str:
                logger.debug(f"提取到JSON字符串，长度: {len(json_str)} 字符")
                try:
                    steps_data = json.loads(json_str)
                    if "steps" in steps_data and isinstance(steps_data["steps"], list):
                        logger.info(f"✓ 成功解析操作步骤: {len(steps_data['steps'])} 个步骤")
                        return {
                            "success": True,
                            "steps": steps_data["steps"],
                        }
                    else:
                        logger.warning("JSON中未找到有效的steps数组")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON解析失败: {e}")
            else:
                logger.warning("无法从响应中提取JSON字符串")
        
        error_response_preview = response[:500] if isinstance(response, str) else str(response)[:500]
        logger.error(f"✗ 无法解析操作步骤。响应预览: {error_response_preview}")
        return {
            "success": False,
            "error": "无法从LLM响应中解析操作步骤",
            "raw_response": response[:500] if isinstance(response, str) else str(response)[:500],
        }
        
    except Exception as e:
        logger.error(f"✗ LLM分析过程中发生异常: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"LLM分析失败: {str(e)}",
        }


def _verify_result_with_llm(
    llm_provider,
    task_description: str,
    screenshot_base64: str,
) -> Dict[str, Any]:
    """
    使用LLM验证操作结果
    
    Args:
        llm_provider: LLM提供者
        task_description: 任务描述
        screenshot_base64: 验证截图的base64编码
    
    Returns:
        验证结果字典
    """
    try:
        system_prompt = """你是一个任务验证助手。分析用户提供的桌面截图，判断任务是否已经成功完成。

请返回JSON格式的验证结果：
{
    "success": true/false,
    "message": "验证结果描述"
}"""

        user_prompt = f"""任务：{task_description}

请分析截图，判断任务是否已经成功完成。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = None
        exception = None
        
        def run_in_thread():
            """在线程中运行异步代码"""
            nonlocal response, exception
            try:
                # 创建新的事件循环（在线程中）
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    response = new_loop.run_until_complete(
                        llm_provider.chat(
                            messages=messages,
                            images=[screenshot_base64],
                            temperature=0.3,
                            max_tokens=500,
                        )
                    )
                finally:
                    new_loop.close()
            except Exception as e:
                exception = e
        
        # 在线程中运行
        thread = threading.Thread(target=run_in_thread)
        thread.start()
        thread.join()  # 等待线程完成
        
        # 检查是否有异常
        if exception:
            raise exception
        
        if isinstance(response, str):
            json_str = _extract_json_from_response(response)
            if json_str:
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        
        return {
            "success": False,
            "message": "无法解析验证结果",
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"验证失败: {str(e)}",
        }


def _extract_json_from_response(response: str) -> Optional[str]:
    """
    从LLM响应中提取JSON字符串
    
    Args:
        response: LLM响应文本
    
    Returns:
        JSON字符串，如果未找到则返回None
    """
    # 尝试查找JSON代码块
    import re
    
    # 查找 ```json ... ``` 代码块
    json_block_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(json_block_pattern, response, re.DOTALL)
    if match:
        return match.group(1)
    
    # 查找 {...} JSON对象
    json_object_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
    match = re.search(json_object_pattern, response, re.DOTALL)
    if match:
        return match.group(0)
    
    return None
