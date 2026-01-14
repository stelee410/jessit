"""
Jessit应用主类
"""

import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QObject, pyqtSlot
from typing import Optional

from src.ui.tray import JessitTray
from src.ui.chat_window import ChatWindow
from src.core.agent import JessitAgent
from src.core.llm import LLMConfig


class JessitApp(QObject):
    """Jessit应用主类"""

    def __init__(self, api_key: str):
        super().__init__()
        self.chat_window: Optional[ChatWindow] = None
        self.agent: Optional[JessitAgent] = None
        self.tray: Optional[JessitTray] = None
        self.app: Optional[QApplication] = None
        
        self._initialize_application(api_key)

    def _initialize_application(self, api_key: str) -> None:
        """初始化应用程序"""
        try:
            self._create_qt_application()
            self._check_system_tray()
            self._create_tray_icon()
            self._create_agent(api_key)
            self._create_chat_window()
            self._setup_tray_menu()
        except Exception as e:
            print(f"初始化失败: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def _create_qt_application(self) -> None:
        """创建Qt应用程序"""
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

    def _check_system_tray(self) -> None:
        """检查系统托盘是否可用"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            print("错误: 系统托盘不可用")
            sys.exit(1)

    def _create_tray_icon(self) -> None:
        """创建托盘图标"""
        self.tray = JessitTray(self.app)
        self.tray.show_chat.connect(self._on_show_chat)
        self.tray.quit_app.connect(self._on_quit)
        self.tray.clear_context.connect(self._on_clear_context)
        self.tray.show()

    def _create_agent(self, api_key: str) -> None:
        """创建Agent"""
        llm_config = LLMConfig(api_key=api_key)
        self.agent = JessitAgent(llm_config, provider_type="claude")

    def _create_chat_window(self) -> None:
        """创建聊天窗口"""
        self.chat_window = ChatWindow(self.agent)

    def _setup_tray_menu(self) -> None:
        """设置托盘菜单"""
        self.tray.setup_menu()

    @pyqtSlot()
    def _on_show_chat(self) -> None:
        """显示聊天窗口"""
        try:
            if self.chat_window is None:
                return

            if not self.chat_window.isVisible():
                self.chat_window.show()
            self.chat_window.activateWindow()
            self.chat_window.raise_()
            if hasattr(self.chat_window, 'input_field'):
                self.chat_window.input_field.setFocus()
        except Exception as e:
            print(f"显示聊天窗口时出错: {e}")
            import traceback
            traceback.print_exc()

    @pyqtSlot()
    def _on_quit(self) -> None:
        """退出应用"""
        if self.app:
            self.app.quit()

    @pyqtSlot()
    def _on_clear_context(self) -> None:
        """清空对话上下文"""
        if self.agent:
            self.agent.clear_context()
        if self.chat_window and hasattr(self.chat_window, 'clear_history'):
            self.chat_window.clear_history()
        if self.tray:
            self.tray.show_message("Jessit", "对话上下文已清空")

    def run(self) -> int:
        """
        运行应用
        
        Returns:
            退出代码
        """
        try:
            self._show_welcome_message()
            self._setup_exception_handler()
            return self.app.exec() if self.app else 1
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            print(f"运行应用时出错: {e}")
            import traceback
            traceback.print_exc()
            return 1

    def _show_welcome_message(self) -> None:
        """显示欢迎消息"""
        if self.tray:
            self.tray.show_message("Jessit", "Jessit已启动！右键点击托盘图标打开菜单")

    def _setup_exception_handler(self) -> None:
        """设置全局异常处理"""
        def excepthook(exc_type, exc_value, exc_traceback):
            print(f"未捕获的异常: {exc_type.__name__}: {exc_value}")
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback)

        sys.excepthook = excepthook
