"""
Skills管理器
"""

import os
import json
import yaml
from typing import Dict, List, Optional, Any
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

        return SkillDefinition(
            name=data.get("name", file_path.stem),
            description=data.get("description", ""),
            parameters=data.get("parameters", {}),
            handler=data.get("handler", ""),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
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
        """获取用于LLM工具调用的skills格式"""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "parameters": skill.parameters,
            }
            for skill in self.skills.values()
            if skill.enabled
        ]
