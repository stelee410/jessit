"""
经验文档管理模块
"""

from pathlib import Path
from typing import Optional


def load_experience(experience_file: str = "jessit.txt") -> str:
    """
    加载经验文档
    
    Args:
        experience_file: 经验文档文件名，默认为 "jessit.txt"
    
    Returns:
        经验内容字符串，如果文件不存在或读取失败则返回空字符串
    """
    try:
        # 尝试从当前工作目录读取经验文档
        experience_path = Path(experience_file)
        if experience_path.exists():
            with open(experience_path, "r", encoding="utf-8") as f:
                experience_content = f.read().strip()
                if experience_content:
                    print(f"已加载经验文档: {experience_path}")
                    return experience_content
                else:
                    print(f"经验文档为空: {experience_path}")
                    return ""
        else:
            print(f"经验文档不存在: {experience_path}，将创建新文件")
            return ""
    except Exception as e:
        print(f"加载经验文档失败: {e}")
        return ""


def save_experience(content: str, experience_file: str = "jessit.txt") -> bool:
    """
    保存经验到文档
    
    Args:
        content: 要保存的经验内容
        experience_file: 经验文档文件名，默认为 "jessit.txt"
    
    Returns:
        是否保存成功
    """
    try:
        experience_path = Path(experience_file)
        with open(experience_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"经验已保存到: {experience_path}")
        return True
    except Exception as e:
        print(f"保存经验文档失败: {e}")
        return False
