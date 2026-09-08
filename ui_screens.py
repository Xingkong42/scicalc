# -*- coding: utf-8 -*-
"""各应用屏幕与主窗口:主菜单/计算/统计/函数表格/方程/不等式/复数 + 设置/目录/工具/变量/功能/单位换算"""
from PySide6.QtCore import Qt, QSettings, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QWidget, QLabel, QFrame, QGridLayout, QVBoxLayout, QHBoxLayout,
                               QPushButton, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
                               QComboBox, QScrollArea, QApplication, QListWidget, QSizePolicy)

from engine import CalcEngine, CalcError, CATALOG, UNITS, VARIABLES
from ui_keypad import KeyButton, ExpressionLine, LCDScreen, SolarPanel, esc


# --------------------------------------------------------------------------
# 通用小部件
# --------------------------------------------------------------------------
class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


def make_tile(icon, name, sub, on_click):
    f = ClickableFrame()
    f.setObjectName("tile")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(4, 6, 4, 4)
    lay.setSpacing(1)
    ic = QLabel(icon)
    ic.setAlignment(Qt.AlignCenter)
    f1 = QFont()
    f1.setPointSizeF(11.5)
    f1.setBold(True)
    ic.setFont(f1)
    nm = QLabel(name)
    nm.setAlignment(Qt.AlignCenter)
    f2 = QFont()
    f2.setPointSizeF(8.5)
    f2.setBold(True)
    nm.setFont(f2)
    sb = QLabel(sub)
    sb.setAlignment(Qt.AlignCenter)
    f3 = QFont()
    f3.setPointSizeF(6.5)
    sb.setFont(f3)
    lay.addWidget(ic)
    lay.addWidget(nm)
    lay.addWidget(sb)
    f.clicked.connect(on_click)
    f._labels = [ic, nm, sb]
    return f


def set_tile_selected(f, sel):
    if sel:
        f.setStyleSheet("QFrame{background:#33383f;border-radius:6px;}"
                        "QLabel{color:#e8ece4;background:transparent;border:none;}")
    else:
        f.setStyleSheet("QFrame{background:transparent;border-radius:6px;}"
                        "QLabel{color:#22262b;background:transparent;border:none;}")


def expr_insert_key(line, code, shifted):
    """把按键映射为表达式编辑操作,返回是否已处理"""
    var_shift = {"1": "X", "2": "Y", "3": "Z", "4": "D", "5": "E", "6": "F",
                 "7": "A", "8": "B", "9": "C"}
    if code in "0123456789":
        line.insert_text(var_shift[code] if (shifted and code in var_shift) else code)
        return True
    if code == "dot":
        line.insert_text(".")
        return True
    if code == "neg":
        line.insert_text("−")
        return True
    if code == "add":
        line.insert_text("+")
        return True
    if code == "sub":
        line.insert_text("-")
        return True
    if code == "mul":
        line.insert_text("×")
        return True
    if code == "div":
        line.insert_text("÷")
        return True
    if code == "lparen":
        line.insert_text("(")
        return True
    if code == "rparen":
        line.insert_text(")")
        return True
    if code == "sin":
        line.insert_text("sin⁻¹(" if shifted else "sin(")
        return True
    if code == "cos":
        line.insert_text("cos⁻¹(" if shifted else "cos(")
        return True
    if code == "tan":
        line.insert_text("tan⁻¹(" if shifted else "tan(")
        return True
    if code == "exp10":
        line.insert_text("×10^")
        return True
    if code == "ans":
        line.insert_text("Ans")
        return True
    if code == "power":
        line.insert_template("^(", ")")
        return True
    if code == "fact":
        line.insert_text("!")
        return True
    if code == "pct":
        line.insert_text("%")
        return True
    if code == "del":
        line.del_char()
        return True
    if code == "left":
        line.move_cursor(-1)
        return True
    if code == "right":
        line.move_cursor(1)
        return True
    return False


# --------------------------------------------------------------------------
# 主菜单
# --------------------------------------------------------------------------
class MenuScreen(QWidget):
    APP_KEYS = ["calc", "stats", "table", "equation", "inequality", "complex"]
    APPS = [
        ("＋−×÷", "计算", "基本计算"),
        ("x̄ σ", "统计", "统计计算"),
        ("ƒ(x)", "函数表格", "函数值表"),
        ("x²", "方程", "XY=0"),
        ("x²≥", "不等式", "XY>0"),
        ("i", "复数", "a+bi"),
    ]

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.sel = 0
        self.page_name = "主屏幕"
        g = QGridLayout(self)
        g.setSpacing(8)
        g.setContentsMargins(6, 2, 6, 2)
        self.tiles = []
        for i, (icon, name, sub) in enumerate(self.APPS):
            f = make_tile(icon, name, sub,
                          lambda c=i: self.window.open_app(self.APP_KEYS[c]))
            g.addWidget(f, i // 3, i % 3)
            self.tiles.append(f)

    def on_open(self):
        self.sel = 0
        self._refresh()

    def _refresh(self):
        for i, f in enumerate(self.tiles):
            set_tile_selected(f, i == self.sel)

    def handle_key(self, code, shifted):
        if code == "left":
            self.sel = max(0, self.sel - 1)
        elif code == "right":
            self.sel = min(5, self.sel + 1)
        elif code == "up":
            self.sel = max(0, self.sel - 3)
        elif code == "down":
            self.sel = min(5, self.sel + 3)
        elif code in ("ok", "exe"):
            self.window.open_app(self.APP_KEYS[self.sel])
            return
        self._refresh()


# --------------------------------------------------------------------------
# 计算 / 复数
# --------------------------------------------------------------------------
class CalcScreen(QWidget):
    def __init__(self, window, complex_app=False):
        super().__init__()
        self.window = window
        self.complex_app = complex_app
        self.page_name = "复数" if complex_app else "计算"
        self.history = []
        self.hist_idx = None
        self.form = "auto"
        self.polar = False
        self.last_value = None
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 0, 4, 2)
        v.setSpacing(2)
        self.expr = ExpressionLine(font_size=12.5)
        self.expr.setFixedHeight(66)
        v.addWidget(self.expr)
        self.result = QLabel()
        self.result.setWordWrap(True)
        self.result.setTextFormat(Qt.RichText)
        self.result.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        f = QFont("Segoe UI", 13)
        f.setBold(True)
        self.result.setFont(f)
        self.result.setStyleSheet("color:#101410;background:transparent;")
        v.addWidget(self.result, 1)
        self.hint = QLabel()
        self.hint.setTextFormat(Qt.RichText)
        self.hint.setStyleSheet("color:#5a6a5a;font-size:7.5pt;background:transparent;")
        v.addWidget(self.hint)
        self._blink = QTimer(self)
        self._blink.timeout.connect(self.expr.blink)
        self._blink.start(530)

    def on_open(self):
        if self.complex_app:
            self.window.engine.settings.complex_mode = True
        self.expr.refresh()

    def evaluate(self):
        self.hist_idx = None
        text = self.expr.expr.strip()
        if not text:
            return
        eng = self.window.engine
        try:
            v, _meta = eng.evaluate(text)
        except CalcError as err:
            self._show_error(err.msg)
            return
        self.last_value = v
        self.form = "auto"
        self.polar = False
        s = self.format_result(v)
        self.result.setText(s)
        hint = ""
        if eng.last_store:
            name, val = eng.last_store
            hint = f"{name} = {esc(eng.format_value(val))}"
        self.hint.setText(hint)
        self.history.append((self.expr.expr, s))
        if len(self.history) > 60:
            self.history.pop(0)

    def _show_error(self, msg):
        self.result.setText(f'<span style="color:#a32b2b;">{esc(msg)}</span>')
        QApplication.beep()

    def format_result(self, v):
        eng = self.window.engine
        if self.form == "sexa":
            s = eng.format_sexa(v)
            if s:
                return s
        if self.form == "frac":
            return eng.format_value(v, frac="frac")
        if isinstance(v, complex):
            return eng.format_value(v, polar=self.polar)
        return eng.format_value(v, frac="auto")

    def toggle_form(self):
        v = self.last_value
        if v is None:
            QApplication.beep()
            return
        eng = self.window.engine
        if isinstance(v, complex):
            self.polar = not self.polar
            self.result.setText(self.format_result(v))
            return
        if self.form != "dec":
            self.form = "dec"
        else:
            try:
                s = eng.format_value(v, frac="frac")
                if "⁄" in s:
                    self.form = "frac"
                elif eng.format_sexa(v):
                    self.form = "sexa"
                else:
                    QApplication.beep()
                    return
            except CalcError:
                QApplication.beep()
                return
        self.result.setText(self.format_result(v))

    def clear_input(self):
        self.expr.clear()
        self.form = "auto"
        self.last_value = None
        self.hist_idx = None
        self.result.setText("")
        self.hint.setText("")

    def history_scroll(self, d):
        if not self.history:
            return
        if self.hist_idx is None:
            self.hist_idx = len(self.history) - 1 if d < 0 else 0
        else:
            self.hist_idx = max(0, min(len(self.history) - 1, self.hist_idx + d))
        expr, res = self.history[self.hist_idx]
        self.expr.set_expr(expr)
        self.result.setText(res)

    def handle_key(self, code, shifted):
        if expr_insert_key(self.expr, code, shifted):
            self.hist_idx = None
            return
        if code in ("ok", "exe"):
            self.evaluate()
        elif code == "ac":
            self.clear_input()
        elif code == "ins":
            self.window.toggle_ins()
        elif code in ("up", "scroll_up"):
            self.history_scroll(-1)
        elif code in ("down", "scroll_down"):
            self.history_scroll(1)
        elif code == "fmt":
            if shifted:
                self.toggle_form()
            else:
                self.window.open_overlay("format")


