"""
确认对话框处理模块
"""

import queue
import threading
from typing import Callable, Optional
from PyQt6.QtWidgets import QMessageBox, QWidget
from PyQt6.QtCore import QTimer


class ConfirmationHandler:
    """确认对话框处理器"""
    
    def __init__(self, parent_widget: QWidget):
        """
        初始化确认处理器
        
        Args:
            parent_widget: 父窗口组件，用于显示对话框
        """
        self.parent_widget = parent_widget
        self.confirmation_queue: queue.Queue = queue.Queue()
        self._confirmation_timer: Optional[QTimer] = None
    
    def create_confirmation_callback(self) -> Callable[[str, str], bool]:
        """
        创建确认回调函数（用于在工作线程中调用）
        
        Returns:
            确认回调函数
        """
        def confirmation_callback(tool_name: str, operation_description: str) -> bool:
            """
            确认回调函数（可能在工作线程中调用）
            通过队列在主线程中请求确认
            """
            # 创建一个事件来等待响应
            response_event = threading.Event()
            result_container = {"result": False}
            
            # 将确认请求放入队列，在主线程中处理
            self.confirmation_queue.put({
                "tool_name": tool_name,
                "operation_description": operation_description,
                "response_event": response_event,
                "result_container": result_container,
            })
            
            # 使用QTimer在主线程中处理确认请求
            QTimer.singleShot(0, self._process_confirmation_queue)
            
            # 等待主线程的响应（最多等待60秒）
            if response_event.wait(timeout=60):
                return result_container["result"]
            else:
                # 超时，默认拒绝
                return False
        
        return confirmation_callback
    
    def start_confirmation_processor(self) -> None:
        """启动确认队列处理器"""
        # 创建一个定时器来定期处理确认队列
        if not self._confirmation_timer:
            self._confirmation_timer = QTimer(self.parent_widget)
            self._confirmation_timer.timeout.connect(self._process_confirmation_queue)
            self._confirmation_timer.start(100)  # 每100ms检查一次
    
    def _process_confirmation_queue(self) -> None:
        """处理确认队列中的请求（在主线程中调用）"""
        try:
            while True:
                try:
                    request = self.confirmation_queue.get_nowait()
                    tool_name = request["tool_name"]
                    operation_description = request["operation_description"]
                    response_event = request["response_event"]
                    result_container = request["result_container"]
                    
                    # 显示确认对话框
                    result = self.request_confirmation(tool_name, operation_description)
                    result_container["result"] = result
                    response_event.set()
                except queue.Empty:
                    break
        except Exception as e:
            print(f"处理确认队列时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def request_confirmation(self, tool_name: str, operation_description: str) -> bool:
        """
        请求用户确认危险操作（在UI线程中调用）
        
        Args:
            tool_name: 工具名称
            operation_description: 操作描述
            
        Returns:
            True 如果用户确认，False 如果用户取消
        """
        # 显示确认对话框
        reply = QMessageBox.question(
            self.parent_widget,
            "确认危险操作",
            f"检测到危险操作：{operation_description}\n\n工具：{tool_name}\n\n是否确认执行此操作？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No  # 默认选择"否"以更安全
        )
        
        return reply == QMessageBox.StandardButton.Yes
