"""
Skills 测试脚本
用于直接测试项目中的 skills
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.skill_manager import SkillManager


class SkillTester:
    """Skills 测试器"""
    
    def __init__(self, skills_dir: str = "skills"):
        """初始化测试器"""
        self.skill_manager = SkillManager(skills_dir)
        print(f"已加载 {len(self.skill_manager.list_skills())} 个 skills")
    
    def list_skills(self):
        """列出所有可用的 skills"""
        skills = self.skill_manager.list_skills()
        if not skills:
            print("没有找到可用的 skills")
            return
        
        print("\n" + "=" * 80)
        print("可用的 Skills:")
        print("=" * 80)
        
        for i, skill in enumerate(skills, 1):
            print(f"\n{i}. {skill.name}")
            print(f"   描述: {skill.description}")
            print(f"   状态: {'启用' if skill.enabled else '禁用'}")
            
            # 显示参数信息
            params = skill.parameters.get("properties", {})
            if params:
                print(f"   参数:")
                for param_name, param_info in params.items():
                    param_type = param_info.get("type", "unknown")
                    param_desc = param_info.get("description", "")
                    required = param_name in skill.parameters.get("required", [])
                    default = param_info.get("default", None)
                    
                    req_mark = "[必需]" if required else "[可选]"
                    default_mark = f" (默认: {default})" if default is not None else ""
                    print(f"     - {param_name} ({param_type}) {req_mark}: {param_desc}{default_mark}")
            
            # 显示元数据
            if skill.metadata:
                print(f"   元数据: {json.dumps(skill.metadata, ensure_ascii=False)}")
        
        print("\n" + "=" * 80)
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取 skill 的详细信息"""
        skill = self.skill_manager.get_skill(skill_name)
        if not skill:
            return None
        
        return {
            "name": skill.name,
            "description": skill.description,
            "parameters": skill.parameters,
            "enabled": skill.enabled,
            "metadata": skill.metadata
        }
    
    def test_skill(self, skill_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """测试指定的 skill"""
        if arguments is None:
            arguments = {}
        
        print(f"\n{'=' * 80}")
        print(f"测试 Skill: {skill_name}")
        print(f"{'=' * 80}")
        print(f"参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        print(f"{'=' * 80}\n")
        
        # 执行 skill
        result = self.skill_manager.execute_skill(skill_name, arguments)
        
        # 显示结果
        print("执行结果:")
        print("-" * 80)
        if isinstance(result, dict):
            if result.get("success", False):
                print("[成功] 执行成功")
            else:
                print("[失败] 执行失败")
                if "error" in result:
                    print(f"错误: {result['error']}")
            
            # 美化输出结果
            print("\n详细结果:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result)
        
        print(f"\n{'=' * 80}\n")
        
        return result
    
    def interactive_test(self, skill_name: Optional[str] = None):
        """交互式测试 skill"""
        if skill_name is None:
            # 列出所有 skills
            self.list_skills()
            
            # 让用户选择
            skills = self.skill_manager.list_skills()
            if not skills:
                return
            
            print("\n请输入要测试的 skill 名称（或输入序号）:")
            choice = input("> ").strip()
            
            # 尝试按序号选择
            try:
                index = int(choice) - 1
                if 0 <= index < len(skills):
                    skill_name = skills[index].name
                else:
                    print("无效的序号")
                    return
            except ValueError:
                # 按名称选择
                skill_name = choice
        
        # 获取 skill 信息
        skill = self.skill_manager.get_skill(skill_name)
        if not skill:
            print(f"未找到 skill: {skill_name}")
            return
        
        if not skill.enabled:
            print(f"Skill {skill_name} 已禁用")
            return
        
        print(f"\n准备测试: {skill.name}")
        print(f"描述: {skill.description}")
        
        # 收集参数
        params = skill.parameters.get("properties", {})
        required_params = skill.parameters.get("required", [])
        arguments = {}
        
        if params:
            print("\n请输入参数 (直接回车使用默认值，输入 'skip' 跳过可选参数):")
            
            for param_name, param_info in params.items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                default = param_info.get("default", None)
                is_required = param_name in required_params
                
                # 显示参数信息
                req_mark = "[必需]" if is_required else "[可选]"
                default_mark = f" (默认: {json.dumps(default, ensure_ascii=False)})" if default is not None else ""
                prompt = f"{param_name} ({param_type}) {req_mark}{default_mark}: "
                
                # 对于 object 类型，提供提示
                if param_type == "object":
                    if default is not None:
                        example = json.dumps(default, ensure_ascii=False)
                        prompt += f"\n   提示: 请输入 JSON 格式，例如: {example}\n   或者直接回车使用默认值: "
                    else:
                        prompt += "\n   提示: 请输入 JSON 格式，例如: {\"key\": \"value\"}\n   "
                
                value = input(prompt).strip()
                
                # 处理输入
                if not value:
                    if default is not None:
                        arguments[param_name] = default
                    elif is_required:
                        print(f"  警告: {param_name} 是必需参数，但未提供值")
                    continue
                
                if value.lower() == "skip" and not is_required:
                    continue
                
                # 尝试解析 JSON (用于复杂类型，特别是 object 类型)
                if param_type == "object":
                    # 对于 object 类型，必须解析为 JSON
                    try:
                        parsed_value = json.loads(value)
                        arguments[param_name] = parsed_value
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"  错误: 无法解析 JSON: {e}")
                        print(f"  提示: object 类型参数必须是有效的 JSON 格式")
                        # 询问是否使用默认值
                        if default is not None:
                            use_default = input(f"  是否使用默认值？(y/n): ").strip().lower()
                            if use_default in ("y", "yes", ""):
                                arguments[param_name] = default
                        continue
                else:
                    try:
                        parsed_value = json.loads(value)
                        arguments[param_name] = parsed_value
                    except (json.JSONDecodeError, ValueError):
                        # 如果不是 JSON，按类型转换
                        if param_type == "boolean":
                            arguments[param_name] = value.lower() in ("true", "1", "yes", "y")
                        elif param_type == "integer":
                            try:
                                arguments[param_name] = int(value)
                            except ValueError:
                                arguments[param_name] = value
                        elif param_type == "number":
                            try:
                                arguments[param_name] = float(value)
                            except ValueError:
                                arguments[param_name] = value
                        else:
                            arguments[param_name] = value
        else:
            print("该 skill 不需要参数")
        
        # 执行测试
        self.test_skill(skill_name, arguments)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试 Skills")
    parser.add_argument(
        "--skill",
        "-s",
        type=str,
        help="要测试的 skill 名称"
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="列出所有可用的 skills"
    )
    parser.add_argument(
        "--args",
        "-a",
        type=str,
        help="JSON 格式的参数 (例如: '{\"file_path\": \"test.txt\"}')"
    )
    parser.add_argument(
        "--args-file",
        "-f",
        type=str,
        help="从文件读取 JSON 格式的参数"
    )
    parser.add_argument(
        "--skills-dir",
        type=str,
        default="skills",
        help="Skills 目录路径 (默认: skills)"
    )
    
    args = parser.parse_args()
    
    tester = SkillTester(skills_dir=args.skills_dir)
    
    if args.list:
        tester.list_skills()
    elif args.skill:
        # 解析参数
        arguments = {}
        
        # 优先从文件读取参数
        if args.args_file:
            try:
                args_file_path = Path(args.args_file)
                if not args_file_path.exists():
                    print(f"参数文件不存在: {args.args_file}")
                    return
                with open(args_file_path, "r", encoding="utf-8") as f:
                    arguments = json.load(f)
            except json.JSONDecodeError as e:
                print(f"参数文件 JSON 解析失败: {e}")
                return
            except Exception as e:
                print(f"读取参数文件失败: {e}")
                return
        elif args.args:
            try:
                # 尝试直接解析 JSON
                arguments = json.loads(args.args)
            except json.JSONDecodeError:
                # 如果失败，尝试处理常见的引号问题
                # 替换单引号为双引号（如果整个字符串被单引号包裹）
                cleaned = args.args.strip()
                if cleaned.startswith("'") and cleaned.endswith("'"):
                    cleaned = cleaned[1:-1]
                # 尝试替换转义的双引号
                cleaned = cleaned.replace('\\"', '"')
                
                try:
                    arguments = json.loads(cleaned)
                except json.JSONDecodeError as e:
                    print(f"参数解析失败: {e}")
                    print(f"原始输入: {args.args}")
                    print("\n提示:")
                    print("1. 确保 JSON 格式正确")
                    print("2. 在 PowerShell 中，使用单引号包裹 JSON，内部双引号需要转义:")
                    print('   例如: --args \'{"file_path": "test.txt"}\'')
                    print("3. 或者使用 --args-file 从文件读取参数")
                    print("4. 或者使用交互式模式: python test_skills.py")
                    return
        
        tester.test_skill(args.skill, arguments)
    else:
        # 交互式模式
        tester.interactive_test()


if __name__ == "__main__":
    main()