# --------------------------------------------------------------------------
# 统计
# --------------------------------------------------------------------------
class StatsScreen(QWidget):
    MODES = [
        ("1-VAR", "单变量", "X 与频数"),
        ("a+bx", "线性回归", "X、Y 与频数"),
        ("a+bx+cx²", "二次回归", "X、Y 与频数"),
    ]

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "统计"
        self.state = "mode"
        self.mode = 0
        self.sel = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        self.mode_holder = QWidget()
        mh = QHBoxLayout(self.mode_holder)
        mh.setContentsMargins(0, 0, 0, 0)
        mh.setSpacing(8)
        self.mode_tiles = []
        for i, (icon, name, sub) in enumerate(self.MODES):
            f = make_tile(icon, name, sub, lambda c=i: self._enter_mode(c))
            mh.addWidget(f)
            self.mode_tiles.append(f)
        v.addWidget(self.mode_holder, 1)
        self.data_holder = QWidget()
        dh = QVBoxLayout(self.data_holder)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(4)
        top = QHBoxLayout()
        self.table = QTableWidget()
        top.addWidget(self.table, 1)
        self.results = QLabel()
        self.results.setWordWrap(True)
        self.results.setTextFormat(Qt.RichText)
        self.results.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.results.setStyleSheet("background:transparent;color:#101410;")
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.results)
        sc.setStyleSheet("background:transparent;border:none;")
        sc.setFixedWidth(170)
        top.addWidget(sc, 0)
        dh.addLayout(top, 1)
        btns = QHBoxLayout()
        for label, fn in (("＋行", self.add_row), ("－行", self.del_row),
                          ("计算", self.compute), ("返回", self.show_mode)):
            b = QPushButton(label)
            b.setObjectName("soft")
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        dh.addLayout(btns)
        v.addWidget(self.data_holder, 1)
        self.data_holder.hide()

    def on_open(self):
        self.show_mode()

    def show_mode(self):
        self.state = "mode"
        self.sel = 0
        self.mode_holder.show()
        self.data_holder.hide()
        self._refresh_tiles()

    def _refresh_tiles(self):
        for i, f in enumerate(self.mode_tiles):
            set_tile_selected(f, i == self.sel)

    def _enter_mode(self, i):
        self.sel = i
        self.mode = i
        self.state = "data"
        self._build_table()
        self.results.setText("")
        self.mode_holder.hide()
        self.data_holder.show()
        self.table.setFocus()

    def _build_table(self):
        cols = ["X", "频数"] if self.mode == 0 else ["X", "Y", "频数"]
        self.table.clear()
        self.table.setColumnCount(len(cols))
        self.table.setRowCount(3)
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for r in range(3):
            for c in range(len(cols)):
                self.table.setItem(r, c, QTableWidgetItem(""))
        self.table.setCurrentCell(0, 0)

    def add_row(self):
        self.table.insertRow(self.table.rowCount())

    def del_row(self):
        r = self.table.currentRow()
        if r >= 0 and self.table.rowCount() > 1:
            self.table.removeRow(r)

    def handle_key(self, code, shifted):
        if self.state == "mode":
            if code in ("left", "up"):
                self.sel = max(0, self.sel - 1)
            elif code in ("right", "down"):
                self.sel = min(2, self.sel + 1)
            elif code in ("ok", "exe"):
                self._enter_mode(self.sel)
            self._refresh_tiles()
            return
        if code in ("ok", "exe"):
            self.compute()
        elif code == "ac":
            self.show_mode()
        elif code in ("up", "down", "left", "right"):
            self.table.setFocus()

    def _read_cell(self, r, c, default="0"):
        it = self.table.item(r, c)
        txt = it.text().strip() if it and it.text() else ""
        if not txt:
            return float(default)
        try:
            return float(txt.replace("−", "-"))
        except ValueError:
            raise CalcError("数据无效")

    def _collect(self):
        data = []
        for r in range(self.table.rowCount()):
            x = self._read_cell(r, 0)
            if self.mode == 0:
                f = self._read_cell(r, 1, "1")
                data.append((x, f))
            else:
                y = self._read_cell(r, 1)
                f = self._read_cell(r, 2, "1")
                data.append((x, y, f))
        return data

    def compute(self):
        eng = self.window.engine
        try:
            data = self._collect()
            if self.mode == 0:
                r = eng.stats_1var(data)
                rows = [("n", r["n"]), ("x̄", r["mean"]), ("Σx", r["sx"]), ("Σx²", r["sx2"]),
                        ("σx", r["sdp"]), ("sx", r["sds"]), ("minX", r["min"]),
                        ("Q1", r["q1"]), ("Med", r["med"]), ("Q3", r["q3"]), ("maxX", r["max"])]
            elif self.mode == 1:
                r = eng.stats_lin(data)
                rows = [("a", r["a"]), ("b", r["b"]), ("r", r["r"]), ("n", r["n"]),
                        ("x̄", r["meanx"]), ("ȳ", r["meany"]), ("Σx", r["sx"]),
                        ("Σy", r["sy"]), ("Σx²", r["sxx"]), ("Σy²", r["syy"]),
                        ("Σxy", r["sxy"]), ("σx", r["sdx"]), ("σy", r["sdy"])]
            else:
                r = eng.stats_quad(data)
                rows = [("a", r["a"]), ("b", r["b"]), ("c", r["c"]), ("n", r["n"])]
        except CalcError as err:
            self.results.setText(f'<span style="color:#a32b2b;">{esc(err.msg)}</span>')
            QApplication.beep()
            return
        lines = [f"<b>{esc(k)}</b> = {esc(eng.format_value(v))}" for k, v in rows]
        self.results.setText("<br>".join(lines))


