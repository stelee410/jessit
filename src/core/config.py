"""
配置管理模块
"""

import os
import json
from typing import Dict, Any

from src.core.llm import LLMConfig
from src.core.env import get_api_key, validate_api_key, load_env


def load_api_key():
    """
    加载API Key（兼容旧接口）
    
    Returns:
        API Key字符串，如果未找到则返回None
    """
    return get_api_key()


def build_llm_config(api_key: str) -> LLMConfig:
    """
    构建LLM配置（支持从环境变量读取Anthropic配置）

    Args:
        api_key: 已验证的API Key

    Returns:
        LLMConfig实例
    """
    load_env()
    base_url = os.environ.get("ANTHROPIC_BASE_URL") or None
    model = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or None
    return LLMConfig(api_key=api_key, base_url=base_url, model=model)


def load_settings() -> Dict[str, Any]:
    """
    加载配置文件
    
    Returns:
        配置字典
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "settings.json")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"警告: 配置文件不存在: {config_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"错误: 配置文件格式错误: {e}")
        return {}


def get_hotkey_config() -> Dict[str, Any]:
    """
    获取热键配置
    
    Returns:
        热键配置字典，包含 enabled, modifiers, key
    """
    settings = load_settings()
    hotkey_config = settings.get("hotkey", {})
    
    # 默认配置
    return {
        "enabled": hotkey_config.get("enabled", True),
        "modifiers": hotkey_config.get("modifiers", ["Ctrl", "Alt"]),
        "key": hotkey_config.get("key", "J")
    }
