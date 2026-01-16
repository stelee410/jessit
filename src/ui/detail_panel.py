"""
详情面板组件模块
"""

import json
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QWidget,
    QFrame,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QScrollArea,
    QSizePolicy,
)
from .styles import (
    get_detail_panel_style,
    get_detail_text_edit_style,
    get_detail_label_style,
    get_detail_title_style,
    get_scroll_area_style,
)


class DetailPanel(QFrame):
    """详情面板组件"""
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.current_progress_info: Dict[str, Any] = {
            "analysis": "",
            "plan": [],
            "execution_steps": [],
            "final_result": "",
        }
        self._init_ui()
    
    def _init_ui(self) -> None:
        """初始化UI"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet(get_detail_panel_style())
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("AI处理详情")
        title_label.setStyleSheet(get_detail_title_style())
        layout.addWidget(title_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(get_scroll_area_style())
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # 任务分析区域
        self.analysis_label = QLabel("任务分析：")
        self.analysis_label.setStyleSheet(get_detail_label_style())
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMaximumHeight(100)
        self.analysis_text.setStyleSheet(get_detail_text_edit_style())
        content_layout.addWidget(self.analysis_label)
        content_layout.addWidget(self.analysis_text)
        
        # 计划区域
        self.plan_label = QLabel("执行计划：")
        self.plan_label.setStyleSheet(get_detail_label_style())
        self.plan_text = QTextEdit()
        self.plan_text.setReadOnly(True)
        self.plan_text.setMaximumHeight(150)
        self.plan_text.setStyleSheet(get_detail_text_edit_style())
        content_layout.addWidget(self.plan_label)
        content_layout.addWidget(self.plan_text)
        
        # 实施步骤区域
        self.steps_label = QLabel("实施步骤：")
        self.steps_label.setStyleSheet(get_detail_label_style())
        self.steps_text = QTextEdit()
        self.steps_text.setReadOnly(True)
        self.steps_text.setMaximumHeight(200)
        self.steps_text.setStyleSheet(get_detail_text_edit_style())
        content_layout.addWidget(self.steps_label)
        content_layout.addWidget(self.steps_text)
        
        # 结果区域
        self.result_label = QLabel("最终结果：")
        self.result_label.setStyleSheet(get_detail_label_style())
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setMaximumHeight(100)
        self.result_text.setStyleSheet(get_detail_text_edit_style())
        content_layout.addWidget(self.result_label)
        content_layout.addWidget(self.result_text)
        
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
    
    def update_progress_info(self, progress_info: Dict[str, Any]) -> None:
        """
        更新进度信息
        
        Args:
            progress_info: 进度信息字典
        """
        self.current_progress_info = progress_info
        self._update_display()
    
    def _update_display(self) -> None:
        """更新显示内容"""
        # 更新任务分析
        analysis = self.current_progress_info.get("analysis", "")
        if analysis:
            self.analysis_text.setPlainText(analysis)
        else:
            self.analysis_text.setPlainText("正在分析任务...")
        
        # 更新计划
        plan = self.current_progress_info.get("plan", [])
        if plan:
            plan_text = ""
            for i, step in enumerate(plan, 1):
                tool_name = step.get("tool_name", "未知工具")
                tool_args = step.get("tool_args", {})
                plan_text += f"步骤 {i}: 调用工具 {tool_name}\n"
                plan_text += f"  参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}\n\n"
            self.plan_text.setPlainText(plan_text)
        else:
            self.plan_text.setPlainText("正在制定执行计划...")
        
        # 更新实施步骤
        steps = self.current_progress_info.get("execution_steps", [])
        if steps:
            steps_text = ""
            for i, step in enumerate(steps, 1):
                tool_name = step.get("tool_name", "未知工具")
                tool_args = step.get("tool_args", {})
                result = step.get("result", {})
                status = step.get("status", "unknown")
                status_text = "✓ 成功" if status == "completed" else "✗ 失败"
                
                steps_text += f"步骤 {i}: {tool_name} - {status_text}\n"
                steps_text += f"  参数: {json.dumps(tool_args, ensure_ascii=False, indent=2)}\n"
                steps_text += f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}\n\n"
            self.steps_text.setPlainText(steps_text)
        else:
            self.steps_text.setPlainText("等待执行步骤...")
        
        # 更新最终结果
        result = self.current_progress_info.get("final_result", "")
        if result:
            self.result_text.setPlainText(result)
        else:
            self.result_text.setPlainText("正在处理，请稍候...")