# --------------------------------------------------------------------------
# 函数表格
# --------------------------------------------------------------------------
class TableScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "函数表格"
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        h1 = QHBoxLayout()
        lb = QLabel("f(x) =")
        lb.setStyleSheet("color:#101410;font-weight:bold;background:transparent;")
        h1.addWidget(lb)
        self.expr = ExpressionLine(font_size=11.5)
        self.expr.setFixedHeight(42)
        h1.addWidget(self.expr, 1)
        v.addLayout(h1)
        h2 = QHBoxLayout()
        for label, defval, width in (("起始", "1", 60), ("终止", "5", 60), ("步长", "1", 60)):
            l2 = QLabel(label)
            l2.setStyleSheet("color:#101410;background:transparent;font-size:8.5pt;")
            e2 = QLineEdit(defval)
            e2.setFixedWidth(width)
            h2.addWidget(l2)
            h2.addWidget(e2)
            setattr(self, {"起始": "start", "终止": "end", "步长": "step"}[label], e2)
        b = QPushButton("生成表格")
        b.setObjectName("soft")
        b.clicked.connect(self.generate)
        h2.addWidget(b)
        h2.addStretch(1)
        v.addLayout(h2)
        self.hint = QLabel()
        self.hint.setTextFormat(Qt.RichText)
        self.hint.setStyleSheet("color:#5a6a5a;font-size:7.5pt;background:transparent;")
        v.addWidget(self.hint)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["x", "f(x)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        v.addWidget(self.table, 1)

    def on_open(self):
        self.expr.refresh()
        self.hint.setText("输入 f(x) 表达式,按 EXE 生成表格")

    def handle_key(self, code, shifted):
        if expr_insert_key(self.expr, code, shifted):
            return
        if code in ("ok", "exe"):
            self.generate()
        elif code == "ac":
            self.expr.clear()
        elif code in ("up", "down"):
            self.table.setFocus()

    def generate(self):
        eng = self.window.engine
        expr = self.expr.expr.strip()
        if not expr:
            self.hint.setText('<span style="color:#a32b2b;">请输入 f(x) 表达式</span>')
            QApplication.beep()
            return
        try:
            start = float(self.start.text().replace("−", "-"))
            end = float(self.end.text().replace("−", "-"))
            step = float(self.step.text().replace("−", "-"))
        except ValueError:
            self.hint.setText('<span style="color:#a32b2b;">起始/终止/步长无效</span>')
            QApplication.beep()
            return
        if step == 0 or (end - start) / step < 0:
            self.hint.setText('<span style="color:#a32b2b;">步长无效或方向错误</span>')
            QApplication.beep()
            return
        count = int((end - start) / step + 1e-9) + 1
        if count > 100:
            count = 100
            self.hint.setText("行数超过上限,仅显示前 100 行")
        else:
            self.hint.setText("")
        self.table.setRowCount(count)
        old = eng.vars["X"]
        for k in range(count):
            x = start + k * step
            eng.vars["X"] = x
            try:
                vv, _ = eng.evaluate(expr)
            except CalcError as err:
                eng.vars["X"] = old
                self.hint.setText(f'<span style="color:#a32b2b;">x={esc(eng.format_value(x))}: {esc(err.msg)}</span>')
                QApplication.beep()
                return
            self.table.setItem(k, 0, QTableWidgetItem(eng.format_value(x)))
            self.table.setItem(k, 1, QTableWidgetItem(eng.format_value(vv)))
        eng.vars["X"] = old


# --------------------------------------------------------------------------
# 方程
# --------------------------------------------------------------------------
class EquationScreen(QWidget):
    MODES = [
        ("2元", "联立方程组", "2x+3y=5", 2, "lin"),
        ("3元", "联立方程组", "x,y,z", 3, "lin"),
        ("4元", "联立方程组", "x,y,z,t", 4, "lin"),
        ("二次", "二次方程", "ax²+bx+c=0", 2, "quad"),
        ("三次", "三次方程", "ax³+bx²+cx+d=0", 3, "cubic"),
    ]
    VAR_NAMES = ["x", "y", "z", "t"]
    HEADERS = ["a", "b", "c", "d", "e"]

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "方程"
        self.state = "mode"
        self.sel = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        self.mode_holder = QWidget()
        mh = QHBoxLayout(self.mode_holder)
        mh.setContentsMargins(0, 0, 0, 0)
        mh.setSpacing(6)
        self.mode_tiles = []
        for i, (icon, name, sub, _s, _k) in enumerate(self.MODES):
            f = make_tile(icon, name, sub, lambda c=i: self._enter_mode(c))
            mh.addWidget(f)
            self.mode_tiles.append(f)
        v.addWidget(self.mode_holder, 1)
        self.data_holder = QWidget()
        dh = QVBoxLayout(self.data_holder)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(4)
        top = QHBoxLayout()
        self.table = QTableWidget()
        top.addWidget(self.table, 1)
        self.results = QLabel()
        self.results.setWordWrap(True)
        self.results.setTextFormat(Qt.RichText)
        self.results.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.results.setStyleSheet("background:transparent;color:#101410;font-size:10pt;")
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(self.results)
        sc.setStyleSheet("background:transparent;border:none;")
        sc.setFixedWidth(190)
        top.addWidget(sc, 0)
        dh.addLayout(top, 1)
        btns = QHBoxLayout()
        for label, fn in (("求解", self.solve), ("返回", self.show_mode)):
            b = QPushButton(label)
            b.setObjectName("soft")
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        dh.addLayout(btns)
        v.addWidget(self.data_holder, 1)
        self.data_holder.hide()

    def on_open(self):
        self.show_mode()

    def show_mode(self):
        self.state = "mode"
        self.sel = 0
        self.mode_holder.show()
        self.data_holder.hide()
        self._refresh_tiles()

    def _refresh_tiles(self):
        for i, f in enumerate(self.mode_tiles):
            set_tile_selected(f, i == self.sel)

    def _enter_mode(self, i):
        self.sel = i
        self.state = "data"
        _icon, _name, _sub, size, kind = self.MODES[i]
        self.kind = kind
        self.size = size
        self._build_table()
        self.results.setText("")
        self.mode_holder.hide()
        self.data_holder.show()
        self.table.setFocus()

    def _build_table(self):
        self.table.clear()
        if self.kind == "lin":
            rows, cols = self.size, self.size + 1
            headers = self.HEADERS[:self.size] + ["="]
        else:
            rows, cols = 1, self.size + 1
            headers = self.HEADERS[:self.size + 1]
        self.table.setColumnCount(cols)
        self.table.setRowCount(rows)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for r in range(rows):
            for c in range(cols):
                self.table.setItem(r, c, QTableWidgetItem(""))
        self.table.setCurrentCell(0, 0)

    def handle_key(self, code, shifted):
        if self.state == "mode":
            if code in ("left", "up"):
                self.sel = max(0, self.sel - 1)
            elif code in ("right", "down"):
                self.sel = min(len(self.MODES) - 1, self.sel + 1)
            elif code in ("ok", "exe"):
                self._enter_mode(self.sel)
            self._refresh_tiles()
            return
        if code in ("ok", "exe"):
            self.solve()
        elif code == "ac":
            self.show_mode()
        elif code in ("up", "down", "left", "right"):
            self.table.setFocus()

    def _read_cell(self, r, c):
        it = self.table.item(r, c)
        txt = it.text().strip() if it and it.text() else ""
        if not txt:
            return 0.0
        try:
            return float(txt.replace("−", "-"))
        except ValueError:
            raise CalcError("系数无效")

    def _fmt_root(self, z):
        return self.window.engine.format_value(z)

    def _show_roots(self, roots):
        names = ["x₁", "x₂", "x₃", "x₄"]
        grouped = []
        for z in roots:
            found = None
            for g in grouped:
                if abs(z - g[0]) < 1e-9:
                    found = g
                    break
            if found:
                found.append(z)
            else:
                grouped.append([z])
        if len(grouped) == 1 and len(roots) == 1:
            return f"{names[0]} = {esc(self._fmt_root(roots[0]))}"
        lines = []
        k = 0
        for g in grouped:
            if len(g) == 1:
                lines.append(f"{names[k]} = {esc(self._fmt_root(g[0]))}")
            else:
                joined = "=".join(names[k:k + len(g)])
                lines.append(f"{joined} = {esc(self._fmt_root(g[0]))}")
            k += len(g)
        return "<br>".join(lines)

    def solve(self):
        eng = self.window.engine
        try:
            if self.kind == "lin":
                aug = []
                for r in range(self.size):
                    row = [self._read_cell(r, c) for c in range(self.size + 1)]
                    aug.append(row)
                sols = eng.gauss_solve(aug)
                lines = [f"{self.VAR_NAMES[i]} = {esc(eng.format_value(v))}"
                         for i, v in enumerate(sols)]
                text = "<br>".join(lines)
            else:
                coeffs = [self._read_cell(0, c) for c in range(self.size + 1)]
                if self.kind == "quad":
                    roots = eng.solve_quadratic(*coeffs)
                else:
                    roots = eng.solve_cubic(*coeffs)
                text = self._show_roots(roots)
        except CalcError as err:
            self.results.setText(f'<span style="color:#a32b2b;">{esc(err.msg)}</span>')
            QApplication.beep()
            return
        self.results.setText(text)


# --------------------------------------------------------------------------
# 不等式
# --------------------------------------------------------------------------
class InequalityScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "不等式"
        self.state = "mode"
        self.sel = 0
        self.deg = 2
        self.rel = ">"
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        self.mode_holder = QWidget()
        mh = QHBoxLayout(self.mode_holder)
        mh.setContentsMargins(0, 0, 0, 0)
        mh.setSpacing(8)
        self.mode_tiles = []
        for i, (icon, name, sub) in enumerate((("2", "二次", "ax²+bx+c"),
                                               ("3", "三次", "ax³+bx²+cx+d"))):
            f = make_tile(icon, name, sub, lambda c=i: self._pick_deg(c))
            mh.addWidget(f)
            self.mode_tiles.append(f)
        mh.addStretch(1)
        v.addWidget(self.mode_holder, 1)
        self.rel_holder = QWidget()
        rh = QHBoxLayout(self.rel_holder)
        rh.setContentsMargins(0, 0, 0, 0)
        rh.setSpacing(8)
        self.rel_tiles = []
        for i, r in enumerate((">", "≥", "<", "≤")):
            f = make_tile(r, "", "比较符", lambda c=i: self._pick_rel(c))
            rh.addWidget(f)
            self.rel_tiles.append(f)
        rh.addStretch(1)
        v.addWidget(self.rel_holder, 1)
        self.rel_holder.hide()
        self.data_holder = QWidget()
        dh = QVBoxLayout(self.data_holder)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(4)
        top = QHBoxLayout()
        self.table = QTableWidget()
        top.addWidget(self.table, 1)
        self.results = QLabel()
        self.results.setWordWrap(True)
        self.results.setTextFormat(Qt.RichText)
        self.results.setAlignment(Qt.AlignCenter)
        self.results.setStyleSheet("background:transparent;color:#101410;font-size:11pt;font-weight:bold;")
        top.addWidget(self.results, 1)
        dh.addLayout(top, 1)
        btns = QHBoxLayout()
        for label, fn in (("求解", self.solve), ("返回", self.show_mode)):
            b = QPushButton(label)
            b.setObjectName("soft")
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        dh.addLayout(btns)
        v.addWidget(self.data_holder, 1)
        self.data_holder.hide()
        self.rel_holder.hide()

    def on_open(self):
        self.show_mode()

    def show_mode(self):
        self.state = "mode"
        self.sel = 0
        self.mode_holder.show()
        self.rel_holder.hide()
        self.data_holder.hide()
        self._refresh()

    def _refresh(self):
        for i, f in enumerate(self.mode_tiles):
            set_tile_selected(f, i == self.sel and self.state == "mode")
        for i, f in enumerate(self.rel_tiles):
            set_tile_selected(f, i == self.sel and self.state == "rel")

    def _pick_deg(self, i):
        self.deg = 2 if i == 0 else 3
        self.state = "rel"
        self.sel = 0
        self.mode_holder.hide()
        self.rel_holder.show()
        self._refresh()

    def _pick_rel(self, i):
        self.rel = (">", "≥", "<", "≤")[i]
        self.state = "data"
        self._build_table()
        self.results.setText("")
        self.rel_holder.hide()
        self.data_holder.show()
        self.table.setFocus()

    def _build_table(self):
        self.table.clear()
        self.table.setColumnCount(self.deg + 1)
        self.table.setRowCount(1)
        self.table.setHorizontalHeaderLabels(["a", "b", "c", "d"][:self.deg + 1])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        for c in range(self.deg + 1):
            self.table.setItem(0, c, QTableWidgetItem(""))
        self.table.setCurrentCell(0, 0)

    def handle_key(self, code, shifted):
        if self.state == "mode":
            if code in ("left", "up"):
                self.sel = max(0, self.sel - 1)
            elif code in ("right", "down"):
                self.sel = min(1, self.sel + 1)
            elif code in ("ok", "exe"):
                self._pick_deg(self.sel)
            self._refresh()
            return
        if self.state == "rel":
            if code in ("left", "up"):
                self.sel = max(0, self.sel - 1)
            elif code in ("right", "down"):
                self.sel = min(3, self.sel + 1)
            elif code in ("ok", "exe"):
                self._pick_rel(self.sel)
            self._refresh()
            return
        if code in ("ok", "exe"):
            self.solve()
        elif code == "ac":
            self.show_mode()
        elif code in ("up", "down", "left", "right"):
            self.table.setFocus()

    def _read_cell(self, c):
        it = self.table.item(0, c)
        txt = it.text().strip() if it and it.text() else ""
        if not txt:
            return 0.0
        try:
            return float(txt.replace("−", "-"))
        except ValueError:
            raise CalcError("系数无效")

    def solve(self):
        eng = self.window.engine
        try:
            coeffs = [self._read_cell(c) for c in range(self.deg + 1)]
            text = eng.solve_inequality(coeffs, self.rel)
        except CalcError as err:
            self.results.setText(f'<span style="color:#a32b2b;">{esc(err.msg)}</span>')
            QApplication.beep()
            return
        self.results.setText(esc(text))


# --------------------------------------------------------------------------
# 设置
# --------------------------------------------------------------------------
class SettingsScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "设置"
        self.stack = []
        self.waiting = None
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        self.lb = QLabel()
        self.lb.setTextFormat(Qt.RichText)
        self.lb.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lb.setStyleSheet("background:transparent;color:#101410;")
        v.addWidget(self.lb, 1)
        self.lb.setWordWrap(True)
        hint = QLabel("↑↓ 选择 · OK 进入 · 设置键返回")
        hint.setStyleSheet("color:#5a6a5a;font-size:7.5pt;background:transparent;")
        v.addWidget(hint)

    def on_open(self):
        self.stack = []
        self.waiting = None
        self._open_root()

    def _open_root(self):
        self.stack.append(("设置", self._root_items(), 0))
        self.render()

    def _root_items(self):
        s = self.window.engine.settings
        angle_disp = {"DEG": "度", "RAD": "弧度", "GRA": "百分度"}[s.angle]
        disp_disp = {"NORM1": "NORM1", "NORM2": "NORM2",
                     "SCI": f"SCI {s.digits}", "FIX": f"FIX {s.digits}"}[s.display]
        return [
            ("角度单位", angle_disp, "choice", "angle",
             [("度", "DEG"), ("弧度", "RAD"), ("百分度", "GRA")]),
            ("显示格式", disp_disp, "choice", "display",
             [("NORM1", "NORM1"), ("NORM2", "NORM2"), ("SCI", "SCI"), ("FIX", "FIX")]),
            ("分数显示", "假分数" if s.fraction_type == "improper" else "带分数",
             "choice", "fraction_type",
             [("假分数", "improper"), ("带分数", "mixed")]),
            ("分数结果", "开" if s.fraction else "关", "choice", "fraction",
             [("开", True), ("关", False)]),
            ("复数", "开" if s.complex_mode else "关", "choice", "complex_mode",
             [("开", True), ("关", False)]),
            ("恢复初始设置", "", "action", "reset", None),
            ("关于", "", "action", "about", None),
        ]

    def render(self):
        if self.waiting:
            self.lb.setText(f"<b>{esc(self.waiting)} 显示位数</b><br>按 0~9 选择,AC 取消")
            return
        _title, items, sel = self.stack[-1]
        lines = ['<span style="font-size:10pt;font-weight:bold;">设置</span>']
        for i, (label, value, _t, _k, _x) in enumerate(items):
            if i == sel:
                lines.append('<div style="background:#33383f;color:#e8ece4;">'
                             f"▶ {esc(label)}　{esc(str(value))}</div>")
            else:
                lines.append(f'<div style="color:#22262b;">&nbsp;&nbsp;{esc(label)}　{esc(str(value))}</div>')
        self.lb.setText("<br>".join(lines))

    def handle_key(self, code, shifted):
        if self.waiting:
            if code in "0123456789":
                self.window.engine.set_setting("display", self.waiting)
                self.window.engine.set_setting("digits", int(code))
                self.window.save_settings()
                self.window.refresh_status()
                self.waiting = None
                if len(self.stack) > 1:
                    self.stack.pop()
                self.render()
            elif code == "ac":
                self.waiting = None
                self.render()
            return
        _title, items, sel = self.stack[-1]
        if code == "up":
            self.stack[-1] = (_title, items, max(0, sel - 1))
        elif code == "down":
            self.stack[-1] = (_title, items, min(len(items) - 1, sel + 1))
        elif code in ("ok", "exe"):
            self._activate(items[sel])
        self.render()

    def _activate(self, item):
        label, value, typ, key, extra = item
        eng = self.window.engine
        if typ == "choice":
            self.stack.append((label,
                               [(o_label, "", "set", key, o_val) for o_label, o_val in extra],
                               0))
        elif typ == "set":
            eng.set_setting(key, value)
            self.window.save_settings()
            self.window.refresh_status()
            if key == "display" and value in ("SCI", "FIX"):
                self.waiting = value
            else:
                self.stack.pop()
        elif typ == "action":
            if key == "reset":
                eng.reset_all()
                self.window.save_settings()
                self.window.refresh_status()
                self.stack = []
                self._open_root()
                QApplication.beep()
            elif key == "about":
                self.window.open_overlay("about")


# --------------------------------------------------------------------------
# 目录(函数目录 / 科学常数)
# --------------------------------------------------------------------------
class CatalogScreen(QWidget):
    def __init__(self, window, constants_only=False):
        super().__init__()
        self.window = window
        self.constants_only = constants_only
        self.page_name = "科学常数" if constants_only else "目录"
        self.cats = ["科学常数"] if constants_only else ["全部"] + [c for c, _ in CATALOG]
        self.cat_idx = 0
        self.pane = 1
        self.buffer = ""
        self.items = []
        self.sel = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        self.search = QLineEdit()
        self.search.setReadOnly(True)
        self.search.setPlaceholderText("搜索:直接键入或按数字键(0-9)")
        self.search.setFocusPolicy(Qt.NoFocus)
        v.addWidget(self.search)
        h = QHBoxLayout()
        self.cats_lw = QListWidget()
        self.cats_lw.setFixedWidth(120)
        self.cats_lw.itemClicked.connect(lambda _it: self._cat_clicked())
        h.addWidget(self.cats_lw)
        self.items_lw = QListWidget()
        self.items_lw.itemClicked.connect(lambda _it: self.insert())
        h.addWidget(self.items_lw, 1)
        v.addLayout(h, 1)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color:#4a5a4a;font-size:8pt;background:transparent;")
        v.addWidget(self.desc)

    def on_open(self):
        self.buffer = ""
        self.cat_idx = 0
        self.pane = 1
        self.sel = 0
        self.search.setText("")
        self._refresh_cats()
        self._refresh_items()

    def _refresh_cats(self):
        self.cats_lw.clear()
        for c in self.cats:
            self.cats_lw.addItem(c)
        self.cats_lw.setCurrentRow(self.cat_idx)

    def _cat_clicked(self):
        self.cat_idx = self.cats_lw.currentRow()
        self.pane = 1
        self.sel = 0
        self._refresh_items()

    def _all_items(self):
        out = []
        if self.constants_only:
            for cname, items in CATALOG:
                if cname == "科学常数":
                    return list(items)
            return out
        if self.cat_idx == 0:
            for cname, items in CATALOG:
                out.extend(items)
        else:
            out = list(CATALOG[self.cat_idx - 1][1])
        return out

    def _refresh_items(self):
        self.items = self._all_items()
        q = self.buffer.lower()
        if q:
            self.items = [it for it in self.items if q in it[0].lower()]
        self.items_lw.clear()
        for label, _ins, _desc in self.items:
            self.items_lw.addItem(label)
        self.sel = max(0, min(self.sel, len(self.items) - 1))
        if self.items:
            self.items_lw.setCurrentRow(self.sel)
        self._update_desc()

    def _update_desc(self):
        if self.items:
            self.desc.setText(esc(self.items[self.sel][2]))
        else:
            self.desc.setText("无匹配项")

    def handle_key(self, code, shifted, payload=None):
        if code == "char":
            self.buffer += payload
            self.search.setText(self.buffer)
            self._refresh_items()
            return
        if code in "0123456789" or code == "dot":
            self.buffer += code
            self.search.setText(self.buffer)
            self._refresh_items()
            return
        if code == "del":
            self.buffer = self.buffer[:-1]
            self.search.setText(self.buffer)
            self._refresh_items()
            return
        if code in ("up", "down"):
            d = -1 if code == "up" else 1
            if self.pane == 0:
                self.cat_idx = max(0, min(len(self.cats) - 1, self.cat_idx + d))
                self._refresh_cats()
                self.sel = 0
                self._refresh_items()
            else:
                self.sel = max(0, min(len(self.items) - 1, self.sel + d))
                self.items_lw.setCurrentRow(self.sel)
                self._update_desc()
            return
        if code in ("left", "right"):
            self.pane = 0 if code == "left" else 1
            return
        if code in ("ok", "exe"):
            self.insert()
            return

    def insert(self):
        if not self.items:
            QApplication.beep()
            return
        target = self.window.active_expr_target()
        if target is None:
            QApplication.beep()
            return
        target.insert_catalog(self.items[self.sel][1])
        self.window.close_overlay()


# --------------------------------------------------------------------------
# 工具
# --------------------------------------------------------------------------
class ToolsScreen(QWidget):
    ITEMS = [("科学常数", "const"), ("单位换算", "unit"),
             ("f(x)/g(x) 定义", "func"), ("关于", "about")]

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "工具"
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        self.lw = QListWidget()
        for label, _k in self.ITEMS:
            self.lw.addItem(label)
        self.lw.itemClicked.connect(lambda _it: self._open())
        v.addWidget(self.lw, 1)

    def on_open(self):
        self.lw.setCurrentRow(0)

    def _open(self):
        name = self.ITEMS[self.lw.currentRow()][1]
        self.window.open_overlay(name)

    def handle_key(self, code, shifted):
        if code == "up":
            self.lw.setCurrentRow(max(0, self.lw.currentRow() - 1))
        elif code == "down":
            self.lw.setCurrentRow(min(len(self.ITEMS) - 1, self.lw.currentRow() + 1))
        elif code in ("ok", "exe"):
            self._open()


# --------------------------------------------------------------------------
# 变量
# --------------------------------------------------------------------------
class VarScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "变量"
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        self.lw = QListWidget()
        self.lw.itemClicked.connect(lambda _it: self.insert_sel())
        v.addWidget(self.lw, 1)
        self.hint = QLabel()
        self.hint.setTextFormat(Qt.RichText)
        self.hint.setStyleSheet("color:#5a6a5a;font-size:7.5pt;background:transparent;")
        v.addWidget(self.hint)
        btns = QHBoxLayout()
        for label, fn in (("存入", self.store_sel), ("清零", self.clear_vars)):
            b = QPushButton(label)
            b.setObjectName("soft")
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)

    def on_open(self):
        self.refresh()
        self.hint.setText("OK=插入变量到表达式, SHIFT+OK=存入当前结果")

    def refresh(self):
        self.lw.clear()
        eng = self.window.engine
        for name in VARIABLES:
            self.lw.addItem(f"{name} = {eng.format_value(eng.vars[name])}")
        self.lw.setCurrentRow(0)

    def handle_key(self, code, shifted):
        if code == "up":
            self.lw.setCurrentRow(max(0, self.lw.currentRow() - 1))
        elif code == "down":
            self.lw.setCurrentRow(min(len(VARIABLES) - 1, self.lw.currentRow() + 1))
        elif code in ("ok", "exe"):
            if shifted:
                self.store_sel()
            else:
                self.insert_sel()

    def insert_sel(self):
        target = self.window.active_expr_target()
        if target is None:
            QApplication.beep()
            return
        target.insert_text(VARIABLES[self.lw.currentRow()])
        self.window.close_overlay()

    def _current_value(self):
        eng = self.window.engine
        t = self.window.active_expr_target()
        if t and t.expr.strip():
            try:
                v, _ = eng.evaluate(t.expr)
                return v
            except CalcError:
                return None
        b = self.window.base
        if hasattr(b, "last_value") and b.last_value is not None:
            return b.last_value
        return None

    def store_sel(self):
        name = VARIABLES[self.lw.currentRow()]
        v = self._current_value()
        if v is None:
            QApplication.beep()
            return
        self.window.engine.vars[name] = v
        self.refresh()
        self.hint.setText(f"已存入 {esc(name)} = {esc(self.window.engine.format_value(v))}")

    def clear_vars(self):
        self.window.engine.vars = {k: 0.0 for k in VARIABLES}
        self.refresh()
        QApplication.beep()


