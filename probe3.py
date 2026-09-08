# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from engine import CalcEngine, tokenize
e = CalcEngine()
e.f_expr = "X^(2)+1"
print("tokens:", [(t.kind, t.value) for t in tokenize("X^(2)+1", e)])
print("X before:", e.vars["X"])
e.vars["X"] = 3
print("direct eval:", e.evaluate("X^(2)+1"))
e.vars["X"] = 0
print("f(3):", e.evaluate("f(3)"))
print("X after:", e.vars["X"])
print("f_expr:", repr(e.f_expr))
e.g_expr = "2X+1"
print("g(4):", e.evaluate("g(4)"))
print("sin⁻¹(0.5):", e.evaluate("sin⁻¹(0.5)"))
