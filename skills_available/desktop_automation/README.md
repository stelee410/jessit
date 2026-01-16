# 桌面自动化 Skill

## 功能概述

桌面自动化 skill 允许 AI 助手通过截图和鼠标键盘模拟来操作桌面应用程序。当任务需要操作已打开的桌面应用（如微信、浏览器等）时，会自动：

1. 最小化聊天窗口到托盘
2. 截取整个桌面
3. 将截图传给大模型分析
4. 根据大模型的指令执行鼠标和键盘操作
5. 恢复聊天窗口

## 技术实现

### 核心模块

1. **WindowManager** (`window_manager.py`)
   - 管理聊天窗口的显示/隐藏
   - 使用 `pywin32` 控制 Windows 窗口

2. **ScreenshotService** (`screenshot_service.py`)
   - 使用 `mss` 库快速截取桌面
   - 支持转换为 base64 格式供 LLM 使用

3. **MouseKeyboardController** (`mouse_keyboard_controller.py`)
   - 封装 `pyautogui` 和 `pydirectinput`
   - 支持点击、输入、按键、滚动、拖拽等操作

4. **desktop_automation** (`desktop_automation.py`)
   - 主功能模块
   - 协调各个服务完成自动化任务

### LLM 集成

- 扩展了 LLM 接口以支持视觉输入（图片）
- Claude 3+ 模型支持 base64 图片输入
- LLM 分析截图并返回 JSON 格式的操作步骤

## 使用方法

### 基本用法

用户可以直接在聊天中描述需要执行的任务，例如：

- "在微信中发送消息给张三"
- "在浏览器中搜索Python教程"
- "打开记事本并输入一些文字"

### 参数说明

- `task_description` (必需): 任务描述
- `application_name` (可选): 目标应用程序名称
- `max_steps` (可选): 最大操作步骤数，默认10
- `verify_result` (可选): 是否在操作后验证结果，默认false

## 依赖项

已在 `requirements.txt` 中添加：
- `mss>=9.0.1` - 高性能截图
- `Pillow>=10.0.0` - 图片处理

其他依赖（已存在）：
- `pyautogui>=0.9.54` - 鼠标键盘模拟
- `pydirectinput>=1.0.4` - 底层输入模拟
- `pywin32>=306` - Windows API

## 注意事项

1. **LLM 支持**: 需要支持视觉输入的 LLM（如 Claude 3+）
2. **操作安全**: 桌面自动化操作需要用户确认（通过安全检测）
3. **窗口管理**: 确保聊天窗口标题为 "Jessit" 以便正确识别
4. **操作延迟**: 默认操作之间有 0.5 秒延迟，确保操作稳定

## 工作流程

```
用户请求 → Agent识别需要桌面操作 → 调用desktop_automation skill
    ↓
最小化聊天窗口
    ↓
截取桌面
    ↓
调用LLM分析截图
    ↓
解析操作步骤（JSON格式）
    ↓
执行鼠标键盘操作
    ↓
（可选）验证结果
    ↓
恢复聊天窗口
    ↓
返回执行结果
```

## 操作步骤格式

LLM 返回的操作步骤应为 JSON 格式：

```json
{
    "steps": [
        {"type": "click", "x": 100, "y": 200, "button": "left"},
        {"type": "type", "text": "hello world"},
        {"type": "key", "key": "enter"},
        {"type": "scroll", "x": 500, "y": 300, "dy": -100}
    ]
}
```

支持的操作类型：
- `click`: 点击操作
- `type`: 输入文本
- `key`: 按键操作
- `scroll`: 滚动操作
- `drag`: 拖拽操作