# --------------------------------------------------------------------------
# 用户函数 f(x)/g(x)
# --------------------------------------------------------------------------
class FuncScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "f(x)/g(x)"
        self.active = 0
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        h1 = QHBoxLayout()
        l1 = QLabel("f(x) =")
        l1.setStyleSheet("color:#101410;font-weight:bold;background:transparent;")
        h1.addWidget(l1)
        self.line_f = ExpressionLine(font_size=11)
        self.line_f.setFixedHeight(38)
        h1.addWidget(self.line_f, 1)
        v.addLayout(h1)
        h2 = QHBoxLayout()
        l2 = QLabel("g(x) =")
        l2.setStyleSheet("color:#101410;font-weight:bold;background:transparent;")
        h2.addWidget(l2)
        self.line_g = ExpressionLine(font_size=11)
        self.line_g.setFixedHeight(38)
        h2.addWidget(self.line_g, 1)
        v.addLayout(h2)
        self.hint = QLabel()
        self.hint.setTextFormat(Qt.RichText)
        self.hint.setStyleSheet("color:#5a6a5a;font-size:7.5pt;background:transparent;")
        v.addWidget(self.hint)
        btns = QHBoxLayout()
        for label, fn in (("保存 f", lambda: self.save_line(0)), ("保存 g", lambda: self.save_line(1)),
                          ("清除 f", lambda: self.clear_line(0)), ("清除 g", lambda: self.clear_line(1))):
            b = QPushButton(label)
            b.setObjectName("soft")
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)

    def on_open(self):
        self.line_f.set_expr(self.window.engine.f_expr or "")
        self.line_g.set_expr(self.window.engine.g_expr or "")
        self.active = 0
        self.hint.setText("自变量用 X,如 X^(2)+1;OK=保存当前行")

    def _active_line(self):
        return self.line_f if self.active == 0 else self.line_g

    def handle_key(self, code, shifted):
        if code in ("up", "down"):
            self.active = 1 if code == "down" else 0
            return
        if expr_insert_key(self._active_line(), code, shifted):
            return
        if code in ("ok", "exe"):
            self.save_line(self.active)

    def save_line(self, idx):
        line = self.line_f if idx == 0 else self.line_g
        expr = line.expr.strip()
        eng = self.window.engine
        if expr:
            old = eng.vars["X"]
            try:
                eng.evaluate(expr)
            except CalcError as err:
                self.hint.setText(f'<span style="color:#a32b2b;">{esc(err.msg)}</span>')
                QApplication.beep()
                return
            finally:
                eng.vars["X"] = old
        if idx == 0:
            eng.f_expr = expr or None
        else:
            eng.g_expr = expr or None
        self.hint.setText(f"已保存 {esc('f(x)' if idx == 0 else 'g(x)')} = {esc(expr or '(空)')}")

    def clear_line(self, idx):
        line = self.line_f if idx == 0 else self.line_g
        line.clear()
        if idx == 0:
            self.window.engine.f_expr = None
        else:
            self.window.engine.g_expr = None
        self.hint.setText(f"已清除 {esc('f(x)' if idx == 0 else 'g(x)')}")


