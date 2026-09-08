# -*- coding: utf-8 -*-
"""科学计算器 —— 主程序(PySide6)

运行:
    pip install PySide6
    python main.py

结构:
- FitLabel        自适应缩字的显示标签(表达式 / 结果)
- HistoryPanel    历史记录侧栏(持久化到 AppData/SciCalc/history.json)
- CalculatorWindow 主窗口:工具栏 / 显示区 / 内存行 / 科学面板 / 标准键盘
- main            入口

设计要点:
- 输入始终发生在表达式末尾(计算器惯例),⌫ 做记号级智能删除
- 输入过程中实时预览结果(防抖 120ms);按 = 后进入结果态
- 结果态下:输入数字/常量/函数/左括号 → 开新表达式;输入运算符/后缀 → 以 ans 续算
- 浅色 / 深色两套完整主题,默认浅色,选择持久化
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QFont, QFontMetricsF, QKeyEvent
from PySide6.QtWidgets import (QApplication, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from engine import BACKSPACE_TOKENS, CalcError, evaluate, format_result
import icon as appicon
import theme

# ---------------------------------------------------------------------------
# 小工具
# ---------------------------------------------------------------------------
_OPS = ("+", "−", "×", "÷", "^")
_SUFFIXES = ("!", "²", "³", "⁻¹", "%")
_VALUE_TAILS = (")", "π", "φ", "τ", "e")           # 可接后缀的结尾字符
_VALUE_WORDS = ("ans", "m", "!", "²", "³", "⁻¹", "%")  # 可接后缀的结尾词

_NUM_TAIL_RE = re.compile(r"(\d+\.?\d*|\.\d+)$")   # 末尾数字段
_DIGIT_TAIL_RE = re.compile(r"[\d.]+$")            # 末尾数字/点段


def _balanced(s: str) -> bool:
    """检查括号是否配对平衡"""
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


# ---------------------------------------------------------------------------
# 自适应字号标签
# ---------------------------------------------------------------------------
class FitLabel(QLabel):
    """文本超宽时自动缩小字号(最小到 min_pt),右对齐显示"""

    def __init__(self, base_pt: float, min_pt: float, parent: QWidget | None = None):
        super().__init__(parent)
        self._base_pt = base_pt
        self._min_pt = min_pt
        self._color = "#1D1D1F"
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)

    def set_display(self, text: str, color: str, base_pt: float | None = None) -> None:
        """设置文本 / 颜色 / 基准字号(结果态与输入态字号不同)"""
        self._color = color
        self.setText(text)
        self._fit(base_pt if base_pt is not None else self._base_pt)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt 命名)
        super().resizeEvent(event)
        self._fit()

    def _fit(self, base_pt: float | None = None) -> None:
        text = self.text()
        pt = base_pt if base_pt is not None else self._base_pt
        if text:
            font = QFont()
            font.setPointSizeF(pt)
            metrics = QFontMetricsF(font)
            avail = max(self.width() - 6.0, 40.0)
            while pt > self._min_pt and metrics.horizontalAdvance(text) > avail:
                pt -= 0.5
                font.setPointSizeF(pt)
                metrics = QFontMetricsF(font)
        font = QFont()
        font.setPointSizeF(max(pt, self._min_pt))
        self.setFont(font)
        self.setStyleSheet(f"color: {self._color}; background: transparent;")


# ---------------------------------------------------------------------------
# 历史面板
# ---------------------------------------------------------------------------
class HistoryPanel(QFrame):
    """历史记录侧栏:单击条目把表达式回填到输入区"""

    def __init__(self, on_pick, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("HistPanel")
        self.setFixedWidth(300)
        self._on_pick = on_pick
        self._entries: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 标题行
        head = QWidget()
        head_l = QHBoxLayout(head)
        head_l.setContentsMargins(16, 12, 10, 10)
        title = QLabel("历史记录")
        title.setObjectName("HistTitle")
        self._clear_btn = QPushButton("清空")
        self._clear_btn.setObjectName("ToolBtn")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.clicked.connect(self.clear_all)
        head_l.addWidget(title)
        head_l.addStretch(1)
        head_l.addWidget(self._clear_btn)
        root.addWidget(head)

        line = QFrame()
        line.setObjectName("DividerH")
        line.setFixedHeight(1)
        root.addWidget(line)

        self._list = QListWidget()
        self._list.setObjectName("HistList")
        self._list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.itemClicked.connect(self._handle_click)
        root.addWidget(self._list, 1)

    # ---- 数据 ----
    def load(self, entries: list[dict]) -> None:
        self._entries = entries[-200:]
        self._rebuild()

    def add(self, expr: str, result: str) -> None:
        self._entries.append({"e": expr, "r": result, "t": datetime.now().strftime("%H:%M")})
        if len(self._entries) > 200:
            self._entries = self._entries[-200:]
        self._rebuild()
        self._save()

    def clear_all(self) -> None:
        self._entries.clear()
        self._rebuild()
        self._save()

    @property
    def count(self) -> int:
        return len(self._entries)

    # ---- 内部 ----
    def _handle_click(self, item: QListWidgetItem) -> None:
        expr = item.data(Qt.UserRole)
        if expr:
            self._on_pick(expr)

    def _rebuild(self) -> None:
        self._list.clear()
        for entry in reversed(self._entries):          # 最新在最上
            item = QListWidgetItem()
            item.setData(Qt.UserRole, entry["e"])
            item.setSizeHint(QSize(0, 58))
            self._list.addItem(item)
            self._list.setItemWidget(item, self._make_row(entry))

    def _make_row(self, entry: dict) -> QFrame:
        box = QFrame()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(16, 8, 12, 8)
        lay.setSpacing(2)
        expr = QLabel(entry["e"])
        expr.setObjectName("HistExpr")
        expr.setWordWrap(True)
        row = QHBoxLayout()
        row.setSpacing(6)
        result = QLabel(entry["r"])
        result.setObjectName("HistResult")
        time = QLabel(entry["t"])
        time.setObjectName("HistTime")
        row.addWidget(result)
        row.addStretch(1)
        row.addWidget(time, 0, Qt.AlignBottom)
        lay.addWidget(expr)
        lay.addLayout(row)
        return box

    def _save(self) -> None:
        try:
            path = _history_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._entries, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def _history_path() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(base) / "SciCalc" / "history.json"


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------
class CalculatorWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("科学计算器")
        self.setWindowIcon(appicon.load_app_icon())
        self.setMinimumSize(430, 640)

        # ---- 状态 ----
        self._settings = QSettings("SciCalc", "SciCalc")
        self._theme_name = self._settings.value("theme", theme.DEFAULT_THEME)
        self._angle = self._settings.value("angle", "DEG")
        try:
            self._memory = float(self._settings.value("memory", 0.0))
        except (TypeError, ValueError):
            self._memory = 0.0
        self._expr = ""
        self._result_mode = False     # 按 = 后的结果态
        self._error_mode = False      # 错误提示态
        self._second = False          # 2nd 键状态
        self._last_result = 0.0       # ans
        self._sci_specs: list[dict] = []   # 2nd 可切换的按键
        self._graph_window = None     # 函数图像窗口(按需创建)

        # ---- 布局 ----
        central = QHBoxLayout(self)
        central.setContentsMargins(0, 0, 0, 0)
        central.setSpacing(0)

        main_col = QWidget()
        col = QVBoxLayout(main_col)
        col.setContentsMargins(18, 12, 18, 18)
        col.setSpacing(12)
        central.addWidget(main_col, 1)

        col.addWidget(self._build_toolbar())

        self._expr_label = FitLabel(20, 12)
        self._expr_label.setFixedHeight(34)
        self._result_label = FitLabel(34, 15)
        self._result_label.setFixedHeight(52)
        screen = QVBoxLayout()
        screen.setContentsMargins(4, 6, 4, 2)
        screen.setSpacing(4)
        screen.addWidget(self._expr_label)
        screen.addWidget(self._result_label)
        col.addLayout(screen)

        col.addWidget(self._build_mem_row())
        col.addSpacing(2)
        col.addWidget(self._build_science())
        col.addWidget(self._build_standard())

        divider = QFrame()
        divider.setObjectName("DividerV")
        divider.setFixedWidth(1)
        central.addWidget(divider)

        self._history = HistoryPanel(self._load_expression)
        self._history.load(self._read_history_file())
        self._history.setVisible(self._settings.value("hist_visible", False, type=bool))
        central.addWidget(self._history)

        # 预览防抖
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._refresh_preview)

        # 恢复窗口几何并首次渲染
        geo = self._settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(790, 720)
        self.apply_theme(self._theme_name)
        self._update_display()

    # ------------------------------------------------------------------
    # 构建界面
    # ------------------------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._hist_btn = QPushButton(" 历史")
        self._hist_btn.setObjectName("ToolBtn")
        self._hist_btn.setCursor(Qt.PointingHandCursor)
        self._hist_btn.setIconSize(QSize(16, 16))
        self._hist_btn.clicked.connect(self._toggle_history)
        lay.addWidget(self._hist_btn)

        self._graph_btn = QPushButton(" 图像")
        self._graph_btn.setObjectName("ToolBtn")
        self._graph_btn.setCursor(Qt.PointingHandCursor)
        self._graph_btn.setIconSize(QSize(16, 16))
        self._graph_btn.setToolTip("绘制函数图像(显函数 / 隐函数 / 参数方程 / 极坐标)")
        self._graph_btn.clicked.connect(self._open_graph)
        lay.addWidget(self._graph_btn)

        lay.addStretch(1)

        self._angle_btn = QPushButton(self._angle)
        self._angle_btn.setObjectName("AngleBtn")
        self._angle_btn.setCursor(Qt.PointingHandCursor)
        self._angle_btn.setToolTip("切换角度 / 弧度模式")
        self._angle_btn.clicked.connect(self._toggle_angle)
        lay.addWidget(self._angle_btn)

        self._copy_btn = QPushButton(" 复制")
        self._copy_btn.setObjectName("ToolBtn")
        self._copy_btn.setCursor(Qt.PointingHandCursor)
        self._copy_btn.setIconSize(QSize(16, 16))
        self._copy_btn.clicked.connect(self._copy_result)
        lay.addWidget(self._copy_btn)

        self._theme_btn = QPushButton()
        self._theme_btn.setObjectName("ToolBtn")
        self._theme_btn.setCursor(Qt.PointingHandCursor)
        self._theme_btn.setFixedSize(34, 30)
        self._theme_btn.setIconSize(QSize(16, 16))
        self._theme_btn.setToolTip("切换浅色 / 深色主题")
        self._theme_btn.clicked.connect(self._toggle_theme)
        lay.addWidget(self._theme_btn)
        return bar

    def _build_mem_row(self) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        for label, slot, tip in (
            ("MC", self._memory_clear, "清除内存"),
            ("MR", self._memory_recall, "召回内存值"),
            ("M+", self._memory_add, "当前值加入内存"),
            ("M−", self._memory_sub, "从内存减去当前值"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("btn-mem")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        lay.addStretch(1)
        self._mem_badge = QLabel("")
        self._mem_badge.setObjectName("MemBadge")
        lay.addWidget(self._mem_badge)
        return row

    def _build_science(self) -> QWidget:
        """科学函数面板:5 列 × 4 行,支持 2nd 切换"""
        specs = [
            # (标签, 插入文本, 2nd 标签, 2nd 插入文本)
            ("2nd", None, None, None),
            ("sin", "sin(", "sin⁻¹", "asin("),
            ("cos", "cos(", "cos⁻¹", "acos("),
            ("tan", "tan(", "tan⁻¹", "atan("),
            ("√(", "√(", "∛(", "∛("),
            ("ln", "ln(", None, None),
            ("log", "log(", "10ˣ", "10^("),
            ("(", "(", None, None),
            (")", ")", None, None),
            ("^", "^", None, None),
            ("x²", "²", "x³", "³"),
            ("!", "!", None, None),
            ("1/x", "⁻¹", None, None),
            ("|x|", "abs(", None, None),
            ("mod", "mod", None, None),
            ("π", "π", None, None),
            ("e", "e", None, None),
            ("ans", "ans", None, None),
            ("eˣ", "exp(", None, None),
            ("log₂", "log₂(", None, None),
        ]
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(7)
        for i, spec in enumerate(specs):
            r, c = divmod(i, 5)
            btn = QPushButton(spec[0])
            btn.setObjectName("btn-2nd" if spec[1] is None else "btn-fn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(42)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(btn, r, c)
            grid.setColumnStretch(c, 1)
            if spec[1] is None:                       # 2nd 切换键
                btn.setCheckable(True)
                btn.toggled.connect(self._toggle_second)
            else:
                btn.clicked.connect(
                    lambda _=False, s=spec: self._insert(s[3] if self._second and s[3] else s[1])
                )
                if spec[2]:                           # 有 2nd 功能,记录以便切换标签
                    self._sci_specs.append({"btn": btn, "spec": spec})
        wrap = QWidget()
        wrap.setLayout(grid)
        return wrap

    def _build_standard(self) -> QWidget:
        """标准键盘:5 列 × 4 行"""
        keys = [
            ("C", "btn-danger", self._clear),
            ("⌫", "btn-fn", self._backspace),
            ("%", "btn-op", lambda: self._insert("%")),
            ("÷", "btn-op", lambda: self._insert("÷")),
            ("7", "btn-num", lambda: self._insert("7")),
            ("8", "btn-num", lambda: self._insert("8")),
            ("9", "btn-num", lambda: self._insert("9")),
            ("×", "btn-op", lambda: self._insert("×")),
            ("4", "btn-num", lambda: self._insert("4")),
            ("5", "btn-num", lambda: self._insert("5")),
            ("6", "btn-num", lambda: self._insert("6")),
            ("−", "btn-op", lambda: self._insert("−")),
            ("1", "btn-num", lambda: self._insert("1")),
            ("2", "btn-num", lambda: self._insert("2")),
            ("3", "btn-num", lambda: self._insert("3")),
            ("+", "btn-op", lambda: self._insert("+")),
            ("±", "btn-fn", self._plusminus),
            ("0", "btn-num", lambda: self._insert("0")),
            (".", "btn-num", lambda: self._insert(".")),
            ("=", "btn-eq", self._equals),
        ]
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(9)
        for i, (label, obj, slot) in enumerate(keys):
            r, c = divmod(i, 4)
            btn = QPushButton(label)
            btn.setObjectName(obj)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(56)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(slot)
            grid.addWidget(btn, r, c)
            grid.setColumnStretch(c, 1)
        wrap = QWidget()
        wrap.setLayout(grid)
        return wrap

    # ------------------------------------------------------------------
    # 显示
    # ------------------------------------------------------------------
    def _update_display(self) -> None:
        if self._error_mode:
            self._expr_label.set_display(self._expr, theme.THEMES[self._theme_name]["text2"], 14)
            # 错误信息已在 _show_error 中设置
            return
        if self._result_mode:
            self._expr_label.set_display(self._expr, theme.THEMES[self._theme_name]["text2"], 13)
            self._result_label.set_display(self._result_text, theme.THEMES[self._theme_name]["text"], 34)
        else:
            self._expr_label.set_display(self._expr or " ", theme.THEMES[self._theme_name]["text"], 20)
            self._schedule_preview()

    def _schedule_preview(self) -> None:
        self._preview_timer.start()

    def _refresh_preview(self) -> None:
        """输入过程中的实时预览(失败时静默)"""
        if self._result_mode or self._error_mode:
            return
        expr = self._expr.strip()
        if not expr:
            self._result_label.set_display(" ", theme.THEMES[self._theme_name]["text3"], 34)
            return
        try:
            value = evaluate(expr, angle=self._angle, ans=self._last_result, mem=self._memory)
            self._result_label.set_display(format_result(value),
                                           theme.THEMES[self._theme_name]["text3"], 30)
        except CalcError:
            self._result_label.set_display(" ", theme.THEMES[self._theme_name]["text3"], 30)

    def _show_error(self, msg: str) -> None:
        self._error_mode = True
        self._result_label.set_display(msg, theme.THEMES[self._theme_name]["error"], 22)

    def _clear_error(self) -> None:
        if self._error_mode:
            self._error_mode = False
            self._update_display()

    # ------------------------------------------------------------------
    # 输入逻辑
    # ------------------------------------------------------------------
    def _insert(self, text: str) -> None:
        """把一段文本插入表达式末尾,带连按防呆"""
        self._clear_error()
        if self._result_mode:
            # 结果态:值类输入开新式,运算类以 ans 续算
            value_starts = (
                text[:1].isdigit()
                or text[:1] == "."
                or text in ("(", "π", "e", "φ", "τ")
                or (text.endswith("(") and text[0].isalpha())
            )
            self._expr = "" if value_starts else "ans"
            self._result_mode = False

        expr = self._expr
        last = expr[-1] if expr else ""

        # 运算符防呆:连按替换;运算符后的 − 视为负号;不允许的开头/位置直接忽略
        if text in _OPS:
            if last in _OPS:
                if text == "−" and last in ("+", "×", "÷", "^"):
                    pass                       # 负号
                else:
                    expr = expr[:-1]           # 连按 → 替换
            elif last == "" and text != "−":
                return                         # 空表达式不允许非负号运算符开头
            elif last == "(" and text != "−":
                return                         # "(×" 不合法
        elif text == ".":
            seg = _DIGIT_TAIL_RE.search(expr)
            seg_text = seg.group() if seg else ""
            if seg_text:
                if "." in seg_text:
                    return                     # 数字段里已有小数点
                text = "."
            else:
                if last in _VALUE_TAILS or expr.endswith(_VALUE_WORDS) or expr.endswith("mod"):
                    return
                text = "0."
        elif text in _SUFFIXES:
            ok = last.isdigit() or last in _VALUE_TAILS or expr.endswith(_VALUE_WORDS)
            if ok and expr.endswith("mod"):
                ok = False
            if not ok:
                return
        elif text == ")":
            if last in _OPS or last == "(" or not _balanced(expr + text):
                return
        elif text == "mod":
            if last == "" or last in _OPS or last == "(":
                return

        self._expr = expr + text
        self._update_display()

    def _backspace(self) -> None:
        """智能退格:函数名/常量整体删除,数字逐位删除"""
        self._clear_error()
        if self._result_mode:
            self._result_mode = False
            self._update_display()
            return
        expr = self._expr
        for token in BACKSPACE_TOKENS:             # 已按长度降序
            if token and expr.endswith(token):
                expr = expr[: -len(token)]
                break
        else:
            expr = expr[:-1] if expr else ""
        self._expr = expr
        self._update_display()

    def _clear(self) -> None:
        self._expr = ""
        self._result_mode = False
        self._error_mode = False
        self._update_display()

    def _plusminus(self) -> None:
        """± :切换末尾数字符号;其余情况对整个表达式取负/还原"""
        self._clear_error()
        if self._result_mode:
            self._expr = "−ans"
            self._result_mode = False
            self._update_display()
            return
        expr = self._expr
        m = _NUM_TAIL_RE.search(expr)
        if m:
            i = m.start()
            if i > 0 and expr[i - 1] == "−" and (i - 1 == 0 or expr[i - 2] in "+−×÷^("):
                expr = expr[: i - 1] + m.group()      # 已是负数 → 去掉负号
            else:
                expr = expr[:i] + "−" + m.group()     # 数字前插入负号
        elif expr.startswith("−") and _balanced(expr[1:]):
            expr = expr[1:]                           # 还原整体负号
        elif expr == "":
            expr = "−"
        else:
            expr = "−" + expr                         # 整体取负
        self._expr = expr
        self._update_display()

    def _equals(self) -> None:
        if self._error_mode or self._result_mode:
            return
        expr = self._expr.strip()
        if not expr:
            return
        try:
            value = evaluate(expr, angle=self._angle, ans=self._last_result, mem=self._memory)
        except CalcError as err:
            self._show_error(err.msg if hasattr(err, "msg") else str(err))
            return
        self._last_result = value
        self._result_text = format_result(value)
        self._history.add(expr, self._result_text)
        self._result_mode = True
        self._update_display()

    def _load_expression(self, expr: str) -> None:
        """从历史回填表达式"""
        self._clear_error()
        self._expr = expr
        self._result_mode = False
        self._update_display()

    # ------------------------------------------------------------------
    # 内存
    # ------------------------------------------------------------------
    def _current_value(self) -> float | None:
        """当前可参与内存运算的值:结果态取 ans;输入态尝试求值"""
        if self._result_mode:
            return self._last_result
        expr = self._expr.strip()
        if not expr:
            return None
        try:
            return evaluate(expr, angle=self._angle, ans=self._last_result, mem=self._memory)
        except CalcError:
            return None

    def _memory_add(self) -> None:
        value = self._current_value()
        if value is not None:
            self._memory += value
            self._after_memory_change()

    def _memory_sub(self) -> None:
        value = self._current_value()
        if value is not None:
            self._memory -= value
            self._after_memory_change()

    def _memory_recall(self) -> None:
        self._clear_error()
        if self._result_mode or self._expr:
            self._insert("×m")
        else:
            self._insert("m")

    def _memory_clear(self) -> None:
        self._memory = 0.0
        self._after_memory_change()

    def _after_memory_change(self) -> None:
        self._settings.setValue("memory", self._memory)
        self._mem_badge.setText(
            "" if self._memory == 0 else f"M = {format_result(self._memory)}"
        )
        self._schedule_preview()

    # ------------------------------------------------------------------
    # 工具栏动作
    # ------------------------------------------------------------------
    def _toggle_history(self) -> None:
        visible = not self._history.isVisible()
        self._history.setVisible(visible)
        self._settings.setValue("hist_visible", visible)

    def _open_graph(self) -> None:
        """打开(或前置)函数图像窗口"""
        if self._graph_window is None:
            from graph_window import GraphWindow      # 延迟导入,加快启动
            self._graph_window = GraphWindow(self._theme_name)
        self._graph_window.show()
        self._graph_window.raise_()
        self._graph_window.activateWindow()

    def _toggle_angle(self) -> None:
        self._angle = "RAD" if self._angle == "DEG" else "DEG"
        self._settings.setValue("angle", self._angle)
        self._angle_btn.setText(self._angle)
        if self._result_mode:
            # 角度模式改变后重算当前表达式
            try:
                value = evaluate(self._expr, angle=self._angle,
                                 ans=self._last_result, mem=self._memory)
                self._last_result = value
                self._result_text = format_result(value)
            except CalcError:
                self._result_mode = False
        self._update_display()

    def _toggle_theme(self) -> None:
        self.apply_theme("dark" if self._theme_name == "light" else "light")

    def _toggle_second(self, checked: bool) -> None:
        """2nd 状态切换:更新科学键标签(插入文本在点击时按状态动态决定)"""
        self._second = checked
        for item in self._sci_specs:
            btn, spec = item["btn"], item["spec"]
            btn.setText(spec[2] if checked and spec[2] else spec[0])

    def apply_theme(self, name: str) -> None:
        self._theme_name = name if name in theme.THEMES else theme.DEFAULT_THEME
        QApplication.instance().setStyleSheet(theme.build_qss(self._theme_name))
        self._settings.setValue("theme", self._theme_name)
        # 主题变化后刷新随主题着色的图标与文字
        t = theme.THEMES[self._theme_name]
        self._hist_btn.setIcon(appicon.make_glyph_icon("history", t["text2"]))
        self._graph_btn.setIcon(appicon.make_glyph_icon("graph", t["text2"]))
        self._copy_btn.setIcon(appicon.make_glyph_icon("copy", t["text2"]))
        self._theme_btn.setIcon(appicon.make_glyph_icon("theme", t["text2"]))
        self._angle_btn.setText(self._angle)
        if self._graph_window is not None:
            self._graph_window.apply_theme(self._theme_name)
        self._after_memory_change()
        self._update_display()

    def _copy_result(self) -> None:
        """复制当前结果(错误态忽略;无结果时复制表达式)"""
        text = ""
        if not self._error_mode and self._result_mode:
            text = self._result_text
        elif not self._error_mode:
            text = self._result_label.text().strip()
        if not text or text == " ":
            text = self._expr
        if text:
            QApplication.clipboard().setText(text)

    # ------------------------------------------------------------------
    # 历史持久化
    # ------------------------------------------------------------------
    @staticmethod
    def _read_history_file() -> list[dict]:
        try:
            path = _history_path()
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [e for e in data if isinstance(e, dict) and "e" in e and "r" in e]
        except (OSError, ValueError):
            pass
        return []

    # ------------------------------------------------------------------
    # 键盘
    # ------------------------------------------------------------------
    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        key, text = event.key(), event.text()
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._equals()
        elif key == Qt.Key_Backspace:
            self._backspace()
        elif key in (Qt.Key_Escape, Qt.Key_Delete):
            self._clear()
        elif key == Qt.Key_Equal:
            self._equals()
        elif event.modifiers() & Qt.ControlModifier and key == Qt.Key_C:
            self._copy_result()
        elif event.modifiers() & Qt.ControlModifier:
            super().keyPressEvent(event)          # 放行其他系统快捷键
        elif text:
            mapped = {"*": "×", "/": "÷", "-": "−", "+": "+", "^": "^",
                      "(": "(", ")": ")", "%": "%", ".": ".", "!": "!"}
            if text.isdigit() or text in mapped:
                self._insert(text if text.isdigit() else mapped[text])
            elif text.isalpha():
                self._insert(text.lower())        # 支持手输函数名 / ans / m
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # 退出
    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:  # noqa: N802
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("memory", self._memory)
        self._settings.setValue("hist_visible", self._history.isVisible())
        if self._graph_window is not None:
            self._graph_window.close()          # 主窗口关闭时一并关闭图像窗口
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("科学计算器")
    font = QFont("Microsoft YaHei UI", 9)
    font.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(font)
    window = CalculatorWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
