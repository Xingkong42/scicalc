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

    # 恢复默认设置,避免测试残留
    win._settings.setValue("theme", "light")
    win._settings.setValue("angle", "DEG")
    win._settings.setValue("memory", 0.0)
    win._settings.setValue("hist_visible", False)

    print("\nGUI 冒烟测试全部通过")


if __name__ == "__main__":
    main()
