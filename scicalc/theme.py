# -*- coding: utf-8 -*-
"""科学计算器 —— 主题(浅色 / 深色两套完整设计,默认浅色)

设计原则:极简扁平、简洁克制、留白与层次;仅用一种强调色,
按键只靠背景明度区分层级(数字键浮起 → 功能键凹下 → 等号键实心强调色)。
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 色板
# ---------------------------------------------------------------------------
THEMES: dict[str, dict[str, str]] = {
    "light": {
        # 基础
        "bg":       "#F5F5F7",   # 窗口背景
        "divider":  "#E7E7EC",   # 分隔线
        "text":     "#1D1D1F",   # 主文字
        "text2":    "#6E6E73",   # 次级文字
        "text3":    "#AEAEB2",   # 弱化文字(预览)
        "accent":   "#0071E3",   # 强调色
        "danger":   "#E8352A",   # 清除键文字
        "error":    "#D70015",   # 错误信息
        # 按键
        "num_bg":     "#FFFFFF",
        "num_hover":  "#F4F4F7",
        "num_press":  "#EBEBEF",
        "num_text":   "#1D1D1F",
        "fn_bg":      "#F0F0F4",
        "fn_hover":   "#E8E8EE",
        "fn_press":   "#DFDFE6",
        "fn_text":    "#3A3A3C",
        "op_bg":      "#EAF2FC",
        "op_hover":   "#DEEBFA",
        "op_press":   "#D0E2F7",
        "op_text":    "#0071E3",
        "eq_bg":      "#0071E3",
        "eq_hover":   "#1B84F0",
        "eq_press":   "#0062C4",
        "eq_text":    "#FFFFFF",
        # 历史面板
        "hist_bg":    "#FCFCFD",
        "hist_hover": "#F1F1F5",
        "scroll":     "#C9C9CE",
    },
    "dark": {
        "bg":       "#1C1C1E",
        "divider":  "#363638",
        "text":     "#F5F5F7",
        "text2":    "#A1A1A6",
        "text3":    "#6E6E73",
        "accent":   "#0A84FF",
        "danger":   "#FF6961",
        "error":    "#FF453A",
        "num_bg":     "#333336",
        "num_hover":  "#3D3D40",
        "num_press":  "#47474B",
        "num_text":   "#F5F5F7",
        "fn_bg":      "#29292B",
        "fn_hover":   "#323235",
        "fn_press":   "#3B3B3E",
        "fn_text":    "#C7C7CC",
        "op_bg":      "#1C2A3E",
        "op_hover":   "#223349",
        "op_press":   "#283C55",
        "op_text":    "#0A84FF",
        "eq_bg":      "#0A84FF",
        "eq_hover":   "#3395FF",
        "eq_press":   "#0069DB",
        "eq_text":    "#FFFFFF",
        "hist_bg":    "#232325",
        "hist_hover": "#2C2C2E",
        "scroll":     "#4A4A4D",
    },
}

DEFAULT_THEME = "light"
FONT_FAMILY = '"Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei UI", sans-serif'


# ---------------------------------------------------------------------------
# 样式表
# ---------------------------------------------------------------------------
def build_qss(name: str = DEFAULT_THEME) -> str:
    """根据主题名生成全局 QSS"""
    c = THEMES.get(name, THEMES[DEFAULT_THEME])
    return f"""
/* ---------- 全局 ---------- */
QWidget {{
    background: {c['bg']};
    color: {c['text']};
    font-family: {FONT_FAMILY};
}}
QLabel {{ background: transparent; }}

/* ---------- 显示区 ---------- */
#ScreenExpr   {{ color: {c['text']}; }}
#ScreenResult {{ color: {c['text']}; }}
#MemBadge     {{ color: {c['text2']}; font-size: 12px; }}

/* ---------- 按键通用 ---------- */
QPushButton {{
    border: none;
    border-radius: 12px;
    font-size: 16px;
    padding: 0;
}}
QPushButton:flat {{ outline: none; }}

#btn-num {{
    background: {c['num_bg']};   color: {c['num_text']};  font-size: 19px;
}}
#btn-num:hover   {{ background: {c['num_hover']}; }}
#btn-num:pressed {{ background: {c['num_press']}; }}

#btn-fn {{
    background: {c['fn_bg']};    color: {c['fn_text']};   font-size: 14px;
}}
#btn-fn:hover   {{ background: {c['fn_hover']}; }}
#btn-fn:pressed {{ background: {c['fn_press']}; }}

#btn-op {{
    background: {c['op_bg']};    color: {c['op_text']};   font-size: 20px;
}}
#btn-op:hover   {{ background: {c['op_hover']}; }}
#btn-op:pressed {{ background: {c['op_press']}; }}

#btn-eq {{
    background: {c['eq_bg']};    color: {c['eq_text']};   font-size: 22px;
}}
#btn-eq:hover   {{ background: {c['eq_hover']}; }}
#btn-eq:pressed {{ background: {c['eq_press']}; }}

#btn-danger {{
    background: {c['fn_bg']};    color: {c['danger']};    font-size: 17px;
}}
#btn-danger:hover   {{ background: {c['fn_hover']}; }}
#btn-danger:pressed {{ background: {c['fn_press']}; }}

/* 2nd 键:选中时用强调色点亮 */
#btn-2nd {{
    background: {c['fn_bg']};    color: {c['fn_text']};   font-size: 14px;
}}
#btn-2nd:hover   {{ background: {c['fn_hover']}; }}
#btn-2nd:checked {{ background: {c['op_bg']}; color: {c['accent']}; }}

/* 内存键:更小更轻 */
#btn-mem {{
    background: transparent;     color: {c['text2']};     font-size: 12px;
    border-radius: 8px;
}}
#btn-mem:hover   {{ background: {c['fn_bg']}; color: {c['text']}; }}
#btn-mem:pressed {{ background: {c['fn_press']}; }}

/* ---------- 顶部工具栏 ---------- */
#ToolBtn {{
    background: transparent;     color: {c['text2']};     font-size: 13px;
    border-radius: 8px;          padding: 5px 10px;
}}
#ToolBtn:hover   {{ background: {c['fn_bg']}; color: {c['text']}; }}
#ToolBtn:pressed {{ background: {c['fn_press']}; }}

#AngleBtn {{
    background: {c['op_bg']};    color: {c['accent']};    font-size: 12px;
    font-weight: 600;            border-radius: 9px;      padding: 4px 11px;
}}
#AngleBtn:hover   {{ background: {c['op_hover']}; }}
#AngleBtn:pressed {{ background: {c['op_press']}; }}

/* ---------- 历史面板 ---------- */
#HistPanel {{ background: {c['hist_bg']}; }}
#HistTitle {{ color: {c['text2']}; font-size: 13px; background: transparent; }}
#HistList {{
    background: transparent;     border: none;            outline: none;
}}
#HistList::item {{
    border-bottom: 1px solid {c['divider']};
    padding: 1px;
}}
#HistList::item:hover  {{ background: {c['hist_hover']}; }}
#HistList::item:selected {{ background: {c['hist_hover']}; }}

#HistExpr   {{ color: {c['text2']};  font-size: 12px; }}
#HistResult {{ color: {c['text']};   font-size: 16px; }}
#HistTime   {{ color: {c['text3']};  font-size: 10px; }}

/* ---------- 分隔线 ---------- */
#DividerV, #DividerH {{ background: {c['divider']}; }}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{
    background: transparent;     width: 8px;              margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {c['scroll']};   border-radius: 4px;      min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {c['text3']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""
