"""
安全检测模块 - 检测危险操作
"""

import re
from typing import Dict, Any, Tuple


def is_dangerous_operation(tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, str]:
    """
    检测是否为危险操作
    
    Args:
        tool_name: 工具名称
        tool_args: 工具参数
        
    Returns:
        (是否为危险操作, 危险操作描述)
    """
    # 检测删除文件的操作（通过PowerShell命令）
    if tool_name == "execute_powershell":
        command = tool_args.get("command", "").strip()
        # 检测删除命令
        delete_patterns = [
            r'\bRemove-Item\b',
            r'\brm\b',
            r'\bdel\s',
            r'\berase\s',
            r'\brmdir\s',
            r'\bRemove-Item\s+-Force\b',
            r'\bRemove-Item\s+-Recurse\b',
        ]
        for pattern in delete_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                # 提取要删除的文件路径（简单匹配）
                path_match = re.search(r'["\']([^"\']+)["\']|(-Path|--Path)\s+([^\s]+)', command, re.IGNORECASE)
                target = path_match.group(1) if path_match else (path_match.group(3) if path_match else "文件")
                return True, f"执行删除操作: {command}"
    
    # 检测其他危险操作可以在这里添加
    # 例如：格式化磁盘、修改系统配置等
    
    return False, ""
