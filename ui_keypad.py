# -*- coding: utf-8 -*-
"""按键控件、表达式显示、LCD 屏幕"""
import html as _html
import re

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient
from PySide6.QtWidgets import (QAbstractButton, QTextEdit, QFrame, QLabel,
                               QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget)

from engine import DISPLAY_TOKENS


def esc(s):
    return _html.escape(s, quote=False)


def _match_paren(s, o):
    d = 0
    for i in range(o, len(s)):
        if s[i] == "(":
            d += 1
        elif s[i] == ")":
            d -= 1
            if d == 0:
                return i
    return len(s) - 1


_CUR_ON = '<span style="color:#0a3d1a;font-weight:bold;">│</span>'
_CUR_OFF = '<span style="color:#0a3d1a;font-weight:bold;">&nbsp;</span>'


def render_expr(expr, cursor, cursor_visible=True):
    """把内部表达式字符串渲染成带上下标/根号的 HTML"""
    out = []
    i, n = 0, len(expr)
    while i < n:
        if i == cursor:
            out.append(_CUR_ON if cursor_visible else _CUR_OFF)
        # 科学记数 ×10^ 优先
        mm = re.match(r"×10\^(−?\d+(?:\.\d+)?)", expr[i:])
        if mm:
            s = mm.group(0)
            out.append("×10<sup>" + esc(s[4:]) + "</sup>")
            i += len(s)
            continue
        if expr.startswith("ˣ√(", i):
            j = _match_paren(expr, i + 2)
            inner = expr[i + 3:j]
            out.append(esc("ˣ√") + '<span style="text-decoration:overline">('
                       + esc(inner) + ")</span>")
            i = j + 1
            continue
        if expr.startswith("√(", i) or expr.startswith("³√(", i):
            pre = "³√" if expr.startswith("³√", i) else "√"
            j = _match_paren(expr, i + len(pre))
            inner = expr[i + len(pre):j + 1]
            out.append(esc(pre) + '<span style="text-decoration:overline">'
                       + esc(inner) + "</span>")
            i = j + 1
            continue
        mname = None
        for tok in DISPLAY_TOKENS:
            if tok == "e^":
                continue
            if expr.startswith(tok, i):
                mname = tok
                break
        if mname:
            out.append(esc(mname))
            i += len(mname)
            continue
        c = expr[i]
        if c == "^" and i + 1 < n and expr[i + 1] == "(":
            j = _match_paren(expr, i + 1)
            out.append("<sup>" + esc(expr[i + 2:j]) + "</sup>")
            i = j + 1
            continue
        out.append(esc(c))
        i += 1
    if cursor >= n:
        out.append(_CUR_ON if cursor_visible else _CUR_OFF)
    return "".join(out)


