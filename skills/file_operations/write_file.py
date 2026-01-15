"""
文件写入操作实现
"""

import os
import re
from pathlib import Path
from typing import Dict, Any


def resolve_path(path_str: str) -> Path:
    """
    解析路径，支持常见路径别名

    支持的别名：
    - 桌面 / Desktop
    - 文档 / Documents
    - 下载 / Downloads
    - 图片 / Pictures
    - 视频 / Videos
    - 音乐 / Music
    - 主目录 / ~ / home

    Args:
        path_str: 路径字符串

    Returns:
        解析后的 Path 对象
    """
    # 获取用户主目录
    home_dir = Path.home()

    # Windows 特殊路径
    desktop = home_dir / "Desktop"
    documents = home_dir / "Documents"
    downloads = home_dir / "Downloads"
    pictures = home_dir / "Pictures"
    videos = home_dir / "Videos"
    music = home_dir / "Music"

    # 定义路径映射规则 - 使用捕获组来精确匹配别名部分
    patterns = [
        (r'^(桌面|Desktop)(.*)$', desktop),
        (r'^(文档|Documents)(.*)$', documents),
        (r'^(下载|Downloads)(.*)$', downloads),
        (r'^(图片|Pictures)(.*)$', pictures),
        (r'^(视频|Videos)(.*)$', videos),
        (r'^(音乐|Music)(.*)$', music),
        (r'^(~|/home)(.*)$', home_dir),
    ]

    # 检查是否匹配路径别名
    for pattern, base_path in patterns:
        match = re.match(pattern, path_str, re.IGNORECASE)
        if match:
            # 提取剩余路径部分（group(2)）
            suffix = match.group(2).strip('\\/ ')
            if suffix:
                return base_path / suffix
            return base_path

    # 处理波浪号和相对路径
    path_str = path_str.replace('~', str(home_dir))
    # 展开 Windows 环境变量（如 %USERNAME%）
    path_str = os.path.expandvars(path_str)
    return Path(path_str).expanduser().absolute()


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
