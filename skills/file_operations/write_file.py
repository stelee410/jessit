"""
文件写入操作实现
"""

from typing import Dict, Any
from src.utils.path_utils import resolve_path


def write_file(file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
    """
    写入内容到文件

    Args:
        file_path: 文件路径（支持路径别名，如"桌面/test.txt"）
        content: 要写入的内容
        encoding: 文件编码，默认为utf-8

    Returns:
        操作结果字典
    """
    try:
        # 解析路径
        path = resolve_path(file_path)

        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(path, "w", encoding=encoding) as f:
            f.write(content)

        return {
            "success": True,
            "message": f"文件已成功写入: {path}",
            "path": str(path),
        }

    except PermissionError:
        return {
            "success": False,
            "error": "权限不足，无法写入文件",
            "path": str(path),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"写入文件失败: {str(e)}",
            "path": file_path,
        }


if __name__ == "__main__":
    # 测试路径解析
    print("路径解析测试:")
    print(f"桌面 -> {resolve_path('桌面')}")
    print(f"桌面/test.txt -> {resolve_path('桌面/test.txt')}")
    print(f"文档/test.txt -> {resolve_path('文档/test.txt')}")

    # 测试写入文件
    print("\n文件写入测试:")
    result = write_file("桌面/jessit_test.txt", "hello world")
    print(result)
