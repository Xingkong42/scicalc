# -*- coding: utf-8 -*-
"""CASIO fx-991CN CW 仿真计算器 — 启动入口

运行:
    pip install PySide6
    python main.py
"""
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from ui_screens import CalculatorWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("CASIO fx-991CN CW 模拟器")
    f = QFont("Microsoft YaHei UI", 9)
    f.setHintingPreference(QFont.PreferFullHinting)
    app.setFont(f)
    w = CalculatorWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
