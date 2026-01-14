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
)
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor
from typing import Optional

from src.ui.workers import ChatWorker




class ChatWindow(QMainWindow):
    """聊天窗口"""

    def __init__(self, agent, parent=None):
        super().__init__(parent)
        self.agent = agent
        self.chat_worker: Optional[ChatWorker] = None
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化UI"""
        self.setWindowTitle("Jessit - AI Desktop Agent")
        self.setMinimumSize(600, 500)

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
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入你的问题... (按Enter发送)")
        self.input_field.setStyleSheet(self._get_input_style())
        self.input_field.returnPressed.connect(self._send_message)
        input_layout.addWidget(self.input_field)

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
        self.chat_worker = ChatWorker(self.agent, message, stream=True)
        self.chat_worker.stream_chunk.connect(self._on_stream_chunk)
        self.chat_worker.response_received.connect(self._on_response_received)
        self.chat_worker.error_occurred.connect(self._on_error)
        self.chat_worker.start()

    @pyqtSlot(str)
    def _on_stream_chunk(self, chunk: str) -> None:
        """处理流式响应"""
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    @pyqtSlot(str)
    def _on_response_received(self, response: str) -> None:
        """响应接收完成"""
        self._enable_input()
        self._append_newline()

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