# --------------------------------------------------------------------------
# 单位换算
# --------------------------------------------------------------------------
class UnitScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "单位换算"
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        v.setSpacing(4)
        g = QGridLayout()
        g.addWidget(QLabel("类别"), 0, 0)
        self.cat_cb = QComboBox()
        self.cat_cb.currentIndexChanged.connect(lambda _i: self._refresh_units())
        g.addWidget(self.cat_cb, 0, 1)
        g.addWidget(QLabel("从"), 1, 0)
        self.from_cb = QComboBox()
        g.addWidget(self.from_cb, 1, 1)
        g.addWidget(QLabel("到"), 2, 0)
        self.to_cb = QComboBox()
        g.addWidget(self.to_cb, 2, 1)
        g.addWidget(QLabel("数值"), 3, 0)
        self.value = QLineEdit()
        g.addWidget(self.value, 3, 1)
        v.addLayout(g)
        self.result = QLabel()
        self.result.setTextFormat(Qt.RichText)
        self.result.setWordWrap(True)
        self.result.setStyleSheet("background:transparent;color:#101410;font-size:10.5pt;font-weight:bold;")
        v.addWidget(self.result, 1)
        btns = QHBoxLayout()
        b = QPushButton("换算")
        b.setObjectName("soft")
        b.clicked.connect(self.convert)
        btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)

    def on_open(self):
        self.cat_cb.blockSignals(True)
        self.cat_cb.clear()
        self.cat_cb.addItems(list(UNITS.keys()))
        self.cat_cb.blockSignals(False)
        self._refresh_units()
        self.value.setText(self.window.engine.format_value(self.window.engine.ans))
        self.result.setText("")

    def _refresh_units(self):
        units = list(UNITS[self.cat_cb.currentText()].keys())
        self.from_cb.clear()
        self.to_cb.clear()
        self.from_cb.addItems(units)
        self.to_cb.addItems(units)
        if len(units) > 1:
            self.to_cb.setCurrentIndex(1)

    def handle_key(self, code, shifted):
        if code in ("ok", "exe"):
            self.convert()

    def convert(self):
        eng = self.window.engine
        try:
            v = float(self.value.text().replace("−", "-"))
        except ValueError:
            self.result.setText('<span style="color:#a32b2b;">数值无效</span>')
            QApplication.beep()
            return
        frm = self.from_cb.currentText()
        to = self.to_cb.currentText()
        try:
            r = eng.convert_unit(self.cat_cb.currentText(), v, frm, to)
        except CalcError as err:
            self.result.setText(f'<span style="color:#a32b2b;">{esc(err.msg)}</span>')
            QApplication.beep()
            return
        self.result.setText(f"{esc(eng.format_value(v))} {esc(frm)} = "
                            f"<b>{esc(eng.format_value(r))}</b> {esc(to)}")


