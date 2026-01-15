"""
Jessit主程序入口
"""

import sys
from src.core.config import load_api_key, validate_api_key, build_llm_config
from src.ui.app import JessitApp


def main() -> None:
    """主入口函数"""
    # 加载并验证API Key
    api_key = load_api_key()
    validate_api_key(api_key)
    llm_config = build_llm_config(api_key)

    # 创建并运行应用
    jessit_app = JessitApp(llm_config)
    sys.exit(jessit_app.run())


if __name__ == "__main__":
    main()
