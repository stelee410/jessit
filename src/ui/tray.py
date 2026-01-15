"""
系统托盘图标 - 简化版本
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal


class JessitTray(QObject):
    """Jessit系统托盘"""

    # 信号定义
    show_chat = pyqtSignal()
    quit_app = pyqtSignal()
    clear_context = pyqtSignal()

    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.tray_icon = QSystemTrayIcon()
        self._create_tray_icon()

    def setup_menu(self):
        """设置托盘菜单"""
        try:
            # 创建菜单
            self.menu = QMenu()

            # 打开聊天窗口
            show_action = QAction("打开聊天窗口", self)
            show_action.triggered.connect(self.show_chat)
            self.menu.addAction(show_action)

            # 清空上下文
            clear_action = QAction("清空对话上下文", self)
            clear_action.triggered.connect(self.clear_context)
            self.menu.addAction(clear_action)

            self.menu.addSeparator()

            # 退出
            quit_action = QAction("退出", self)
            quit_action.triggered.connect(self.quit_app)
            self.menu.addAction(quit_action)

            # 设置上下文菜单
            self.tray_icon.setContextMenu(self.menu)

        except Exception as e:
            import traceback
            traceback.print_exc()

    def _create_tray_icon(self):
        """创建托盘图标"""
        from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont

        # 创建一个带J字母的图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor("#6366f1"))

        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        font = QFont()
        font.setPixelSize(48)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), 0x84, "J")
        painter.end()

        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Jessit - AI Desktop Agent")
        
        # 连接激活信号，处理双击事件
        self.tray_icon.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        """处理托盘图标激活事件"""
        # 双击时打开聊天窗口
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_chat.emit()

    def show(self):
        """显示托盘图标"""
        self.tray_icon.show()

    def hide(self):
        """隐藏托盘图标"""
        self.tray_icon.hide()

    def show_message(self, title: str, message: str):
        """显示通知消息"""
        self.tray_icon.showMessage(title, message)
