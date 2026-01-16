"""
聊天窗口UI
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSlot, QSize
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor
from typing import Optional
import json

from src.ui.workers import ChatWorker




class ChatWindow(QMainWindow):
    """聊天窗口"""

    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.chat_worker: Optional[ChatWorker] = None
        self._is_assistant_label_added = False
        self.current_progress_info = {
            "analysis": "",
            "plan": [],
            "execution_steps": [],
            "final_result": "",
        }
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("Jessit - AI Desktop Agent")
        self.setMinimumSize(800, 600)
        self.resize(900, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self._create_chat_history(layout)
        self._create_input_area(layout)
        self._show_welcome_message()

    def _create_chat_history(self, parent_layout: QVBoxLayout) -> None:
        """创建聊天历史区域"""
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: #ffffff; border: none;")
        parent_layout.addWidget(self.chat_history)

    def _create_input_area(self, parent_layout: QVBoxLayout) -> None:
        """创建输入区域"""
        # 创建详情按钮区域
        detail_button_layout = QHBoxLayout()
        self.detail_button = QPushButton("查看处理详情")
        self.detail_button.setStyleSheet(self._get_detail_button_style())
        self.detail_button.clicked.connect(self._toggle_detail_panel)
        detail_button_layout.addWidget(self.detail_button)
        detail_button_layout.addStretch()
        parent_layout.addLayout(detail_button_layout)
        
        # 创建详情面板（初始隐藏）
        self.detail_panel = self._create_detail_panel()
        self.detail_panel.setVisible(False)
        parent_layout.addWidget(self.detail_panel)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入你的问题... (按Enter发送)")
        self.input_field.setStyleSheet(self._get_input_style())
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field)

        save_button = QPushButton("保存")
        save_button.setStyleSheet(self._get_save_button_style())
        save_button.clicked.connect(self._on_save_clicked)
        save_button.setToolTip("保存当前工作为经验到jessit.txt")
        input_layout.addWidget(save_button)

        send_button = QPushButton("发送")
        send_button.setStyleSheet(self._get_button_style())
        send_button.clicked.connect(self._send_message)
        input_layout.addWidget(send_button)

        parent_layout.addLayout(input_layout)

    def _get_input_style(self) -> str:
        """获取输入框样式"""
        return """
            QLineEdit {
                padding: 10px;
                border: 2px solid #e5e7eb;
                border-radius: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #6366f1;
            }
        """

    def _get_button_style(self) -> str:
        """获取按钮样式"""
        return """
            QPushButton {
                background-color: #6366f1;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #4338ca;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """
    
    def _get_detail_button_style(self) -> str:
        """获取详情按钮样式"""
        return """
            QPushButton {
                background-color: #10b981;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
            QPushButton:pressed {
                background-color: #047857;
            }
            QPushButton:disabled {
                background-color: #9ca3af;
            }
        """
    
    def _get_save_button_style(self) -> str:
        """获取保存按钮样式"""
        return """
            QPushButton {
                background-color: #f59e0b;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
            QPushButton:pressed {
                background-color: #b45309;
            }
        """

    def _show_welcome_message(self) -> None:
        """显示欢迎消息"""
        welcome_text = (
            "你好！我是Jessit，你的AI桌面助手。"
            "我能帮你执行各种任务，如文件操作、PowerShell命令、Excel处理等。"
            "有什么可以帮助你的吗？"
        )
        self._add_message("assistant", welcome_text)

    def _add_message(self, role: str, content: str) -> None:
        """添加消息到聊天历史"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        format = QTextCharFormat()
        if role == "user":
            format.setBackground(QColor("#6366f1"))
            format.setForeground(QColor("white"))
        else:
            format.setBackground(QColor("#f3f4f6"))
            format.setForeground(QColor("#1f2937"))

        cursor.insertBlock()
        cursor.insertText(f"{role.upper()}: {content}\n\n")
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    def _send_message(self) -> None:
        """发送消息"""
        message = self.input_field.text().strip()
        if not message:
            return

        self._disable_input()
        self.input_field.clear()
        self._add_message("user", message)
        self._start_chat_worker(message)

    def _disable_input(self) -> None:
        """禁用输入"""
        self.input_field.setEnabled(False)

    def _enable_input(self) -> None:
        """启用输入"""
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

    def _start_chat_worker(self, message: str) -> None:
        """启动聊天工作线程"""
        self._is_assistant_label_added = False
        # 重置进度信息
        self.current_progress_info = {
            "analysis": "",
            "plan": [],
            "execution_steps": [],
            "final_result": "",
        }
        # 如果详情面板是展开的，更新显示（显示重置后的状态）
        if self.detail_panel.isVisible():
            self._update_detail_panel()
        self.chat_worker = ChatWorker(self.agent, message, stream=True)
        self.chat_worker.stream_chunk.connect(self._on_stream_chunk)
        self.chat_worker.response_received.connect(self._on_response_received)
        self.chat_worker.error_occurred.connect(self._on_error)
        self.chat_worker.progress_updated.connect(self._on_progress_updated)
        self.chat_worker.start()

    @pyqtSlot(str)
    def _on_stream_chunk(self, chunk: str) -> None:
        """处理流式响应"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # 如果是第一个chunk，先添加ASSISTANT标签
        if not self._is_assistant_label_added:
            cursor.insertBlock()
            format = QTextCharFormat()
            format.setBackground(QColor("#f3f4f6"))
            format.setForeground(QColor("#1f2937"))
            cursor.setCharFormat(format)
            cursor.insertText("ASSISTANT: ")
            self._is_assistant_label_added = True
        
        cursor.insertText(chunk)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    @pyqtSlot(str)
    def _on_response_received(self, response: str) -> None:
        """响应接收完成"""
        self._enable_input()
        self._append_newline()
        # 如果详情面板是展开的，更新显示最终结果
        if self.detail_panel.isVisible():
            self._update_detail_panel()

    def _append_newline(self) -> None:
        """添加换行"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText("\n\n")
        self.chat_history.setTextCursor(cursor)

    @pyqtSlot(str)
    def _on_error(self, error: str) -> None:
        """处理错误"""
        self._add_message("system", f"错误: {error}")
        self._enable_input()
    
    def _on_save_clicked(self) -> None:
        """保存按钮点击事件"""
        save_text = "把刚才的工作做一个总结，归纳为经验，添加到内容到jessit.txt"
        self.input_field.setText(save_text)
        self.input_field.setFocus()
        # 将光标移到文本末尾
        self.input_field.setCursorPosition(len(save_text))

    def append_message(self, role: str, content: str) -> None:
        """追加消息"""
        self._add_message(role, content)

    def clear_history(self) -> None:
        """清空历史记录"""
        self.chat_history.clear()

    def closeEvent(self, event) -> None:
        """窗口关闭事件"""
        # 隐藏窗口而不是关闭
        self.hide()
        event.ignore()

    def show_and_focus(self) -> None:
        """显示窗口并获取焦点"""
        self.show()
        self.activateWindow()
        self.raise_()
        self.input_field.setFocus()
    
    def _create_detail_panel(self) -> QWidget:
        """创建详情面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("AI处理详情")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1f2937;
                padding: 5px 0;
            }
        """)
        layout.addWidget(title_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # 任务分析区域
        self.analysis_label = QLabel("任务分析：")
        self.analysis_label.setStyleSheet("font-weight: bold; color: #374151;")
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMaximumHeight(100)
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        content_layout.addWidget(self.analysis_label)
        content_layout.addWidget(self.analysis_text)
        
        # 计划区域
        self.plan_label = QLabel("执行计划：")
        self.plan_label.setStyleSheet("font-weight: bold; color: #374151;")
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        self.plan_text.setMaximumHeight(150)
        self.plan_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        content_layout.addWidget(self.plan_label)
        content_layout.addWidget(self.plan_text)
        
        # 实施步骤区域
        self.steps_label = QLabel("实施步骤：")
        self.steps_label.setStyleSheet("font-weight: bold; color: #374151;")
        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        self.steps_text.setMaximumHeight(200)
        self.steps_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        content_layout.addWidget(self.steps_label)
        content_layout.addWidget(self.steps_text)
        
        # 结果区域
        self.result_label = QLabel("最终结果：")
        self.result_label.setStyleSheet("font-weight: bold; color: #374151;")
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        content_layout.addWidget(self.result_label)
        content_layout.addWidget(self.result_text)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        return panel
    
    def _toggle_detail_panel(self) -> None:
        """切换详情面板显示/隐藏"""
        is_visible = self.detail_panel.isVisible()
        self.detail_panel.setVisible(not is_visible)
        if not is_visible:
            self._update_detail_panel()
    
    def _update_detail_panel(self) -> None:
        """更新详情面板内容"""
        # 更新任务分析
        analysis = self.current_progress_info.get("analysis", "")
        if analysis:
            self.analysis_text.setPlainText(analysis)
        else:
            self.analysis_text.setPlainText("正在分析任务...")
        
        # 更新计划
        plan = self.current_progress_info.get("plan", [])
        if plan:
            plan_text = ""
            for i, step in enumerate(plan, 1):
                tool_name = step.get("tool_name", "未知工具")
                tool_args = step.get("tool_args", {})
                plan_text += f"步骤 {i}: 调用工具 {tool_name}\n"
                plan_text += f"  参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}\n\n"
            self.plan_text.setPlainText(plan_text)
        else:
            self.plan_text.setPlainText("正在制定执行计划...")
        
        # 更新实施步骤
        steps = self.current_progress_info.get("execution_steps", [])
        if steps:
            steps_text = ""
            for i, step in enumerate(steps, 1):
                tool_name = step.get("tool_name", "未知工具")
                tool_args = step.get("tool_args", {})
                result = step.get("result", {})
                status = step.get("status", "unknown")
                status_text = "✓ 成功" if status == "completed" else "✗ 失败"
                
                steps_text += f"步骤 {i}: {tool_name} - {status_text}\n"
                steps_text += f"  参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}\n"
                steps_text += f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}\n\n"
            self.steps_text.setPlainText(steps_text)
        else:
            self.steps_text.setPlainText("等待执行步骤...")
        
        # 更新最终结果
        result = self.current_progress_info.get("final_result", "")
        if result:
            self.result_text.setPlainText(result)
        else:
            self.result_text.setPlainText("正在处理，请稍候...")
    
    @pyqtSlot(dict)
    def _on_progress_updated(self, progress_data: dict) -> None:
        """处理进度更新"""
        stage = progress_data.get("stage", "")
        
        if stage == "analysis_complete":
            self.current_progress_info["analysis"] = progress_data.get("analysis", "")
        elif stage == "planning":
            self.current_progress_info["plan"] = progress_data.get("plan", [])
        elif stage == "step_complete":
            step = progress_data.get("step", {})
            self.current_progress_info["execution_steps"].append(step)
        elif stage == "complete":
            self.current_progress_info["final_result"] = progress_data.get("final_result", "")
            if "progress_info" in progress_data:
                self.current_progress_info = progress_data["progress_info"]
        elif stage == "error":
            self.current_progress_info["final_result"] = progress_data.get("error", "")
            if "progress_info" in progress_data:
                self.current_progress_info = progress_data["progress_info"]
        
        # 如果详情面板可见，实时更新
        if self.detail_panel.isVisible():
            self._update_detail_panel()