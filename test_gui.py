# -*- coding: utf-8 -*-
"""离屏 GUI 冒烟测试:驱动各界面并截图"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.stdout.reconfigure(encoding="utf-8")

from PySide6.QtWidgets import QApplication, QTableWidgetItem
from PySide6.QtGui import QFont

app = QApplication(sys.argv)
f = QFont("Microsoft YaHei UI", 9)
app.setFont(f)

from ui_screens import CalculatorWindow

w = CalculatorWindow()
w.show()
app.processEvents()

os.makedirs("shots", exist_ok=True)

def key(code, shifted=False):
    w.handle_key(code, shifted)
    app.processEvents()

def shot(name):
    w.grab().save(os.path.join("shots", name + ".png"))
    print("shot:", name)

def set_cell(table, r, c, text):
    table.setItem(r, c, QTableWidgetItem(text))

# 1. 主菜单
shot("00_menu")
# 2. 计算:1+2×3
key("exe")
key("1"); key("add"); key("2"); key("mul"); key("3")
shot("01_expr")
key("exe")
shot("02_result")
# 3. sin(30) 与分数
key("ac")
key("sin"); key("3"); key("0"); key("rparen"); key("exe")
shot("03_sin")
key("ac")
key("1"); key("div"); key("3"); key("exe")
key("fmt")   # 格式快速菜单
shot("04_format")
key("ac")    # 关闭
# 4. 目录
key("catalog")
shot("05_catalog")
key("ac")
# 5. 设置
key("settings")
key("down")
shot("06_settings")
key("settings")   # 关闭
# 6. 统计
key("home")
key("right"); key("exe")   # 统计
shot("07_stats_mode")
key("exe")                 # 进入 1-VAR
st = w.pages["stats"]
for r, (x, fr) in enumerate([("1", ""), ("2", "2"), ("3", "")]):
    set_cell(st.table, r, 0, x)
    set_cell(st.table, r, 1, fr)
st.compute()
shot("08_stats_results")
# 7. 方程(二次)
key("home")
key("right"); key("right"); key("right"); key("exe")  # 方程
key("right"); key("right"); key("right"); key("exe")  # 二次方程
eq = w.pages["equation"]
set_cell(eq.table, 0, 0, "1"); set_cell(eq.table, 0, 1, "-5"); set_cell(eq.table, 0, 2, "6")
eq.solve()
shot("09_equation")
# 8. 函数表格
key("home")
key("right"); key("right"); key("exe")   # 函数表格
tb = w.pages["table"]
tb.expr.set_expr("X^(2)+1")
tb.generate()
shot("10_table")
# 9. 不等式(二次 > )
key("home")
key("right"); key("right"); key("right"); key("right"); key("exe")  # 不等式
key("exe")       # 二次
key("exe")       # >
iq = w.pages["inequality"]
set_cell(iq.table, 0, 0, "1"); set_cell(iq.table, 0, 1, "-5"); set_cell(iq.table, 0, 2, "6")
iq.solve()
shot("11_inequality")
# 10. 复数
key("home")
key("right"); key("right"); key("right"); key("right"); key("right"); key("exe")  # 复数
key("lparen"); key("3"); key("add"); key("4"); key("i_pad")  # 用目录插入 i 较繁,直接键入
w.pages["complex"].expr.set_expr("(3+4i)(1+i)")
w.pages["complex"].evaluate()
shot("12_complex")
# 11. 变量
key("var")
shot("13_var")
key("var")   # 关闭
# 12. 工具→单位换算
key("tools")
key("down"); key("exe")
shot("14_unit")
key("ac")
# 13. 功能 f(x)/g(x)
key("func")
w.pages["func"].line_f.set_expr("X^(2)+1")
w.pages["func"].save_line(0)
shot("15_func")
key("func")
# 14. 关机
key("shift"); key("del")
shot("16_off")
key("on")
shot("17_on")
print("DONE")
