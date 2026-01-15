"""
配置管理模块
"""

import os
from typing import Optional

from src.core.llm import LLMConfig


def _load_env() -> None:
    """加载.env文件（如果可用）"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def load_api_key() -> Optional[str]:
    """
    加载API Key
    
    优先从环境变量读取，如果不存在则尝试从.env文件加载
    
    Returns:
        API Key字符串，如果未找到则返回None
    """
    _load_env()
    return os.environ.get("ANTHROPIC_API_KEY")


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


def build_llm_config(api_key: str) -> LLMConfig:
    """
    构建LLM配置（支持从环境变量读取Anthropic配置）

    Args:
        api_key: 已验证的API Key

    Returns:
        LLMConfig实例
    """
    _load_env()
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or None
    model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or None
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)