class ExpressionLine(QTextEdit):
    """只读富文本表达式行(光标由 HTML 渲染,支持智能删除)"""

    def __init__(self, parent=None, font_size=12.0):
        super().__init__(parent)
        self.expr = ""
        self.cursor = 0
        self.overwrite = False
        self._cursor_visible = True
        self.setReadOnly(True)
        self.setAcceptRichText(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setFocusPolicy(Qt.NoFocus)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.document().setDocumentMargin(0)
        f = QFont("Segoe UI", int(font_size))
        self.setFont(f)
        self.setStyleSheet("QTextEdit{background:transparent;color:#101410;border:none;}")
        self.refresh()

    def refresh(self):
        self.setHtml(render_expr(self.expr, self.cursor, self._cursor_visible))
        vb = self.verticalScrollBar()
        vb.setValue(vb.maximum())

    def blink(self):
        self._cursor_visible = not self._cursor_visible
        self.refresh()

    def set_expr(self, s, cursor=None):
        self.expr = s
        self.cursor = len(s) if cursor is None else max(0, min(cursor, len(s)))
        self.refresh()

    def insert_text(self, s):
        if self.overwrite and self.cursor < len(self.expr):
            self.expr = self.expr[:self.cursor] + s + self.expr[self.cursor + 1:]
        else:
            self.expr = self.expr[:self.cursor] + s + self.expr[self.cursor:]
        self.cursor += len(s)
        self.refresh()

    def insert_template(self, pre, post):
        self.expr = self.expr[:self.cursor] + pre + post + self.expr[self.cursor:]
        self.cursor += len(pre)
        self.refresh()

    def insert_catalog(self, s):
        """插入目录模板:删除所有 ◦ 占位符,光标停在第一个 ◦ 处"""
        pos = s.find("◦")
        clean = s.replace("◦", "")
        self.expr = self.expr[:self.cursor] + clean + self.expr[self.cursor:]
        self.cursor += (pos if pos >= 0 else len(clean))
        self.refresh()

    def _token_at(self, pos, forward=True):
        best = ""
        for tok in DISPLAY_TOKENS:
            if tok == "e^":
                continue
            if forward:
                if self.expr.startswith(tok, pos) and len(tok) > len(best):
                    best = tok
            else:
                if self.expr[max(0, pos - len(tok)):pos] == tok and len(tok) > len(best):
                    best = tok
        return best

    def del_char(self):
        tok = self._token_at(self.cursor, True)
        if tok:
            self.expr = self.expr[:self.cursor] + self.expr[self.cursor + len(tok):]
        elif self.cursor < len(self.expr):
            self.expr = self.expr[:self.cursor] + self.expr[self.cursor + 1:]
        self.refresh()

    def del_left(self):
        tok = self._token_at(self.cursor, False)
        if tok:
            self.expr = self.expr[:self.cursor - len(tok)] + self.expr[self.cursor:]
            self.cursor -= len(tok)
        elif self.cursor > 0:
            self.expr = self.expr[:self.cursor - 1] + self.expr[self.cursor:]
            self.cursor -= 1
        self.refresh()

    def move_cursor(self, d):
        self.cursor = max(0, min(len(self.expr), self.cursor + d))
        self.refresh()

    def clear(self):
        self.expr = ""
        self.cursor = 0
        self.refresh()


class KeyButton(QAbstractButton):
    """自绘计算器按键:主标签 + 上方浅色次级标签"""

    def __init__(self, main, sub="", code="", base="#3a3d43", sub_color="#8fb8f0",
                 main_color="#f2f2f2", main_size=10.5, sub_size=6.5, w=54, h=44,
                 parent=None):
        super().__init__(parent)
        self._main = main
        self._sub = sub
        self._main_color = QColor(main_color)
        self.code = code
        self._base = QColor(base)
        self._sub_color = QColor(sub_color)
        self._main_size = main_size
        self._sub_size = sub_size
        self.setFixedSize(w, h)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self.setAttribute(Qt.WA_Hover, True)

    def set_lit(self, lit):
        self.setProperty("lit", lit)
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)
        col = QColor(self._base)
        if self.property("lit"):
            col = col.lighter(160)
        elif self.isDown():
            col = col.darker(140)
        elif self.underMouse():
            col = col.lighter(112)
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawRoundedRect(r, 7, 7)
        p.setPen(QColor(255, 255, 255, 24))
        p.drawLine(int(r.left()) + 8, int(r.top()) + 1, int(r.right()) - 8, int(r.top()) + 1)
        if self._sub:
            f = QFont(self.font())
            f.setPointSizeF(self._sub_size)
            p.setFont(f)
            p.setPen(self._sub_color)
            sub_rect = QRectF(r.left(), r.top() + 1, r.width(), r.height() * 0.46)
            p.drawText(sub_rect, Qt.AlignHCenter | Qt.AlignTop, self._sub)
        f = QFont(self.font())
        f.setPointSizeF(self._main_size)
        f.setBold(True)
        p.setFont(f)
        p.setPen(self._main_color)
        top = r.height() * 0.30 if self._sub else 0.0
        main_rect = QRectF(r.left(), r.top() + top, r.width(), r.height() - top)
        p.drawText(main_rect, Qt.AlignHCenter | Qt.AlignVCenter, self._main)


class SolarPanel(QWidget):
    """顶部太阳能电池板"""

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        g = QLinearGradient(0, 0, 0, r.height())
        g.setColorAt(0, QColor("#161d28"))
        g.setColorAt(1, QColor("#28364a"))
        p.fillRect(r, g)
        p.setPen(QColor(255, 255, 255, 26))
        n = 8
        for i in range(1, n):
            x = int(r.width() * i / n)
            p.drawLine(x, 0, x, r.height())
        p.setPen(QColor(255, 255, 255, 46))
        p.drawLine(0, 0, r.width(), 0)
        p.drawLine(0, r.height() - 1, r.width(), r.height() - 1)


class LCDScreen(QFrame):
    """计算器屏幕:状态行 + 页面堆栈"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("lcd")
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 6, 12, 8)
        v.setSpacing(0)
        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        self.status_left = QLabel()
        self.status_left.setTextFormat(Qt.RichText)
        self.status_right = QLabel()
        self.status_right.setTextFormat(Qt.RichText)
        self.status_right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for lb in (self.status_left, self.status_right):
            lb.setStyleSheet("color:#3c4a5c;font-size:8pt;")
        h.addWidget(self.status_left, 1)
        h.addWidget(self.status_right, 0)
        v.addLayout(h)
        self.stack = QStackedWidget()
        v.addWidget(self.stack, 1)

    def add_page(self, w):
        self.stack.addWidget(w)

    def show_page(self, w):
        self.stack.setCurrentWidget(w)

    def set_status(self, left="", right=""):
        self.status_left.setText(left)
        self.status_right.setText(right)
