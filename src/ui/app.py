"""
Jessit应用主类
"""

import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QObject, pyqtSlot
from typing import Optional

from src.ui.tray import JessitTray
from src.ui.chat_window import ChatWindow
from src.ui.hotkey import HotKeyManager
from src.core.agent import JessitAgent
from src.core.llm import LLMConfig
from src.core.config import get_hotkey_config


class JessitApp(QObject):
    """Jessit应用主类"""

    def __init__(self, llm_config: LLMConfig):
        super().__init__()
        self.chat_window: Optional[ChatWindow] = None
        self.agent: Optional[JessitAgent] = None
        self.tray: Optional[JessitTray] = None
        self.app: Optional[QApplication] = None
        self.hotkey_manager: Optional[HotKeyManager] = None
        self.llm_config = llm_config
        
        self._initialize_application()

    def _initialize_application(self) -> None:
        """初始化应用程序"""
        try:
            self._create_qt_application()
            self._check_system_tray()
            self._create_tray_icon()
            # 先创建聊天窗口（临时agent），然后在创建chat_window后再设置确认回调
            self._create_agent()
            self._create_chat_window()
            # 创建chat_window后，更新agent的确认回调
            self._setup_agent_confirmation()
            self._setup_tray_menu()
            # 先显示聊天窗口
            self._show_chat_window_on_startup()
            # 聊天窗口显示后再注册热键
            self._setup_hotkey()
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

    def _create_agent(self) -> None:
        """创建Agent"""
        self.agent = JessitAgent(self.llm_config, provider_type="claude")

    def _create_chat_window(self) -> None:
        """创建聊天窗口"""
        self.chat_window = ChatWindow(self.agent)
        
        # 注册聊天窗口到desktop_automation skill（如果存在）
        try:
            from skills.desktop_automation.desktop_automation import set_chat_window
            set_chat_window(self.chat_window)
        except ImportError:
            pass  # desktop_automation skill 可能不存在
    
    def _setup_agent_confirmation(self) -> None:
        """设置Agent的确认回调（已在ChatWindow中设置，这里无需操作）"""
        # 确认回调已在ChatWindow的_setup_confirmation_callback中设置
        pass

    def _setup_tray_menu(self) -> None:
        """设置托盘菜单"""
        self.tray.setup_menu()
    
    def _show_chat_window_on_startup(self) -> None:
        """启动时显示聊天窗口"""
        try:
            if self.chat_window:
                self.chat_window.show()
                self.chat_window.activateWindow()
                self.chat_window.raise_()
                if hasattr(self.chat_window, 'input_field'):
                    self.chat_window.input_field.setFocus()
        except Exception as e:
            print(f"显示聊天窗口时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _setup_hotkey(self) -> None:
        """设置全局热键（在聊天窗口显示后调用）"""
        try:
            hotkey_config = get_hotkey_config()
            
            if not hotkey_config.get("enabled", True):
                print("热键功能已禁用")
                return
            
            modifiers = hotkey_config.get("modifiers", ["Ctrl", "Alt"])
            key = hotkey_config.get("key", "J")
            
            self.hotkey_manager = HotKeyManager(self)
            self.hotkey_manager.hotkey_triggered.connect(self._on_show_chat)
            
            # 使用聊天窗口作为父对象，确保 HotkeyWindow 有有效的父窗口
            parent_widget = self.chat_window if self.chat_window else None
            
            # 不使用聊天窗口句柄，让 HotKeyManager 创建专门的 HotkeyWindow
            # 但传递聊天窗口作为父对象
            if self.hotkey_manager.register_hotkey(modifiers, key, hwnd=None, parent_widget=parent_widget):
                hotkey_str = "+".join(modifiers) + "+" + key
                if self.tray:
                    self.tray.show_message("Jessit", f"热键已注册: {hotkey_str}")
            else:
                print("警告: 热键注册失败，但应用将继续运行")
                
        except Exception as e:
            print(f"设置热键时出错: {e}")
            import traceback
            traceback.print_exc()
            print("热键设置失败，但应用将继续运行")

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
        # 注销热键
        if self.hotkey_manager:
            self.hotkey_manager.unregister_hotkey()
        
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
