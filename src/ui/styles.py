"""
UI样式定义模块
"""


def get_input_style() -> str:
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


def get_button_style() -> str:
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


def get_detail_button_style() -> str:
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


def get_save_button_style() -> str:
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


def get_detail_panel_style() -> str:
    """获取详情面板样式"""
    return """
        QFrame {
            background-color: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 10px;
        }
    """


def get_detail_text_edit_style() -> str:
    """获取详情文本编辑框样式"""
    return """
        QTextEdit {
            background-color: white;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            padding: 8px;
            font-size: 12px;
        }
    """


def get_detail_label_style() -> str:
    """获取详情标签样式"""
    return "font-weight: bold; color: #374151;"


def get_detail_title_style() -> str:
    """获取详情标题样式"""
    return """
        QLabel {
            font-size: 16px;
            font-weight: bold;
            color: #1f2937;
            padding: 5px 0;
        }
    """


def get_scroll_area_style() -> str:
    """获取滚动区域样式"""
    return """
        QScrollArea {
            border: none;
            background-color: transparent;
        }
    """
