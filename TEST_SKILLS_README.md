# Skills 测试脚本使用说明

## 概述

`test_skills.py` 是一个用于测试项目中 skills 的脚本，可以列出所有可用的 skills，并支持交互式和命令行两种方式测试 skills。

## 使用方法

### 1. 列出所有可用的 skills

```bash
python test_skills.py --list
# 或
python test_skills.py -l
```

### 2. 交互式测试（推荐）

直接运行脚本，进入交互式模式：

```bash
python test_skills.py
```

在交互式模式下：
- 脚本会列出所有可用的 skills
- 你可以输入 skill 名称或序号来选择要测试的 skill
- 然后按提示输入参数（直接回车使用默认值）

### 3. 命令行测试

#### 方式 1: 直接传递 JSON 参数

```bash
# 测试 read_file skill
python test_skills.py --skill read_file --args '{"file_path": "test_skills.py"}'

# 测试 write_file skill
python test_skills.py --skill write_file --args '{"file_path": "桌面/test.txt", "content": "Hello World"}'

# 测试 market_pulse_observer skill（使用默认参数）
python test_skills.py --skill market_pulse_observer
```

**注意**: 在 PowerShell 中，JSON 参数需要用单引号包裹，并且内部的双引号需要转义：

```powershell
# PowerShell 示例
python test_skills.py --skill read_file --args '{\"file_path\": \"test_skills.py\"}'
```

#### 方式 2: 从文件读取参数（推荐，更简单）

首先创建一个 JSON 文件，例如 `test_args.json`:

```json
{
  "file_path": "test_skills.py",
  "encoding": "utf-8"
}
```

然后使用 `--args-file` 参数：

```bash
python test_skills.py --skill read_file --args-file test_args.json
```

这种方式避免了在命令行中处理复杂的引号转义问题。

### 4. 指定 skills 目录

如果 skills 不在默认的 `skills` 目录下：

```bash
python test_skills.py --skills-dir custom_skills_dir --list
```

## 示例

### 示例 1: 测试文件读取

```bash
python test_skills.py --skill read_file --args '{"file_path": "test_skills.py"}'
```

### 示例 2: 测试文件写入

```bash
python test_skills.py --skill write_file --args '{"file_path": "桌面/test_output.txt", "content": "这是测试内容"}'
```

### 示例 3: 从文件读取参数测试

创建 `test_write_args.json`:
```json
{
  "file_path": "桌面/test_output.txt",
  "content": "这是测试内容",
  "encoding": "utf-8"
}
```

然后运行:
```bash
python test_skills.py --skill write_file --args-file test_write_args.json
```

### 示例 4: 交互式测试 market_pulse_observer

```bash
python test_skills.py
# 然后输入: market_pulse_observer
# 或输入序号: 3
```

## 功能特性

- ✅ 列出所有可用的 skills 及其参数信息
- ✅ 交互式参数输入（支持默认值）
- ✅ 命令行参数测试
- ✅ 详细的执行结果输出
- ✅ 支持 JSON 格式的参数
- ✅ 自动类型转换（字符串、数字、布尔值等）

## 参数说明

- `--skill, -s`: 要测试的 skill 名称
- `--list, -l`: 列出所有可用的 skills
- `--args, -a`: JSON 格式的参数（直接在命令行传递）
- `--args-file, -f`: 从文件读取 JSON 格式的参数（推荐方式）
- `--skills-dir`: Skills 目录路径（默认: skills）

## 注意事项

1. 确保项目依赖已安装（`pip install -r requirements.txt`）
2. 某些 skills 可能需要额外的依赖（如 `market_pulse_observer` 需要 selenium）
3. 在 PowerShell 中使用 JSON 参数时，注意引号的转义
4. 建议使用交互式模式进行测试，更简单直观
