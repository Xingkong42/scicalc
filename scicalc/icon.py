# -*- coding: utf-8 -*-
"""科学计算器 —— 图标

应用图标加载顺序:
1. 用户预留图标:把 icon.png / icon.ico / icon.svg 放到本程序目录即可自动生效
   (这也是推荐做法——你可以随时替换为自己的作品,无需改代码);
2. 若未提供,则用 QPainter 现场绘制一枚极简图标作为兜底。

另外提供工具栏小图标(历史 / 复制 / 主题)的自绘函数,颜色随主题刷新。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap,
                           QPolygonF)

_APP_DIR = Path(__file__).resolve().parent

# 用户自备图标的候选文件名(按优先级)
_USER_ICON_NAMES = ("icon.png", "icon.ico", "icon.svg")


# ---------------------------------------------------------------------------
# 应用图标
# ---------------------------------------------------------------------------
def load_app_icon() -> QIcon:
    """优先加载用户自备图标;没有则绘制默认图标"""
    for name in _USER_ICON_NAMES:
        path = _APP_DIR / name
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return make_default_icon()


def make_default_icon() -> QIcon:
    """绘制默认图标:圆角方块 + 屏幕条 + 按键点阵(极简风格)"""
    size = 256
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    r = QRectF(16, 16, 224, 224)
    # 背景圆角方块
    path = QPainterPath()
    path.addRoundedRect(r, 56, 56)
    p.fillPath(path, QColor("#0071E3"))

    # 顶部"屏幕"横条
    screen = QPainterPath()
    screen.addRoundedRect(QRectF(56, 60, 144, 44), 14, 14)
    p.fillPath(screen, QColor(255, 255, 255, 235))

    # 按键点阵:2 行 × 3 列圆点
    p.setBrush(QColor(255, 255, 255, 165))
    p.setPen(Qt.NoPen)
    for row in range(2):
        for col in range(3):
            x = 78 + col * 50
            y = 138 + row * 44
            p.drawEllipse(QPointF(x, y), 13, 13)

    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------------------
# 工具栏小图标(矢量线条风格,随主题着色)
# ---------------------------------------------------------------------------
def make_glyph_icon(kind: str, color: str, size: int = 64) -> QIcon:
    """绘制工具栏小图标。kind: history / copy / theme

    以 64×64 画布绘制,线条粗 5,圆角端点,颜色由主题提供。
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    pen = QPen(QColor(color))
    pen.setWidthF(4.5)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if kind == "history":
        # 时钟:圆 + 指针
        p.drawEllipse(QRectF(10, 10, 44, 44))
        p.drawLine(QPointF(32, 32), QPointF(32, 18))
        p.drawLine(QPointF(32, 32), QPointF(42, 38))
    elif kind == "copy":
        # 复制:前后两张纸
        p.drawRoundedRect(QRectF(14, 20, 30, 32), 6, 6)
        # 后面一张只画露出的右上角折线
        p.drawLine(QPointF(26, 14), QPointF(42, 14))
        p.drawLine(QPointF(48, 20), QPointF(48, 38))
        p.drawLine(QPointF(42, 14), QPointF(48, 20))
    elif kind == "theme":
        # 主题:一半填充的圆(浅色 → 右半深色;深色 → 右半留白)
        p.drawEllipse(QRectF(10, 10, 44, 44))
        p.setBrush(QColor(color))
        p.setPen(Qt.NoPen)
        p.drawPie(QRectF(10, 10, 44, 44), 90 * 16, 180 * 16)
    elif kind == "trash":
        # 清空:垃圾桶
        p.drawRoundedRect(QRectF(18, 22, 28, 30), 5, 5)
        p.drawLine(QPointF(13, 22), QPointF(51, 22))
        p.drawLine(QPointF(27, 15), QPointF(37, 15))
        p.drawLine(QPointF(28, 30), QPointF(28, 44))
        p.drawLine(QPointF(36, 30), QPointF(36, 44))

    p.end()
    return QIcon(pm)
