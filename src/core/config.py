"""
配置管理模块
"""

import os
from typing import Optional


def load_api_key() -> Optional[str]:
    """
    加载API Key
    
    优先从环境变量读取，如果不存在则尝试从.env文件加载
    
    Returns:
        API Key字符串，如果未找到则返回None
    """
    # 首先尝试从环境变量读取
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if api_key:
        return api_key
    
    # 尝试从.env文件加载
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        return api_key
    except ImportError:
        pass
    
    return None


def validate_api_key(api_key: Optional[str]) -> str:
    """
    验证API Key是否存在
    
    Args:
        api_key: API Key字符串
        
    Returns:
        验证通过的API Key
        
    Raises:
        SystemExit: 如果API Key不存在
    """
    if not api_key:
        print("错误: 未设置ANTHROPIC_API_KEY环境变量")
        print("请设置环境变量或创建.env文件，内容如下:")
        print("ANTHROPIC_API_KEY=your_api_key_here")
        raise SystemExit(1)
    
    return api_key