# --------------------------------------------------------------------------
# 显示格式(格式键)
# --------------------------------------------------------------------------
class FormatScreen(QWidget):
    ITEMS = ["NORM1", "NORM2", "SCI", "FIX"]

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "显示格式"
        self.wants_ac = True
        self.sel = 0
        self.waiting = None
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        self.lb = QLabel()
        self.lb.setTextFormat(Qt.RichText)
        self.lb.setStyleSheet("background:transparent;color:#101410;")
        self.lb.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        v.addWidget(self.lb, 1)
        hint = QLabel("↑↓ 选择 · OK 确定 · SCI/FIX 后按 0-9 选位数")
        hint.setStyleSheet("color:#5a6a5a;font-size:7.5pt;background:transparent;")
        v.addWidget(hint)

    def on_open(self):
        self.sel = 0
        self.waiting = None
        self.render()

    def render(self):
        eng = self.window.engine.settings
        if self.waiting:
            self.lb.setText(f"<b>{esc(self.waiting)} 显示位数</b><br>按 0~9 选择,AC 取消")
            return
        lines = ['<span style="font-size:10pt;font-weight:bold;">显示格式</span>']
        for i, item in enumerate(self.ITEMS):
            cur = "●" if eng.display == item else "　"
            if i == self.sel:
                lines.append(f'<div style="background:#33383f;color:#e8ece4;">▶ {esc(item)}　{cur}</div>')
            else:
                lines.append(f'<div style="color:#22262b;">&nbsp;&nbsp;{esc(item)}　{cur}</div>')
        self.lb.setText("<br>".join(lines))

    def handle_key(self, code, shifted):
        if self.waiting:
            if code in "0123456789":
                self.window.engine.set_setting("display", self.waiting)
                self.window.engine.set_setting("digits", int(code))
                self.window.save_settings()
                self.window.refresh_status()
                self.window.close_overlay()
            elif code == "ac":
                self.waiting = None
                self.render()
            return
        if code == "up":
            self.sel = max(0, self.sel - 1)
        elif code == "down":
            self.sel = min(len(self.ITEMS) - 1, self.sel + 1)
        elif code in ("ok", "exe"):
            item = self.ITEMS[self.sel]
            if item in ("NORM1", "NORM2"):
                self.window.engine.set_setting("display", item)
                self.window.save_settings()
                self.window.refresh_status()
                self.window.close_overlay()
            else:
                self.waiting = item
        self.render()


# --------------------------------------------------------------------------
# 关于
# --------------------------------------------------------------------------
class AboutScreen(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.page_name = "关于"
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 2, 4, 2)
        self.lb = QLabel()
        self.lb.setTextFormat(Qt.RichText)
        self.lb.setWordWrap(True)
        self.lb.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lb.setStyleSheet("background:transparent;color:#101410;")
        self.lb.setText(
            "<b>CASIO fx-991CN CW 计算器模拟器</b> v1.0<br><br>"
            "六大应用:计算 / 统计 / 函数表格 / 方程 / 不等式 / 复数<br><br>"
            "特性:自然书写表达式、隐式乘法、分数与带分数、六十进制、科学记数、"
            "变量 A-F/X/Y/Z/M 与 Ans、用户函数 f(x)/g(x)、科学常数、单位换算、"
            "显示格式 NORM/SCI/FIX、S⇔D 分数/小数/度分秒切换<br><br>"
            "按键:SHIFT+DEL 关机 · SHIFT+AC 清除全部变量 · SHIFT+数字 输入变量 · "
            "▲▼ 查看历史 · SHIFT+格式(S⇔D) 切换显示形式<br><br>"
            "键盘:数字与运算符直接输入,Enter=EXE,退格=DEL,Esc=AC,方向键=十字键,"
            "Shift=SHIFT,目录打开时字母可搜索")
        v.addWidget(self.lb, 1)
        b = QPushButton("关闭")
        b.setObjectName("soft")
        b.clicked.connect(self.window.close_overlay)
        h = QHBoxLayout()
        h.addStretch(1)
        h.addWidget(b)
        v.addLayout(h)

    def on_open(self):
        pass

    def handle_key(self, code, shifted):
        pass


class OffPage(QWidget):
    def __init__(self):
        super().__init__()
        self.page_name = ""
        self.setStyleSheet("background:#101215;")

    def on_open(self):
        pass

    def handle_key(self, code, shifted):
        pass


