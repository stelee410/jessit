"""
全局热键管理器
使用 Windows API RegisterHotKey 注册全局热键
"""

import sys
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget

try:
    import win32con
    from ctypes import windll, wintypes, Structure
    WIN32_AVAILABLE = True
    user32 = windll.user32
    kernel32 = windll.kernel32
except ImportError:
    WIN32_AVAILABLE = False
    user32 = None
    kernel32 = None
    Structure = None


class HotkeyWindow(QWidget):
    """用于接收热键消息的隐藏窗口"""
    
    hotkey_triggered = pyqtSignal()
    
    def __init__(self, hotkey_id, parent=None):
        super().__init__(parent)
        self.hotkey_id = hotkey_id
        # 设置为工具窗口，不显示在任务栏
        self.setWindowFlags(self.windowFlags() | self.windowType().Tool)
        self.hide()  # 隐藏窗口
    
    def nativeEvent(self, eventType, message):
        """处理原生 Windows 事件"""
        # 先调用父类方法，确保正常处理其他消息
        try:
            result = super().nativeEvent(eventType, message)
        except Exception as e:
            # 如果父类方法出错，返回 False, 0 避免崩溃
            return False, 0
        
        # 确保返回元组格式
        if not isinstance(result, tuple):
            result = (result, 0) if result else (False, 0)
        
        # 如果不是 Windows 平台或 API 不可用，直接返回
        if sys.platform != 'win32' or not WIN32_AVAILABLE or Structure is None:
            return result
        
        # 检查是否是 Windows 消息
        try:
            if isinstance(eventType, bytes):
                event_type_str = eventType.decode('utf-8', errors='ignore')
            else:
                event_type_str = str(eventType)
        except:
            return result
        
        if "windows" not in event_type_str.lower():
            return result
        
        # 尝试解析热键消息（只在确实是 Windows 消息时）
        # 定义 MSG 结构（在方法外部定义会更安全，但这里先放在 try 块内）
        try:
            # 定义 MSG 结构
            class MSG(Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam", wintypes.WPARAM),
                    ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD),
                    ("pt", wintypes.POINT),
                ]
            
            # 将 voidptr 转换为 MSG 结构
            try:
                # 获取指针地址
                msg_ptr = None
                if hasattr(message, '__int__'):
                    try:
                        msg_ptr = message.__int__()
                    except:
                        pass
                elif hasattr(message, 'value'):
                    try:
                        msg_ptr = message.value
                    except:
                        pass
                
                if msg_ptr is None or msg_ptr == 0:
                    # 无法获取有效指针，跳过
                    return result
                
                # 从地址创建 MSG 结构（使用 ctypes 的 from_address）
                try:
                    msg = MSG.from_address(msg_ptr)
                except (ValueError, OSError, MemoryError):
                    # 无效的内存地址，跳过
                    return result
                
                # 检查是否是热键消息
                if msg.message == win32con.WM_HOTKEY:
                    # 检查是否是我们的热键ID
                    if msg.wParam == self.hotkey_id:
                        # 发出信号
                        from PyQt6.QtCore import QTimer
                        QTimer.singleShot(0, self.hotkey_triggered.emit)
                        return True, 0
            except Exception as e1:
                # 所有异常都静默处理，避免崩溃
                # 不打印异常，避免日志过多导致性能问题
                pass
        except Exception as e:
            # 如果定义 MSG 结构失败，静默处理
            pass
        
        return result


