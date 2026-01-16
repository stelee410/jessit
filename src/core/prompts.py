"""
系统提示构建模块
"""

from typing import Optional
from .experience import load_experience


def build_system_prompt(experience_file: Optional[str] = None) -> str:
    """
    构建系统提示
    
    Args:
        experience_file: 经验文档文件名，如果为None则使用默认值
    
    Returns:
        系统提示字符串
    """
    base_prompt = """你是Jessit，一个运行在Windows系统上的AI桌面助手。

你的能力包括：
1. 执行PowerShell命令
2. 操作本地文件系统
3. 处理Excel文件
4. 通过Chrome扩展抓取网页数据
5. 控制鼠标和键盘（在必要时）
6. 调用各种预定义的skills

请使用自然语言与用户交流，根据用户的需求选择最合适的方式完成任务。
当需要执行危险操作时（如删除文件），请先向用户确认。"""
    
    # 加载经验文档并合并到系统提示
    experience_content = load_experience(experience_file or "jessit.txt")
    if experience_content:
        return f"""{base_prompt}

以下是之前的经验总结，请参考这些经验来更好地完成任务：
{experience_content}"""
    else:
        return base_prompt
