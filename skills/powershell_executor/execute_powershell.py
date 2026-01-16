"""
PowerShell命令执行器实现
"""

import subprocess
import sys
from typing import Dict, Any, Optional
from pathlib import Path


def execute_powershell(
    command: str,
    timeout: int = 30,
    working_directory: Optional[str] = None,
) -> Dict[str, Any]:
    """
    执行PowerShell命令并返回结果

    Args:
        command: 要执行的PowerShell命令
        timeout: 命令执行超时时间（秒），默认为30秒
        working_directory: 执行命令的工作目录，默认为当前目录

    Returns:
        操作结果字典，包含：
        - success: 是否成功
        - command: 执行的命令
        - stdout: 标准输出
        - stderr: 标准错误输出
        - return_code: 返回码
        - error: 错误信息（如果失败）
    """
    try:
        # 设置工作目录
        cwd = None
        if working_directory:
            cwd = Path(working_directory)
            if not cwd.exists():
                return {
                    "success": False,
                    "error": f"工作目录不存在: {working_directory}",
                    "command": command,
                }
            if not cwd.is_dir():
                return {
                    "success": False,
                    "error": f"路径不是目录: {working_directory}",
                    "command": command,
                }

        # 构建PowerShell命令
        # 使用 -NoProfile -NonInteractive 避免加载配置文件，提高执行速度
        # 使用 -Command 执行命令
        ps_command = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ]

        # 执行命令
        process = subprocess.run(
            ps_command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",  # 处理编码错误
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
        )

        # 准备返回结果
        result = {
            "success": process.returncode == 0,
            "command": command,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "return_code": process.returncode,
        }

        # 如果执行失败，添加错误信息
        if process.returncode != 0:
            error_msg = process.stderr.strip() or "命令执行失败"
            result["error"] = error_msg

        return result

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"命令执行超时（超过 {timeout} 秒）",
            "command": command,
            "timeout": timeout,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "未找到 PowerShell 执行程序",
            "command": command,
        }
    except PermissionError:
        return {
            "success": False,
            "error": "权限不足，无法执行命令",
            "command": command,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"执行PowerShell命令失败: {str(e)}",
            "command": command,
        }


if __name__ == "__main__":
    # 测试执行PowerShell命令
    result = execute_powershell("Get-Date")
    print(result)
