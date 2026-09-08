# -*- coding: utf-8 -*-
"""科学计算器 —— 函数图像窗口

- PlotCanvas :画布(网格 / 坐标轴 / 曲线 / 图例),滚轮缩放、拖拽平移、双击复位
- GraphWindow:表达式输入区 + 画布 + 状态栏

输入区每行一条曲线,类型由表达式自动识别(显函数 / 隐函数 / 参数方程 / 极坐标),
输入后自动重绘(防抖 400ms)。
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QPainter, QPainterPath,
                           QPen)
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QMenu, QPlainTextEdit,
                               QPushButton, QVBoxLayout, QWidget)

import icon as appicon
import plot
import theme
from plot import CurveSpec, SampleResult, Viewport

# 缩放步进(滚轮每格)
ZOOM_STEP = 0.82
# 输入变化到重绘的防抖时间
REPLOT_DELAY_MS = 400


# ---------------------------------------------------------------------------
# 画布
# ---------------------------------------------------------------------------
class PlotCanvas(QWidget):
    """函数图像画布"""

    coords_changed = Signal(float, float)      # 鼠标所在位置的数学坐标

    def __init__(self, theme_name: str = theme.DEFAULT_THEME, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PlotCanvas")
        self.setMouseTracking(True)
        self.setMinimumSize(360, 260)

        self._theme_name = theme_name
        self._view = Viewport(-10.0, 10.0, -6.0, 6.0)
        self._curves: list[CurveSpec] = []
        self._samples: list[SampleResult] = []
        self._drag_origin: QPointF | None = None
        self._drag_view: Viewport | None = None

        # 精细重采样防抖(拖拽 / 缩放过程中先用低精度保证流畅)
        self._refine_timer = QTimer(self)
        self._refine_timer.setSingleShot(True)
        self._refine_timer.setInterval(150)
        self._refine_timer.timeout.connect(lambda: self._resample("full"))

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    @property
    def view(self) -> Viewport:
        return self._view

    def set_curves(self, curves: list[CurveSpec]) -> None:
        self._curves = curves
        self._resample("full")

    def set_theme(self, name: str) -> None:
        self._theme_name = name
        self.update()

    def reset_view(self) -> None:
        """恢复默认视口(并按画布比例校正纵横比)"""
        self._view = Viewport(-10.0, 10.0, -6.0, 6.0).with_aspect(self.width(), self.height())
        self._resample("full")

    # ------------------------------------------------------------------
    # 采样
    # ------------------------------------------------------------------
    def _resample(self, quality: str = "full") -> None:
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return
        samples: list[SampleResult] = []
        for curve in self._curves:
            try:
                samples.append(plot.sample_curve(curve, self._view, w, h, quality))
            except plot.CalcError:
                samples.append(SampleResult(kind=curve.kind))
        self._samples = samples
        self.update()

    # ------------------------------------------------------------------
    # 绘制
    # ------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        colors = theme.THEMES[self._theme_name]
        w, h = self.width(), self.height()

        painter.fillRect(self.rect(), QColor(str(colors["plot_bg"])))
        self._draw_grid(painter, w, h, colors)
        self._draw_curves(painter, w, h, colors)
        self._draw_legend(painter, w, colors)
        painter.end()

    def _draw_grid(self, painter: QPainter, w: int, h: int, colors: dict) -> None:
        """网格线、坐标轴与刻度数字"""
        view = self._view
        # 两个方向都用约 70px 一个网格,视觉密度一致
        x_step = plot.nice_step(view.width, max(4, w // 70))
        y_step = plot.nice_step(view.height, max(4, h // 70))

        # 网格
        painter.setPen(QPen(QColor(str(colors["grid"])), 1))
        for xv in plot.tick_values(view.x_min, view.x_max, x_step):
            px, _ = view.math_to_px(xv, 0.0, w, h)
            painter.drawLine(QPointF(px, 0.0), QPointF(px, float(h)))
        for yv in plot.tick_values(view.y_min, view.y_max, y_step):
            _, py = view.math_to_px(0.0, yv, w, h)
            painter.drawLine(QPointF(0.0, py), QPointF(float(w), py))

        # 坐标轴(仅当原点在视口内时绘制)
        axis_pen = QPen(QColor(str(colors["axis"])), 1.4)
        painter.setPen(axis_pen)
        y0_px: float | None = None
        x0_px: float | None = None
        if view.y_min <= 0.0 <= view.y_max:
            _, y0_px = view.math_to_px(0.0, 0.0, w, h)
            painter.drawLine(QPointF(0.0, y0_px), QPointF(float(w), y0_px))
        if view.x_min <= 0.0 <= view.x_max:
            x0_px, _ = view.math_to_px(0.0, 0.0, w, h)
            painter.drawLine(QPointF(x0_px, 0.0), QPointF(x0_px, float(h)))

        # 刻度数字
        font = QFont()
        font.setPointSizeF(8.5)
        painter.setFont(font)
        painter.setPen(QPen(QColor(str(colors["tick_text"]))))

        x_text_y = (y0_px + 4) if y0_px is not None else (h - 16)
        for xv in plot.tick_values(view.x_min, view.x_max, x_step):
            if xv == 0.0:
                continue
            px, _ = view.math_to_px(xv, 0.0, w, h)
            painter.drawText(QRectF(px - 40, x_text_y, 80, 14),
                             Qt.AlignHCenter | Qt.AlignTop, plot.format_tick(xv, x_step))

        for yv in plot.tick_values(view.y_min, view.y_max, y_step):
            if yv == 0.0:
                continue
            _, py = view.math_to_px(0.0, yv, w, h)
            if x0_px is not None and x0_px > 90:
                rect = QRectF(x0_px - 72, py - 9, 66, 18)
                align = Qt.AlignRight | Qt.AlignVCenter
            else:
                rect = QRectF((x0_px + 8) if x0_px is not None else 8, py - 9, 66, 18)
                align = Qt.AlignLeft | Qt.AlignVCenter
            painter.drawText(rect, align, plot.format_tick(yv, y_step))

        # 原点
        if x0_px is not None and y0_px is not None:
            painter.drawText(QRectF(x0_px + 5, y0_px + 3, 24, 14),
                             Qt.AlignLeft | Qt.AlignTop, "0")

    def _draw_curves(self, painter: QPainter, w: int, h: int, colors: dict) -> None:
        """绘制所有采样结果"""
        palette = colors["curve_colors"]
        view = self._view
        for index, sample in enumerate(self._samples):
            color = QColor(str(palette[index % len(palette)]))
            pen = QPen(color)
            pen.setWidthF(1.8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            path = QPainterPath()
            has_content = False
            if sample.polylines:
                for line in sample.polylines:
                    if len(line) < 2:
                        continue
                    px, py = view.math_to_px(line[0][0], line[0][1], w, h)
                    path.moveTo(px, py)
                    for x, y in line[1:]:
                        px, py = view.math_to_px(x, y, w, h)
                        path.lineTo(px, py)
                    has_content = True
            if sample.segments:
                for x1, y1, x2, y2 in sample.segments:
                    px1, py1 = view.math_to_px(x1, y1, w, h)
                    px2, py2 = view.math_to_px(x2, y2, w, h)
                    path.moveTo(px1, py1)
                    path.lineTo(px2, py2)
                has_content = True
            if has_content:
                painter.drawPath(path)

    def _draw_legend(self, painter: QPainter, w: int, colors: dict) -> None:
        """右上角图例"""
        if not self._curves:
            return
        font = QFont()
        font.setPointSizeF(9)
        painter.setFont(font)
        metrics = QFontMetricsF(font)

        entries: list[tuple[str, str]] = []
        palette = colors["curve_colors"]
        for index, curve in enumerate(self._curves):
            label = curve.label if len(curve.label) <= 30 else curve.label[:29] + "…"
            entries.append((str(palette[index % len(palette)]), label))

        width = max(metrics.horizontalAdvance(label) for _, label in entries) + 38
        height = len(entries) * 18 + 12
        x0 = max(8.0, w - width - 14.0)
        y0 = 12.0

        background = QColor(str(colors["plot_bg"]))
        background.setAlpha(225)
        painter.setPen(QPen(QColor(str(colors["grid"])), 1))
        painter.setBrush(background)
        painter.drawRoundedRect(QRectF(x0, y0, width, height), 8, 8)

        for index, (color, label) in enumerate(entries):
            cy = y0 + 6 + index * 18 + 9
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(x0 + 10, cy - 3, 14, 6), 3, 3)
            painter.setPen(QPen(QColor(str(colors["text"]))))
            painter.drawText(QRectF(x0 + 30, cy - 9, width - 36, 18),
                             Qt.AlignLeft | Qt.AlignVCenter, label)

    # ------------------------------------------------------------------
    # 交互
    # ------------------------------------------------------------------
    def wheelEvent(self, event) -> None:  # noqa: N802
        steps = event.angleDelta().y()
        if steps == 0:
            event.ignore()
            return
        factor = ZOOM_STEP if steps > 0 else 1.0 / ZOOM_STEP
        w, h = self.width(), self.height()
        cx, cy = self._view.px_to_math(event.position().x(), event.position().y(), w, h)
        self._view = self._view.scaled(factor, cx, cy).with_aspect(w, h)
        self._resample("fast")
        self._refine_timer.start()
        event.accept()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.position()
            self._drag_view = self._view
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        w, h = self.width(), self.height()
        mx, my = self._view.px_to_math(pos.x(), pos.y(), w, h)
        self.coords_changed.emit(mx, my)
        if self._drag_origin is not None and self._drag_view is not None and w > 0 and h > 0:
            dx = (pos.x() - self._drag_origin.x()) / w * self._drag_view.width
            dy = (pos.y() - self._drag_origin.y()) / h * self._drag_view.height
            self._view = self._drag_view.translated(-dx, dy)
            self._resample("fast")
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self._drag_origin is not None:
            self._drag_origin = None
            self._drag_view = None
            self.setCursor(Qt.ArrowCursor)
            self._refine_timer.start()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.reset_view()
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._view = self._view.with_aspect(self.width(), self.height())
        self._resample("fast")
        self._refine_timer.start()


# ---------------------------------------------------------------------------
# 图像窗口
# ---------------------------------------------------------------------------
DEFAULT_INPUT = "y = x^2 - 2x - 3"


class GraphWindow(QWidget):
    """函数图像窗口:输入表达式 → 自动绘制"""

    def __init__(self, theme_name: str = theme.DEFAULT_THEME, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("函数图像")
        self.setWindowIcon(appicon.load_app_icon())
        self.resize(920, 720)

        self._theme_name = theme_name
        self._curves: list[CurveSpec] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        # ---- 顶部:输入框 + 操作按钮 ----
        top = QHBoxLayout()
        top.setSpacing(10)

        self._input = QPlainTextEdit()
        self._input.setObjectName("GraphInput")
        self._input.setPlaceholderText(
            "每行一条曲线,输入后自动绘制:\n"
            "y = x^2 - 1        显函数\n"
            "x^2 + y^2 = 25     隐函数(圆 / 椭圆 / 双曲线…)\n"
            "x=3cos(t), y=2sin(t)   参数方程\n"
            "r = 1 - sin(θ)     极坐标"
        )
        self._input.setFixedHeight(84)
        self._input.setPlainText(DEFAULT_INPUT)
        self._input.textChanged.connect(self._schedule_replot)
        top.addWidget(self._input, 1)

        side = QVBoxLayout()
        side.setSpacing(6)
        self._example_btn = QPushButton("示例")
        self._example_btn.setObjectName("GraphBtn")
        self._example_btn.setCursor(Qt.PointingHandCursor)
        self._example_btn.setToolTip("插入常用曲线示例")
        self._example_btn.clicked.connect(self._show_examples)

        self._reset_btn = QPushButton("重置视图")
        self._reset_btn.setObjectName("GraphBtn")
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.setToolTip("回到默认视口(也可在画布上双击)")
        self._reset_btn.clicked.connect(lambda: self._canvas.reset_view())

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setObjectName("GraphBtn")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.clicked.connect(lambda: self._input.setPlainText(""))

        for button in (self._example_btn, self._reset_btn, self._clear_btn):
            button.setFixedWidth(88)
            side.addWidget(button)
        side.addStretch(1)
        top.addLayout(side)
        root.addLayout(top)

        # ---- 画布 ----
        self._canvas = PlotCanvas(theme_name)
        self._canvas.coords_changed.connect(self._on_coords)
        root.addWidget(self._canvas, 1)

        # ---- 状态栏 ----
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        self._status = QLabel("")
        self._status.setObjectName("GraphStatus")
        self._hint = QLabel("滚轮缩放 · 拖拽平移 · 双击复位")
        self._hint.setObjectName("GraphHint")
        status_row.addWidget(self._status, 1)
        status_row.addWidget(self._hint)
        root.addLayout(status_row)

        self._replot_timer = QTimer(self)
        self._replot_timer.setSingleShot(True)
        self._replot_timer.setInterval(REPLOT_DELAY_MS)
        self._replot_timer.timeout.connect(self._replot)

        # 首次绘制
        self._replot()

    # ------------------------------------------------------------------
    # 绘制流程
    # ------------------------------------------------------------------
    def _schedule_replot(self) -> None:
        self._replot_timer.start()

    def _replot(self) -> None:
        curves, errors = plot.parse_lines(self._input.toPlainText())
        self._curves = curves
        self._canvas.set_curves(curves)

        colors = theme.THEMES[self._theme_name]
        if errors:
            self._status.setText("；".join(errors[:3]))
            self._status.setStyleSheet(f"color: {colors['error']};")
        elif curves:
            kinds = "、".join(sorted({curve.kind_name for curve in curves}))
            self._status.setText(f"已绘制 {len(curves)} 条曲线({kinds})")
            self._status.setStyleSheet(f"color: {colors['text2']};")
        else:
            self._status.setText("输入表达式后自动绘制")
            self._status.setStyleSheet(f"color: {colors['text2']};")

    def _on_coords(self, x: float, y: float) -> None:
        self._hint.setText(f"x = {x:.4g},  y = {y:.4g}   ·   滚轮缩放 · 拖拽平移 · 双击复位")

    # ------------------------------------------------------------------
    # 示例菜单
    # ------------------------------------------------------------------
    def _show_examples(self) -> None:
        menu = QMenu(self)
        for name, text in plot.EXAMPLES:
            action = menu.addAction(name)
            action.triggered.connect(lambda _=False, t=text: self._apply_example(t))
        menu.addSeparator()
        menu.addAction("清空输入", lambda: self._input.setPlainText(""))
        menu.exec(self._example_btn.mapToGlobal(
            self._example_btn.rect().bottomLeft()))

    def _apply_example(self, text: str) -> None:
        self._input.setPlainText(text)
        self._replot()

    # ------------------------------------------------------------------
    # 主题
    # ------------------------------------------------------------------
    def apply_theme(self, name: str) -> None:
        self._theme_name = name
        self._canvas.set_theme(name)
        self._replot()
