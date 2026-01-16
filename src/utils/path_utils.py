"""
路径工具模块
"""

import os
import re
from pathlib import Path


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
