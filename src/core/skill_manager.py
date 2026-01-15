"""
Skills管理器
"""

import os
import sys
import json
import yaml
import importlib
import importlib.util
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass
from itertools import chain


@dataclass
class SkillDefinition:
    """技能定义"""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: str
    enabled: bool = True
    metadata: Dict[str, Any] = None
    module_path: Optional[str] = None  # Python 实现模块路径


class SkillManager:
    """Skills管理器"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = Path(skills_dir)
        self.skills: Dict[str, SkillDefinition] = {}
        self._load_skills()

    def _load_skills(self) -> None:
        """加载所有skills"""
        if not self.skills_dir.exists():
            return

        for skill_file in chain(
            self.skills_dir.rglob("*.json"),
            self.skills_dir.rglob("*.yaml"),
            self.skills_dir.rglob("*.yml"),
        ):
            try:
                skill = self._load_skill_file(skill_file)
                if skill and skill.enabled:
                    self.skills[skill.name] = skill
            except Exception as e:
                print(f"Failed to load skill {skill_file}: {e}")

    def _load_skill_file(self, file_path: Path) -> Optional[SkillDefinition]:
        """加载单个skill文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            if file_path.suffix == ".json":
                data = json.load(f)
            else:
                data = yaml.safe_load(f)

        # 构建对应的 Python 模块路径
        # 例如: skills/file_operations/write_file.json -> skills.file_operations.write_file
        module_path = None
        py_file = file_path.with_suffix(".py")
        if py_file.exists():
            # 将文件路径转换为模块路径
            relative = py_file.relative_to(self.skills_dir.parent)
            module_path = str(relative.with_suffix("")).replace(os.sep, ".")

        return SkillDefinition(
            name=data.get("name", file_path.stem),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            handler=data.get("handler", ""),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
            module_path=module_path,
        )

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """获取skill定义"""
        return self.skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        """列出所有skills"""
        return list(self.skills.values())

    def reload(self) -> None:
        """重新加载skills"""
        self.skills.clear()
        self._load_skills()

    def get_skills_for_llm(self) -> List[Dict[str, Any]]:
        """获取用于LLM工具调用的skills格式

        Anthropic API 使用 input_schema 格式
        """
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "input_schema": skill.parameters,
            }
            for skill in self.skills.values()
            if skill.enabled
        ]

    def execute_skill(self, skill_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行指定的 skill

        Args:
            skill_name: skill 名称
            arguments: skill 参数字典

        Returns:
            执行结果字典
        """
        skill = self.get_skill(skill_name)
        if not skill:
            return {
                "success": False,
                "error": f"Skill not found: {skill_name}",
            }

        if not skill.enabled:
            return {
                "success": False,
                "error": f"Skill is disabled: {skill_name}",
            }

        if not skill.module_path:
            return {
                "success": False,
                "error": f"Skill has no implementation: {skill_name}",
            }

        # 解析 handler 字符串，格式为 "module.function"
        # 例如: "file.write" -> 模块 "file_operations" 中的函数 "write_file"
        # 但我们使用模块名直接导入，所以 handler 只是参考信息

        try:
            # 动态导入模块
            module = importlib.import_module(skill.module_path)

            # 从模块名获取函数名
            # 例如: skills.file_operations.write_file -> write_file
            function_name = skill.module_path.split(".")[-1]

            # 获取函数
            func = getattr(module, function_name)

            # 执行函数
            result = func(**arguments)

            return result

        except ImportError as e:
            return {
                "success": False,
                "error": f"Failed to import module {skill.module_path}: {str(e)}",
            }
        except AttributeError as e:
            return {
                "success": False,
                "error": f"Function '{function_name}' not found in module {skill.module_path}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to execute skill {skill_name}: {str(e)}",
            }
