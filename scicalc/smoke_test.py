# -*- coding: utf-8 -*-
"""科学计算器 —— GUI 冒烟测试(离屏运行,不弹窗口)

运行:python smoke_test.py
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")   # 离屏运行

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

import main as app_main  # noqa: E402


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print(f"  ✓ {msg}")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    qt_app = QApplication([])
    win = app_main.CalculatorWindow()
    win.show()

    # 测试确定性:显式设定初始状态,不依赖上次运行遗留的持久化设置
    win._angle = "DEG"
    win._angle_btn.setText("DEG")
    win._history.clear_all()
    win._memory_clear()
    win._clear()

    # 1. 基本四则与括号:7×(5+3) = 56
    for t in ("7", "×", "(", "5", "+", "3", ")"):
        win._insert(t)
    win._equals()
    check(win._result_label.text() == "56", f"7×(5+3) = {win._result_label.text()}(期望 56)")
    check(win._result_mode and win._history.count >= 1, "结果态且历史已记录")

    # 2. 结果态下按运算符以 ans 续算:+1 → 57
    win._insert("+")
    win._insert("1")
    check(win._expr == "ans+1", f"ans 续算表达式为 {win._expr!r}")
    win._equals()
    check(win._result_label.text() == "57", f"ans+1 = {win._result_label.text()}(期望 57)")

    # 3. 三角函数(DEG):sin90 = 1
    win._clear()
    for ch in "sin90":
        win._insert(ch)
    win._equals()
    check(win._result_label.text() == "1", f"sin90(DEG) = {win._result_label.text()}(期望 1)")

    # 4. 实时预览:输入 2^10 不按等号,预览显示 1024
    win._clear()
    for ch in "2^10":
        win._insert(ch)
    win._preview_timer.timeout.emit() if False else win._refresh_preview()
    check(win._result_label.text() == "1024", f"预览 2^10 = {win._result_label.text()}(期望 1024)")

    # 5. 除零错误提示
    win._clear()
    win._insert("5")
    win._insert("÷")
    win._insert("0")
    win._equals()
    check(win._error_mode and win._result_label.text() == "除数不能为零",
          f"除零提示:{win._result_label.text()}")
    win._insert("1")                        # 错误态继续输入自动恢复
    check(not win._error_mode, "错误态输入后自动恢复")

    # 6. 智能退格:sin( 整体删除
    win._clear()
    for t in ("sin(", "5"):
        win._insert(t)
    check(win._expr == "sin(5", f"插入后表达式 {win._expr!r}")
    win._backspace()                        # 删 5
    check(win._expr == "sin(", "退格删除一位")
    win._backspace()                        # 整体删 sin(
    check(win._expr == "", "函数名整体删除")

    # 7. 连按运算符替换:5 + + → 5 +
    win._clear()
    win._insert("5")
    win._insert("+")
    win._insert("+")
    check(win._expr == "5+", "连按运算符被替换")

    # 8. ± 切换末尾数字符号
    win._clear()
    for ch in "12":
        win._insert(ch)
    win._plusminus()
    check(win._expr == "−12", f"取负:{win._expr!r}")
    win._plusminus()
    check(win._expr == "12", "还原正数")

    # 9. 内存:M+ 累加、MR 召回
    win._clear()
    for ch in "123":
        win._insert(ch)
    win._memory_add()
    check(win._memory == 123.0, f"M+ 后内存 {win._memory}")
    win._clear()
    win._memory_recall()
    check(win._expr == "m", f"MR 召回:{win._expr!r}")
    win._memory_clear()
    check(win._memory == 0.0, "MC 清除内存")

    # 10. 科学按键与 2nd 切换
    sci_btns = win._sci_specs
    check(len(sci_btns) == 6, f"2nd 可切换按键数量 {len(sci_btns)}(期望 6)")
    win._clear()
    win._insert("√(")
    win._insert("9")
    win._insert(")")
    win._equals()
    check(win._result_label.text() == "3", f"√(9) = {win._result_label.text()}")

    # 11. 历史面板
    check(win._history.count >= 3, f"历史条目数 {win._history.count}")
    win._history.clear_all()
    check(win._history.count == 0, "清空历史")

    # 12. 主题切换
    win.apply_theme("dark")
    check(win._theme_name == "dark", "切换深色主题")
    win.apply_theme("light")
    check(win._theme_name == "light", "切回浅色主题")

    # 13. 键盘输入映射
    win._clear()
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    for key, text in ((Qt.Key_8, "8"), (Qt.Key_Slash, "/"), (Qt.Key_2, "2")):
        win.keyPressEvent(QKeyEvent(QEvent.KeyPress, key, Qt.KeyboardModifier.NoModifier, text))
    check(win._expr == "8÷2", f"键盘输入映射:{win._expr!r}")
    win.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.KeyboardModifier.NoModifier, "\r"))
    check(win._result_label.text() == "4", f"回车求值:{win._result_label.text()}")

    # 14. 复制
    win._copy_result()
    check(QApplication.clipboard().text() == "4", "复制结果到剪贴板")

    # 15. 函数图像窗口
    import plot as plot_mod

    win._open_graph()
    check(win._graph_window is not None, "图像窗口已创建")
    gw = win._graph_window
    gw.show()
    gw._replot()

    # 默认输入:二次函数(显函数)
    check(len(gw._curves) == 1 and gw._curves[0].kind == plot_mod.EXPLICIT,
          f"默认输入应识别为显函数,实际 {[c.kind for c in gw._curves]}")
    check(sum(len(s.polylines) for s in gw._canvas._samples) > 0, "二次函数采样出折线")

    # 圆(隐函数)
    gw._apply_example("x^2 + y^2 = 25")
    check(gw._curves[0].kind == plot_mod.IMPLICIT, "圆应识别为隐函数")
    check(len(gw._canvas._samples[0].segments) > 50,
          f"圆应产生轮廓线段,实际 {len(gw._canvas._samples[0].segments)}")

    # 双曲线(隐函数)
    gw._apply_example("x^2/4 - y^2/9 = 1")
    check(gw._curves[0].kind == plot_mod.IMPLICIT and len(gw._canvas._samples[0].segments) > 20,
          "双曲线应产生轮廓线段")

    # 参数方程
    gw._apply_example("x = 3cos(t), y = 2sin(t)")
    check(gw._curves[0].kind == plot_mod.PARAMETRIC, "参数方程识别")
    check(sum(len(p) for p in gw._canvas._samples[0].polylines) > 1000, "参数椭圆采样点充足")

    # 极坐标
    gw._apply_example("r = 1 - sin(θ)")
    check(gw._curves[0].kind == plot_mod.POLAR, "极坐标识别")
    check(len(gw._canvas._samples[0].polylines) >= 1, "心形线采样出折线")

    # 多曲线 + 错误提示
    gw._input.setPlainText("y=sin(x)\ny=cos(x)\n乱写乱写")
    gw._replot()
    check(len(gw._curves) == 2, f"多曲线解析得到 {len(gw._curves)} 条(期望 2)")
    check("第 3 行" in gw._status.text(), f"错误行提示:{gw._status.text()!r}")

    # 缩放 / 平移 / 重置视图
    view_before = gw._canvas.view
    gw._canvas._view = view_before.scaled(0.5, 0.0, 0.0).with_aspect(
        gw._canvas.width(), gw._canvas.height())
    check(abs(gw._canvas.view.width - view_before.width * 0.5) < 1e-6, "缩放改变视口宽度")
    gw._canvas.reset_view()
    check(abs(gw._canvas.view.width - 20.0) < 1e-6,
          f"重置视图宽度应为 20,实际 {gw._canvas.view.width}")

    # 渲染:画布上应出现网格 / 坐标轴 / 曲线等多种颜色
    image = gw._canvas.grab().toImage()
    check(image.width() > 100 and image.height() > 100, "画布渲染尺寸正常")
    colors_seen = set()
    for y_px in range(0, image.height(), 7):
        for x_px in range(0, image.width(), 7):
            colors_seen.add(image.pixel(x_px, y_px))
    check(len(colors_seen) > 5, f"画布应出现多种颜色,实际 {len(colors_seen)} 种")

    # 主题同步
    win.apply_theme("dark")
    check(gw._theme_name == "dark", "图像窗口跟随主窗口切换深色")
    win.apply_theme("light")
    check(gw._theme_name == "light", "图像窗口跟随主窗口切回浅色")

    # 恢复默认设置,避免测试残留
    win._settings.setValue("theme", "light")
    win._settings.setValue("angle", "DEG")
    win._settings.setValue("memory", 0.0)
    win._settings.setValue("hist_visible", False)

    print("\nGUI 冒烟测试全部通过")


if __name__ == "__main__":
    main()
