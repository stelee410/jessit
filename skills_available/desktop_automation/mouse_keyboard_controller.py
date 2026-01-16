"""
鼠标键盘控制器 - 用于模拟鼠标和键盘操作
"""

import time
import logging
import pyautogui
import pydirectinput
from typing import List, Dict, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)


class MouseKeyboardController:
    """鼠标键盘控制器"""

    def __init__(self, use_direct_input: bool = False, delay: float = 0.5):
        """
        初始化控制器
        
        Args:
            use_direct_input: 是否使用pydirectinput（更底层，兼容性更好）
            delay: 操作之间的延迟（秒）
        """
        self.use_direct_input = use_direct_input
        self.delay = delay
        
        # 设置pyautogui的安全设置
        pyautogui.FAILSAFE = True  # 鼠标移到屏幕角落会触发异常
        pyautogui.PAUSE = delay  # 操作之间的默认延迟

    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个操作步骤
        
        Args:
            step: 操作步骤字典，格式：
                {
                    "type": "click" | "type" | "key" | "scroll" | "drag",
                    "x": int,  # 坐标（用于click, drag）
                    "y": int,  # 坐标（用于click, drag）
                    "text": str,  # 文本（用于type）
                    "key": str,  # 按键（用于key）
                    "clicks": int,  # 点击次数（用于click，默认1）
                    "button": str,  # 鼠标按钮（用于click，默认"left"）
                    "dx": int,  # 滚动距离（用于scroll）
                    "dy": int,  # 滚动距离（用于scroll）
                    "duration": float,  # 拖拽持续时间（用于drag）
                }
        
        Returns:
            执行结果字典
        """
        step_type = step.get("type")
        
        try:
            logger.debug(f"执行操作步骤: {step_type} - {step}")
            
            if step_type == "click":
                return self._execute_click(step)
            elif step_type == "type":
                return self._execute_type(step)
            elif step_type == "key":
                return self._execute_key(step)
            elif step_type == "scroll":
                return self._execute_scroll(step)
            elif step_type == "drag":
                return self._execute_drag(step)
            else:
                logger.warning(f"未知的操作类型: {step_type}")
                return {
                    "success": False,
                    "error": f"未知的操作类型: {step_type}"
                }
        except Exception as e:
            logger.error(f"执行操作步骤失败: {step_type} - {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": f"执行操作失败: {str(e)}"
            }

    def _execute_click(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行点击操作"""
        x = step.get("x")
        y = step.get("y")
        clicks = step.get("clicks", 1)
        button = step.get("button", "left")
        
        if x is None or y is None:
            logger.error(f"点击操作缺少坐标: x={x}, y={y}")
            return {"success": False, "error": "点击操作需要x和y坐标"}
        
        logger.info(f"  点击 ({x}, {y}), 按钮: {button}, 次数: {clicks}")
        
        if self.use_direct_input:
            pydirectinput.click(x, y, clicks=clicks, button=button)
        else:
            pyautogui.click(x, y, clicks=clicks, button=button)
        
        time.sleep(self.delay)
        return {"success": True, "action": f"点击 ({x}, {y})"}

    def _execute_type(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行输入文本操作"""
        text = step.get("text", "")
        interval = step.get("interval", 0.05)  # 字符输入间隔
        
        if not text:
            logger.error("输入操作缺少text参数")
            return {"success": False, "error": "输入操作需要text参数"}
        
        text_preview = text[:50] + "..." if len(text) > 50 else text
        logger.info(f"  输入文本: '{text_preview}'")
        
        if self.use_direct_input:
            pydirectinput.write(text, interval=interval)
        else:
            pyautogui.write(text, interval=interval)
        
        time.sleep(self.delay)
        return {"success": True, "action": f"输入文本: {text[:20]}..."}

    def _execute_key(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行按键操作"""
        key = step.get("key")
        presses = step.get("presses", 1)
        interval = step.get("interval", 0.1)
        
        if not key:
            logger.error("按键操作缺少key参数")
            return {"success": False, "error": "按键操作需要key参数"}
        
        logger.info(f"  按下按键: {key} (次数: {presses})")
        
        if self.use_direct_input:
            for _ in range(presses):
                pydirectinput.press(key)
                if presses > 1:
                    time.sleep(interval)
        else:
            pyautogui.press(key, presses=presses, interval=interval)
        
        time.sleep(self.delay)
        return {"success": True, "action": f"按下按键: {key}"}

    def _execute_scroll(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行滚动操作"""
        x = step.get("x")
        y = step.get("y")
        dx = step.get("dx", 0)
        dy = step.get("dy", 0)
        clicks = step.get("clicks", 3)  # 滚动次数
        
        if dx == 0 and dy == 0:
            return {"success": False, "error": "滚动操作需要dx或dy参数"}
        
        if x is not None and y is not None:
            # 移动到指定位置再滚动
            if self.use_direct_input:
                pydirectinput.moveTo(x, y)
            else:
                pyautogui.moveTo(x, y)
            time.sleep(0.1)
        
        if self.use_direct_input:
            pydirectinput.scroll(dy, x=x, y=y)
        else:
            pyautogui.scroll(dy, x=x, y=y)
        
        time.sleep(self.delay)
        return {"success": True, "action": f"滚动: dx={dx}, dy={dy}"}

    def _execute_drag(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """执行拖拽操作"""
        x1 = step.get("x1") or step.get("x")
        y1 = step.get("y1") or step.get("y")
        x2 = step.get("x2")
        y2 = step.get("y2")
        duration = step.get("duration", 0.5)
        button = step.get("button", "left")
        
        if x1 is None or y1 is None or x2 is None or y2 is None:
            return {"success": False, "error": "拖拽操作需要起始和结束坐标"}
        
        if self.use_direct_input:
            pydirectinput.moveTo(x1, y1)
            time.sleep(0.1)
            pydirectinput.dragTo(x2, y2, duration=duration, button=button)
        else:
            pyautogui.drag(x2 - x1, y2 - y1, duration=duration, button=button)
        
        time.sleep(self.delay)
        return {"success": True, "action": f"拖拽: ({x1}, {y1}) -> ({x2}, {y2})"}

    def execute_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        执行多个操作步骤
        
        Args:
            steps: 操作步骤列表
        
        Returns:
            执行结果字典
        """
        logger.info(f"开始执行 {len(steps)} 个操作步骤...")
        results = []
        success_count = 0
        
        for i, step in enumerate(steps):
            step_num = i + 1
            logger.info(f"执行步骤 {step_num}/{len(steps)}: {step.get('type', 'unknown')}")
            
            result = self.execute_step(step)
            results.append({
                "step": step_num,
                "result": result
            })
            
            if result.get("success"):
                success_count += 1
                logger.info(f"  ✓ 步骤 {step_num} 执行成功")
            else:
                # 如果某一步失败，可以选择继续或停止
                error_msg = result.get('error', '未知错误')
                logger.warning(f"  ✗ 步骤 {step_num} 执行失败: {error_msg}")
        
        logger.info(f"操作步骤执行完成: {success_count}/{len(steps)} 成功")
        return {
            "success": success_count == len(steps),
            "total_steps": len(steps),
            "success_steps": success_count,
            "results": results
        }
