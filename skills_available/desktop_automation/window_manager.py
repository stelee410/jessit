"""
窗口管理模块 - 用于控制聊天窗口的显示和隐藏
"""

import win32gui
import win32con
import time
import logging
from typing import Optional
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class WindowManager:
    """窗口管理器"""

    @staticmethod
    def find_window_by_title(title: str) -> Optional[int]:
        """
        根据窗口标题查找窗口句柄
        
        Args:
            title: 窗口标题
            
        Returns:
            窗口句柄，如果未找到则返回None
        """
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if title.lower() in window_title.lower():
                    windows.append(hwnd)
            return True

        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows[0] if windows else None

    @staticmethod
    def minimize_window_by_title(title: str) -> bool:
        """
        根据窗口标题最小化窗口
        
        Args:
            title: 窗口标题
            
        Returns:
            是否成功
        """
        hwnd = WindowManager.find_window_by_title(title)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            time.sleep(0.3)  # 等待窗口完全最小化
            return True
        return False

    @staticmethod
    def minimize_qt_window(window: QWidget) -> bool:
        """
        最小化Qt窗口（使用最小化而不是隐藏，避免窗口未响应问题）
        
        Args:
            window: Qt窗口对象
            
        Returns:
            是否成功
        """
        try:
            logger.debug("最小化Qt窗口...")
            window.showMinimized()  # 最小化窗口而不是隐藏
            time.sleep(0.3)  # 等待窗口完全最小化
            logger.debug("窗口最小化完成")
            return True
        except Exception as e:
            logger.error(f"最小化窗口失败: {e}", exc_info=True)
            return False

    @staticmethod
    def restore_qt_window(window: QWidget) -> bool:
        """
        恢复Qt窗口（从最小化状态恢复）
        
        Args:
            window: Qt窗口对象
            
        Returns:
            是否成功
        """
        try:
            logger.debug("恢复Qt窗口...")
            window.showNormal()  # 从最小化状态恢复为正常显示
            window.activateWindow()
            window.raise_()
            logger.debug("窗口恢复完成")
            return True
        except Exception as e:
            logger.error(f"恢复窗口失败: {e}", exc_info=True)
            return False