# --------------------------------------------------------------------------
# 主窗口
# --------------------------------------------------------------------------
class CalculatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle("CASIO fx-991CN CW 模拟器")
        self.engine = CalcEngine()
        self.qs = QSettings("CasioSimulator", "fx991CNCW")
        self.load_settings()
        self.powered = True
        self.shift_latch = False
        self.ins_mode = True
        self.overlays = []
        self.buttons = {}
        self._build_ui()
        self.base = self.pages["menu"]
        self.open_app("menu")

    # ---------------- UI 搭建 ----------------
    def _build_ui(self):
        self.setStyleSheet("""
            QWidget#root { background: #1b1d20; }
            QFrame#body { background: #23262b; border: 1px solid #0e1013; border-radius: 16px; }
            QLabel#model { color: #9aa2ac; font-size: 8pt; }
            QLabel#classwiz { color: #707985; font-size: 8pt; }
            QFrame#lcd { background: #cdd6c2; border: 1px solid #0a0c0e; border-radius: 8px; }
            QPushButton#soft { background:#31353b; color:#e8ece4; border-radius:4px;
                               padding:2px 10px; font-size:8.5pt; }
            QPushButton#soft:hover { background:#3d4147; }
            QLineEdit, QTableWidget, QComboBox, QListWidget {
                background:#dde4d4; color:#15181c; border:1px solid #8a9382;
                border-radius:3px; selection-background-color:#3d6ea5;
                selection-color:#ffffff; font-size:9pt; }
        """)
        self.setFixedSize(500, 790)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 10)
        outer.setSpacing(0)
        body = QFrame()
        body.setObjectName("body")
        outer.addWidget(body)
        b = QVBoxLayout(body)
        b.setContentsMargins(16, 9, 16, 12)
        b.setSpacing(4)
        self.solar = SolarPanel()
        self.solar.setFixedHeight(14)
        b.addWidget(self.solar)
        mr = QHBoxLayout()
        ml = QLabel("fx-991CN CW")
        ml.setObjectName("model")
        mrr = QLabel("CLASSWIZ")
        mrr.setObjectName("classwiz")
        mr.addWidget(ml)
        mr.addStretch(1)
        mr.addWidget(mrr)
        b.addLayout(mr)
        self.lcd = LCDScreen()
        self.lcd.setFixedHeight(236)
        b.addWidget(self.lcd)
        b.addLayout(self._top_row())
        b.addLayout(self._mid_row())
        b.addLayout(self._main_grid())
        b.addStretch(1)
        self._build_pages()

    def _add_key(self, code, main, sub, w, h, base="#3a3d43", sub_color="#8fb8f0",
                 main_color="#f2f2f2", main_size=9.5, sub_size=6.5):
        btn = KeyButton(main, sub, code, base=base, sub_color=sub_color,
                        main_color=main_color, main_size=main_size,
                        sub_size=sub_size, w=w, h=h)
        btn.clicked.connect(lambda _c=False, c=code: self._key(c))
        self.buttons[code] = btn
        return btn

    def _top_row(self):
        h = QHBoxLayout()
        h.setSpacing(6)
        h.addWidget(self._add_key("on", "开机", "", 50, 36, base="#26282c", main_size=8))
        h.addWidget(self._add_key("home", "主屏幕", "", 76, 36, main_size=8))
        h.addWidget(self._add_key("settings", "设置", "≡", 76, 36, main_size=8))
        h.addStretch(1)
        h.addWidget(self._add_key("catalog", "目录", "▤", 76, 36, main_size=8))
        h.addWidget(self._add_key("tools", "工具", "⋮", 76, 36, main_size=8))
        return h

    def _mid_row(self):
        h = QHBoxLayout()
        h.setSpacing(8)
        h.addWidget(self._add_key("var", "变量", "x", 72, 34, main_size=8))
        h.addWidget(self._add_key("func", "功能", "f(x)", 72, 34, main_size=8))
        h.addStretch(1)
        dp = QGridLayout()
        dp.setSpacing(3)
        dp.addWidget(self._add_key("up", "▲", "", 38, 30, main_size=8), 0, 1)
        dp.addWidget(self._add_key("left", "◀", "", 38, 30, main_size=8), 1, 0)
        dp.addWidget(self._add_key("ok", "OK", "", 46, 34, base="#3f4349", main_size=8), 1, 1)
        dp.addWidget(self._add_key("right", "▶", "", 38, 30, main_size=8), 1, 2)
        dp.addWidget(self._add_key("down", "▼", "", 38, 30, main_size=8), 2, 1)
        dw = QWidget()
        dw.setLayout(dp)
        h.addWidget(dw)
        h.addStretch(1)
        sv = QVBoxLayout()
        sv.setSpacing(3)
        sv.addWidget(self._add_key("scroll_up", "▲", "", 34, 26, main_size=7.5))
        sv.addWidget(self._add_key("scroll_down", "▼", "", 34, 26, main_size=7.5))
        sw = QWidget()
        sw.setLayout(sv)
        h.addWidget(sw)
        return h

    def _main_grid(self):
        specs = {
            "neg": ("(−)", "", "#3a3d43", "#f2f2f2"),
            "sin": ("sin", "sin⁻¹", "#3a3d43", "#f2f2f2"),
            "cos": ("cos", "cos⁻¹", "#3a3d43", "#f2f2f2"),
            "tan": ("tan", "tan⁻¹", "#3a3d43", "#f2f2f2"),
            "lparen": ("(", "", "#3a3d43", "#f2f2f2"),
            "rparen": (")", "", "#3a3d43", "#f2f2f2"),
            "7": ("7", "A", "#43474e", "#f2f2f2"),
            "8": ("8", "B", "#43474e", "#f2f2f2"),
            "9": ("9", "C", "#43474e", "#f2f2f2"),
            "4": ("4", "D", "#43474e", "#f2f2f2"),
            "5": ("5", "E", "#43474e", "#f2f2f2"),
            "6": ("6", "F", "#43474e", "#f2f2f2"),
            "1": ("1", "X", "#43474e", "#f2f2f2"),
            "2": ("2", "Y", "#43474e", "#f2f2f2"),
            "3": ("3", "Z", "#43474e", "#f2f2f2"),
            "0": ("0", "", "#43474e", "#f2f2f2"),
            "dot": (".", "", "#43474e", "#f2f2f2"),
            "ins": ("插入", "", "#3a3d43", "#f2f2f2"),
            "del": ("DEL", "关机", "#3a3d43", "#f2f2f2"),
            "ac": ("AC", "清除全部", "#3a3d43", "#ff9b8a"),
            "mul": ("×", "", "#3a3d43", "#f2f2f2"),
            "div": ("÷", "", "#3a3d43", "#f2f2f2"),
            "add": ("+", "", "#3a3d43", "#f2f2f2"),
            "sub": ("−", "", "#3a3d43", "#f2f2f2"),
            "shift": ("SHIFT", "", "#2e63a8", "#ffd76a"),
            "exp10": ("×10", "x", "#3a3d43", "#f2f2f2"),
            "ans": ("Ans", "", "#3a3d43", "#f2f2f2"),
            "fmt": ("格式", "S⇔D", "#3a3d43", "#f2f2f2"),
            "exe": ("EXE", "", "#a87b35", "#ffffff"),
        }
        rows = [
            [("neg", 1), ("sin", 2), ("cos", 3), ("tan", 4), ("lparen", 5), ("rparen", 6)],
            [("7", 1), ("8", 2), ("9", 3), ("ins", 4), ("del", 5), ("ac", 6)],
            [("4", 1), ("5", 2), ("6", 3), ("mul", 4), ("div", 5)],
            [("1", 1), ("2", 2), ("3", 3), ("add", 4), ("sub", 5)],
            [("shift", 0), ("0", 1), ("dot", 2), ("exp10", 3), ("ans", 4), ("fmt", 5), ("exe", 6)],
        ]
        g = QGridLayout()
        g.setSpacing(6)
        for ri, row in enumerate(rows):
            for code, col in row:
                main, sub, base, mcolor = specs[code]
                g.addWidget(self._add_key(code, main, sub, 53, 46,
                                          base=base, main_color=mcolor), ri, col)
        return g

    def _build_pages(self):
        self.pages = {}
        def add(key, widget):
            widget.page_name = key
            self.pages[key] = widget
            self.lcd.add_page(widget)
        add("off", OffPage())
        add("menu", MenuScreen(self))
        add("calc", CalcScreen(self))
        add("complex", CalcScreen(self, complex_app=True))
        add("stats", StatsScreen(self))
        add("table", TableScreen(self))
        add("equation", EquationScreen(self))
        add("inequality", InequalityScreen(self))
        add("settings", SettingsScreen(self))
        add("catalog", CatalogScreen(self))
        add("const", CatalogScreen(self, constants_only=True))
        add("tools", ToolsScreen(self))
        add("var", VarScreen(self))
        add("func", FuncScreen(self))
        add("unit", UnitScreen(self))
        add("about", AboutScreen(self))
        add("format", FormatScreen(self))
        titles = {"menu": "主屏幕", "calc": "计算", "complex": "复数", "stats": "统计",
                  "table": "函数表格", "equation": "方程", "inequality": "不等式",
                  "settings": "设置", "catalog": "目录", "const": "科学常数",
                  "tools": "工具", "var": "变量", "func": "f(x)/g(x)",
                  "unit": "单位换算", "about": "关于", "format": "显示格式", "off": ""}
        for k, w in self.pages.items():
            w.page_name = titles.get(k, k)

    # ---------------- 导航 ----------------
    def open_app(self, name):
        prev = self.base if hasattr(self, "base") else None
        if prev is self.pages.get("complex") and name != "complex":
            self.engine.settings.complex_mode = self._load_bool("complex_mode", False)
        self.base = self.pages[name]
        self.overlays = []
        self.base.on_open()
        self.lcd.show_page(self.base)
        self.refresh_status()

    def open_overlay(self, name):
        page = self.pages[name]
        page.on_open()
        self.overlays.append(page)
        self.lcd.show_page(page)
        self.refresh_status()

    def close_overlay(self):
        if self.overlays:
            self.overlays.pop()
            w = self.overlays[-1] if self.overlays else self.base
            self.lcd.show_page(w)
            self.refresh_status()

    def active_expr_target(self):
        b = self.base
        name = b.__class__.__name__
        if name == "CalcScreen":
            return b.expr
        if name == "TableScreen":
            return b.expr
        return None

    def power_off(self):
        self.powered = False
        self.overlays = []
        self.lcd.show_page(self.pages["off"])
        self.lcd.set_status("", "")

    def power_on(self):
        self.powered = True
        self.open_app("menu")

    def clear_memory(self):
        self.engine.reset_memory()
        for key in ("calc", "complex"):
            self.pages[key].history = []
            self.pages[key].last_value = None
            self.pages[key].clear_input()
        QApplication.beep()
        self.refresh_status()

    def toggle_ins(self):
        self.ins_mode = not self.ins_mode
        for line in (self.pages["calc"].expr, self.pages["complex"].expr,
                     self.pages["table"].expr,
                     self.pages["func"].line_f, self.pages["func"].line_g):
            line.overwrite = not self.ins_mode
        self.refresh_status()

    def refresh_status(self):
        s = self.engine.settings
        parts = []
        if self.shift_latch:
            parts.append('<span style="color:#b00000;font-weight:bold;">S</span>')
        parts.append("D" if s.angle == "DEG" else ("R" if s.angle == "RAD" else "G"))
        d = s.display + (str(s.digits) if s.display in ("SCI", "FIX") else "")
        parts.append(d)
        if s.complex_mode:
            parts.append("i")
        if not self.ins_mode:
            parts.append("改写")
        top = self.overlays[-1] if self.overlays else None
        page = top if top is not None else self.base
        title = getattr(page, "page_name", "")
        self.lcd.set_status(" ".join(parts), esc(title))

    # ---------------- 设置持久化 ----------------
    def _load_bool(self, key, default):
        v = self.qs.value(key)
        if v is None:
            return default
        return str(v).lower() in ("true", "1")

    def load_settings(self):
        s = self.engine.settings
        s.angle = str(self.qs.value("angle", "DEG"))
        s.display = str(self.qs.value("display", "NORM1"))
        s.fraction_type = str(self.qs.value("fraction_type", "improper"))
        try:
            s.digits = int(self.qs.value("digits", 2))
        except (TypeError, ValueError):
            s.digits = 2
        s.fraction = self._load_bool("fraction", True)
        s.complex_mode = self._load_bool("complex_mode", False)

    def save_settings(self):
        s = self.engine.settings
        for k in ("angle", "display", "fraction_type"):
            self.qs.setValue(k, getattr(s, k))
        self.qs.setValue("digits", s.digits)
        self.qs.setValue("fraction", s.fraction)
        self.qs.setValue("complex_mode", s.complex_mode)

    # ---------------- 按键路由 ----------------
    def _key(self, code):
        shifted = self.shift_latch
        if code != "shift":
            self.shift_latch = False
            self._refresh_shift_ui()
        else:
            self.shift_latch = not self.shift_latch
            self._refresh_shift_ui()
        self.handle_key(code, shifted)

    def _refresh_shift_ui(self):
        b = self.buttons.get("shift")
        if b:
            b.set_lit(self.shift_latch)
        self.refresh_status()

    def handle_key(self, code, shifted, payload=None):
        if not self.powered:
            if code == "on":
                self.power_on()
            return
        if code == "on":
            return
        if code == "del" and shifted:
            self.power_off()
            return
        if code == "ac" and shifted:
            self.clear_memory()
            return
        top = self.overlays[-1] if self.overlays else None
        if top is not None and isinstance(top, CatalogScreen) and \
                (code in "0123456789." or code == "char"):
            top.handle_key(code, shifted, payload)
            return
        if self.route_to_editor(code, shifted):
            return
        if code == "home":
            self.overlays = []
            self.open_app("menu")
            return
        if code == "settings":
            if top is not None and isinstance(top, SettingsScreen):
                self.close_overlay()
            else:
                self.open_overlay("settings")
            return
        if code == "catalog":
            if top is not None and isinstance(top, CatalogScreen):
                self.close_overlay()
            else:
                self.open_overlay("catalog")
            return
        if code == "tools":
            if top is not None and isinstance(top, ToolsScreen):
                self.close_overlay()
            else:
                self.open_overlay("tools")
            return
        if code == "var":
            if top is not None and isinstance(top, VarScreen):
                self.close_overlay()
            else:
                self.open_overlay("var")
            return
        if code == "func":
            if top is not None and isinstance(top, FuncScreen):
                self.close_overlay()
            else:
                self.open_overlay("func")
            return
        if code == "fmt" and not shifted:
            self.open_overlay("format")
            return
        if code == "ac":
            if top is not None:
                if getattr(top, "wants_ac", False):
                    top.handle_key(code, shifted)
                else:
                    self.close_overlay()
            else:
                self.base.handle_key(code, shifted)
            return
        if top is not None:
            if isinstance(top, CatalogScreen):
                top.handle_key(code, shifted, payload)
            else:
                top.handle_key(code, shifted)
            return
        self.base.handle_key(code, shifted)

    def route_to_editor(self, code, shifted):
        fw = QApplication.focusWidget()
        if fw is None:
            return False
        if isinstance(fw, QLineEdit):
            ch = self._code_char(code)
            if ch is not None:
                fw.insert(ch)
                return True
            if code == "del":
                fw.backspace()
                return True
            if code == "ac":
                fw.clear()
                return True
            if code in ("exe", "ok"):
                fw.clearFocus()
                return False
            return False
        if isinstance(fw, QTableWidget):
            ch = self._code_char(code)
            if ch is not None:
                idx = fw.currentIndex()
                if idx.isValid():
                    fw.editItem(idx)
                    QApplication.processEvents()
                    ed = QApplication.focusWidget()
                    if isinstance(ed, QLineEdit):
                        ed.insert(ch)
                    return True
                return True
            if code in ("del", "ac"):
                idx = fw.currentIndex()
                if idx.isValid():
                    fw.setItem(idx.row(), idx.column(), QTableWidgetItem(""))
                return True
            if code in ("exe", "ok"):
                fw.clearFocus()
                return False
            return False
        return False

    @staticmethod
    def _code_char(code):
        if code in "0123456789":
            return code
        if code == "dot":
            return "."
        if code == "neg":
            return "-"
        if code == "add":
            return "+"
        if code == "sub":
            return "-"
        return None

    # ---------------- 物理键盘 ----------------
    def keyPressEvent(self, e):
        fw = QApplication.focusWidget()
        if isinstance(fw, (QLineEdit, QTableWidget, QComboBox)) and \
                e.key() != Qt.Key_Escape:
            super().keyPressEvent(e)
            return
        code = self._map_key(e)
        if code is None:
            txt = e.text()
            if txt and txt.isprintable():
                top = self.overlays[-1] if self.overlays else None
                if top is not None and isinstance(top, CatalogScreen):
                    self.handle_key("char", False, txt)
                    e.accept()
                    return
            super().keyPressEvent(e)
            return
        if code == "shift_toggle":
            self.shift_latch = not self.shift_latch
            self._refresh_shift_ui()
            e.accept()
            return
        self.handle_key(code, False)
        e.accept()

    @staticmethod
    def _map_key(e):
        k = e.key()
        m = {
            Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3",
            Qt.Key_4: "4", Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7",
            Qt.Key_8: "8", Qt.Key_9: "9", Qt.Key_Period: "dot",
            Qt.Key_Plus: "add", Qt.Key_Minus: "sub", Qt.Key_Asterisk: "mul",
            Qt.Key_Slash: "div", Qt.Key_ParenLeft: "lparen",
            Qt.Key_ParenRight: "rparen", Qt.Key_Return: "exe",
            Qt.Key_Enter: "exe", Qt.Key_Equal: "exe",
            Qt.Key_Backspace: "del", Qt.Key_Delete: "del",
            Qt.Key_Escape: "ac", Qt.Key_Up: "up", Qt.Key_Down: "down",
            Qt.Key_Left: "left", Qt.Key_Right: "right",
            Qt.Key_PageUp: "scroll_up", Qt.Key_PageDown: "scroll_down",
            Qt.Key_Shift: "shift_toggle", Qt.Key_AsciiCircum: "power",
            Qt.Key_Exclam: "fact", Qt.Key_Percent: "pct",
        }
        return m.get(k)