class HotKeyManager(QObject):
    """全局热键管理器"""
    
    # 热键被触发时发出的信号
    hotkey_triggered = pyqtSignal()
    
    # Windows 虚拟键码映射
    VK_MAP = {
        'A': 0x41, 'B': 0x42, 'C': 0x43, 'D': 0x44, 'E': 0x45,
        'F': 0x46, 'G': 0x47, 'H': 0x48, 'I': 0x49, 'J': 0x4A,
        'K': 0x4B, 'L': 0x4C, 'M': 0x4D, 'N': 0x4E, 'O': 0x4F,
        'P': 0x50, 'Q': 0x51, 'R': 0x52, 'S': 0x53, 'T': 0x54,
        'U': 0x55, 'V': 0x56, 'W': 0x57, 'X': 0x58, 'Y': 0x59,
        'Z': 0x5A,
        '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
        '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    }
    
    # 修饰键映射
    MOD_MAP = {
        'Ctrl': win32con.MOD_CONTROL if WIN32_AVAILABLE else 0,
        'Alt': win32con.MOD_ALT if WIN32_AVAILABLE else 0,
        'Shift': win32con.MOD_SHIFT if WIN32_AVAILABLE else 0,
        'Win': win32con.MOD_WIN if WIN32_AVAILABLE else 0,
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hotkey_id = 1  # 热键ID，必须唯一
        self.registered = False
        self.modifiers = []
        self.key = None
        self.hwnd = None
        self.hotkey_window = None  # 用于接收消息的隐藏窗口
        
        if not WIN32_AVAILABLE:
            print("警告: Windows API 不可用，热键功能将无法使用")
    
    def register_hotkey(self, modifiers: list, key: str, hwnd=None, parent_widget=None) -> bool:
        """
        注册全局热键
        
        Args:
            modifiers: 修饰键列表，如 ['Ctrl', 'Alt']
            key: 主键，如 'J'
            hwnd: 可选的窗口句柄，如果提供则使用该窗口接收消息
            parent_widget: 可选的父窗口，用于 HotkeyWindow
            
        Returns:
            是否注册成功
        """
        if not WIN32_AVAILABLE:
            print("错误: Windows API 不可用，无法注册热键")
            return False
        
        # 先注销已注册的热键
        if self.registered:
            self.unregister_hotkey()
        
        # 如果提供了窗口句柄，直接使用
        if hwnd:
            self.hwnd = hwnd
        else:
            # 创建一个专用的隐藏窗口来接收热键消息
            try:
                # 如果提供了父窗口，直接使用
                if parent_widget is None:
                    from PyQt6.QtWidgets import QApplication
                    app = QApplication.instance()
                    
                    # 尝试获取聊天窗口（QMainWindow）
                    if app:
                        windows = app.allWindows()
                        if windows:
                            # 优先查找 QMainWindow（通常是聊天窗口）
                            for win in windows:
                                from PyQt6.QtWidgets import QMainWindow
                                if isinstance(win, QMainWindow):
                                    parent_widget = win
                                    break
                            
                            # 如果没找到 QMainWindow，使用任何 QWidget
                            if parent_widget is None:
                                for win in windows:
                                    if isinstance(win, QWidget):
                                        parent_widget = win
                                        break
                
                self.hotkey_window = HotkeyWindow(self.hotkey_id, parent_widget)
                self.hotkey_window.hotkey_triggered.connect(self.hotkey_triggered.emit)
                
                # 获取窗口句柄
                win_id = self.hotkey_window.winId()
                if not win_id:
                    # 如果无法获取，尝试显示一下
                    self.hotkey_window.show()
                    win_id = self.hotkey_window.winId()
                    self.hotkey_window.hide()
                
                if not win_id:
                    return False
                
                self.hwnd = int(win_id)
            except Exception as e:
                return False
        
        # 计算修饰键组合
        mod_flags = 0
        for mod in modifiers:
            mod_upper = mod.capitalize()
            if mod_upper in self.MOD_MAP:
                mod_flags |= self.MOD_MAP[mod_upper]
            else:
                print(f"警告: 不支持的修饰键: {mod}")
        
        # 获取主键的虚拟键码
        key_upper = key.upper()
        if key_upper not in self.VK_MAP:
            print(f"错误: 不支持的主键: {key}")
            return False
        
        vk_code = self.VK_MAP[key_upper]
        
        # 使用 Windows API RegisterHotKey 注册全局热键
        try:
            result = user32.RegisterHotKey(
                self.hwnd,      # 窗口句柄
                self.hotkey_id, # 热键ID
                mod_flags,      # 修饰键组合
                vk_code         # 虚拟键码
            )
            
            if result:
                self.modifiers = modifiers
                self.key = key
                self.registered = True
                return True
            else:
                # 获取错误代码
                error_code = kernel32.GetLastError()
                if error_code == 1409:  # ERROR_HOTKEY_ALREADY_REGISTERED
                    print(f"错误: 热键 {'+'.join(modifiers)}+{key} 已被其他程序占用")
                else:
                    print(f"错误: RegisterHotKey 失败，错误代码: {error_code}")
                return False
                
        except Exception as e:
            print(f"注册热键时发生异常: {e}")
            return False
    
    def unregister_hotkey(self) -> bool:
        """注销全局热键"""
        if not WIN32_AVAILABLE or not self.registered:
            return False
        
        try:
            # 使用 Windows API UnregisterHotKey 注销热键
            if self.hwnd:
                user32.UnregisterHotKey(self.hwnd, self.hotkey_id)
            
            # 清理热键窗口
            if self.hotkey_window:
                try:
                    self.hotkey_window.close()
                    self.hotkey_window = None
                except:
                    pass
            
            self.registered = False
            self.hwnd = None
            return True
            
        except Exception as e:
            return False
    
    def __del__(self):
        """析构函数，确保热键被注销"""
        if self.registered:
            self.unregister_hotkey()
