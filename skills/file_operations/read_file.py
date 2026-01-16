"""
文件读取操作实现
"""

from typing import Dict, Any
from src.utils.path_utils import resolve_path


def read_file(file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    读取文本文件内容

    Args:
        file_path: 文件路径（支持路径别名，如"桌面/test.txt"）
        encoding: 文件编码，默认为utf-8

    Returns:
        操作结果字典
    """
    try:
        # 解析路径
        path = resolve_path(file_path)

        # 检查文件是否存在
        if not path.exists():
            return {
                "success": False,
                "error": f"文件不存在: {path}",
                "path": str(path),
            }

        # 检查是否为文件
        if not path.is_file():
            return {
                "success": False,
                "error": f"路径不是文件: {path}",
                "path": str(path),
            }

        # 读取文件
        with open(path, "r", encoding=encoding) as f:
            content = f.read()

        return {
            "success": True,
            "message": f"文件已成功读取: {path}",
            "path": str(path),
            "content": content,
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": f"文件编码不匹配，尝试其他编码: {encoding}",
            "path": str(path),
        }
    except PermissionError:
        return {
            "success": False,
            "error": "权限不足，无法读取文件",
            "path": str(path),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件失败: {str(e)}",
            "path": file_path,
        }


if __name__ == "__main__":
    # 测试读取文件
    result = read_file("桌面/jessit_test.txt")
    print(result)
