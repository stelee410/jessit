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
)
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor
from typing import Optional

from src.ui.workers import ChatWorker
from src.ui.styles import (
    get_input_style,
    get_button_style,
    get_detail_button_style,
    get_save_button_style,
)
from src.ui.detail_panel import DetailPanel
from src.ui.confirmation import ConfirmationHandler




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
        # 创建确认处理器
        self.confirmation_handler = ConfirmationHandler(self)
        self._init_ui()
        # 设置agent的确认回调
        self._setup_confirmation_callback()

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
        self.detail_button.setStyleSheet(get_detail_button_style())
        self.detail_button.clicked.connect(self._toggle_detail_panel)
        detail_button_layout.addWidget(self.detail_button)
        detail_button_layout.addStretch()
        parent_layout.addLayout(detail_button_layout)
        
        # 创建详情面板（初始隐藏）
        self.detail_panel = DetailPanel(self)
        self.detail_panel.setVisible(False)
        parent_layout.addWidget(self.detail_panel)
        
        # 输入区域
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入你的问题... (按Enter发送)")
        self.input_field.setStyleSheet(get_input_style())
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field)

        save_button = QPushButton("保存")
        save_button.setStyleSheet(get_save_button_style())
        save_button.clicked.connect(self._on_save_clicked)
        save_button.setToolTip("保存当前工作为经验到jessit.txt")
        input_layout.addWidget(save_button)

        send_button = QPushButton("发送")
        send_button.setStyleSheet(get_button_style())
        send_button.clicked.connect(self._send_message)
        input_layout.addWidget(send_button)

        parent_layout.addLayout(input_layout)


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
            self.detail_panel.update_progress_info(self.current_progress_info)
        self.chat_worker = ChatWorker(self.agent, message, stream=True, chat_window=self)
        self.chat_worker.stream_chunk.connect(self._on_stream_chunk)
        self.chat_worker.response_received.connect(self._on_response_received)
        self.chat_worker.error_occurred.connect(self._on_error)
        self.chat_worker.progress_updated.connect(self._on_progress_updated)
        self.chat_worker.start()
        # 启动确认队列处理器（定期检查队列）
        self.confirmation_handler.start_confirmation_processor()

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
            self.detail_panel.update_progress_info(self.current_progress_info)

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
    def _toggle_detail_panel(self) -> None:
        """切换详情面板显示/隐藏"""
        is_visible = self.detail_panel.isVisible()
        self.detail_panel.setVisible(not is_visible)
        if not is_visible:
            self.detail_panel.update_progress_info(self.current_progress_info)
    
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
            self.detail_panel.update_progress_info(self.current_progress_info)
    
    def _setup_confirmation_callback(self) -> None:
        """设置agent的确认回调"""
        if self.agent:
            self.agent.confirmation_callback = self.confirmation_handler.create_confirmation_callback()