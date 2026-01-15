# Jessit 项目计划

## 项目概述

Jessit 是一个基于大模型的 Windows 系统桌面工具，是 Anthropic Claude Cowork 的 Windows 版实现。

### 核心功能

1. **托盘 AI Agent**: 运行在 Windows 托盘，通过 `Ctrl+Alt+Z` 快捷键激活
2. **自然语言指令**: 操作本地文件、执行 PowerShell 脚本、整理 Excel、浏览器数据抓取
3. **本地执行能力**: 类似 Claude Code，偏重于执行命令行工具、驱动鼠标键盘
4. **轻量架构**: 先兼容 Skills 技术架构，后期支持 MCP

---

## 技术架构方案

### 技术栈选择

| 组件 | 技术选型 | 理由 |
|------|----------|------|
| 桌面框架 | Python + PyQt6/PySide6 | 生态丰富，快速开发 |
| LLM 集成 | 多模型支持（Claude、OpenAI、Ollama） | 灵活可插拔 |
| 鼠标键盘自动化 | UiPath风格 + Windows API + PyAutoGUI | 多层次支持 |
| 浏览器自动化 | Chrome扩展 + Native Messaging | 可操作已有标签页 |

### 项目结构

```
jessit/
├── src/
│   ├── core/                 # 核心引擎
│   │   ├── agent.py         # Agent主控
│   │   ├── llm.py           # LLM接口抽象
│   │   ├── skill_manager.py # Skills管理器
│   │   └── context.py       # 上下文管理
│   ├── automation/           # 自动化模块
│   │   ├── mouse_keyboard.py # 鼠标键盘控制
│   │   ├── windows_api.py    # Windows API封装
│   │   ├── ui_automation.py  # UI自动化（UIPath风格）
│   │   └── power_shell.py   # PowerShell执行器
│   ├── browser/              # 浏览器模块
│   │   ├── native_messaging.py # Native Messaging
│   │   └── chrome_extension/    # Chrome扩展
│   ├── office/               # Office操作
│   │   └── excel.py         # Excel操作
│   ├── file/                 # 文件操作
│   │   └── file_manager.py  # 文件管理
│   └── ui/                   # UI界面
│       ├── tray.py          # 托盘图标
│       ├── hotkey.py        # 快捷键捕获
│       └── chat_window.py   # 聊天窗口
├── skills/                   # Skills定义目录
│   ├── file_operations/
│   ├── excel_operations/
│   └── browser_automation/
├── extensions/               # Chrome扩展
│   ├── manifest.json
│   ├── background.js
│   └── content.js
├── config/                   # 配置文件
│   └── settings.json
├── tests/                    # 测试
│   └── ...
├── requirements.txt
├── setup.py
└── main.py
```

### 核心模块设计

#### 1. LLM 可插拔架构

```python
class LLMProvider(ABC):
    """LLM提供商抽象基类"""

    @abstractmethod
    async def chat(self, messages: List[Message]) -> str:
        pass

    @abstractmethod
    async def stream_chat(self, messages: List[Message]) -> AsyncIterator[str]:
        pass

class ClaudeProvider(LLMProvider):
    """Claude API 实现"""

class OpenAIProvider(LLMProvider):
    """OpenAI API 实现"""

class OllamaProvider(LLMProvider):
    """Ollama 本地模型实现"""
```

#### 2. Skills 架构兼容

Skills 定义格式（JSON/YAML）:

```json
{
  "name": "read_excel",
  "description": "读取Excel文件内容",
  "parameters": {
    "type": "object",
    "properties": {
      "file_path": {"type": "string"},
      "sheet_name": {"type": "string"}
    },
    "required": ["file_path"]
  },
  "handler": "excel.read"
}
```

#### 3. Chrome 扩展 + Native Messaging

```
Chrome Extension <---> Native Messaging <---> Python Backend
     │                        │                  │
     └─ 读取DOM/执行JS  ──── JSON消息 ────  Agent处理
```

#### 4. 多层次自动化支持

| 层次 | 方案 | 适用场景 |
|------|------|----------|
| 优先 | UIAutomation (UIPath风格) | 基于元素定位，稳定可靠 |
| 中等 | Windows API (SendInput等) | 需要底层控制 |
| 回退 | PyAutoGUI/PyDirectInput | 简单场景，坐标定位 |

---

## 开发阶段规划

### 阶段 1: 基础框架搭建
- [x] 项目初始化
- [x] 托盘图标实现
- [x] 快捷键捕获 (Ctrl+Alt+J)
- [x] 基础聊天窗口UI
- [x] LLM接口抽象和Claude集成

### 阶段 2: 核心功能实现
- [ ] 文件操作能力
- [ ] PowerShell执行器
- [ ] Excel操作能力
- [ ] Skills管理器

### 阶段 3: 自动化能力
- [ ] Windows API封装
- [ ] 鼠标键盘控制
- [ ] UIAutomation集成

### 阶段 4: 浏览器集成
- [ ] Chrome Native Messaging
- [ ] Chrome扩展开发
- [ ] 浏览器数据抓取能力

### 阶段 5: 多LLM支持
- [ ] OpenAI集成
- [ ] Ollama本地模型支持
- [ ] 模型切换配置

### 阶段 6: MCP支持（后期）
- [ ] MCP协议集成
- [ ] MCP服务器管理
- [ ] 与现有Skills架构融合

---

## 关键技术难点

### 1. 快捷键全局捕获
- 使用 Windows `RegisterHotKey` API
- 解决权限问题（需要管理员权限）
- 与其他应用快捷键冲突处理

### 2. Chrome Native Messaging
- 注册表配置
- 异步消息通信
- 扩展安装和更新机制

### 3. UI自动化可靠性
- 元素定位策略
- 动态内容处理
- 反作弊检测规避

### 4. 多LLM统一接口
- 不同API的调用差异
- 流式输出统一处理
- 错误处理和重试机制

---

## 依赖库清单

```
# UI框架
PyQt6>=6.5.0

# LLM SDK
anthropic>=0.18.0
openai>=1.0.0

# 自动化
pyautogui>=0.9.54
pydirectinput>=1.0.4
uiautomation>=2.0.0

# Windows API
pywin32>=306

# 浏览器
selenium>=4.15.0

# Office
openpyxl>=3.1.2
pandas>=2.1.0

# 其他
pyyaml>=6.0
```

---

## 进度跟踪

| 阶段 | 状态 | 完成时间 |
|------|------|----------|
| 阶段 1: 基础框架搭建 | ✅ 已完成 | 2026-01-14 |
| 阶段 2: 核心功能实现 | ⏳ 未开始 | - |
| 阶段 3: 自动化能力 | ⏳ 未开始 | - |
| 阶段 4: 浏览器集成 | ⏳ 未开始 | - |
| 阶段 5: 多LLM支持 | ⏳ 未开始 | - |
| 阶段 6: MCP支持 | ⏳ 未开始 | - |

---

## 备注

- 优先实现 MVP（最小可行产品）
- 采用渐进式开发，每个阶段可独立运行
- 注重错误处理和用户体验
- 考虑性能优化（如缓存、异步执行）
