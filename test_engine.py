# -*- coding: utf-8 -*-
"""引擎自测: python test_engine.py"""
import math
from engine import CalcEngine, CalcError, CATALOG, CONSTANTS, UNITS

e = CalcEngine()
fails = []

def ev(s):
    v, _ = e.evaluate(s)
    return v

def fmt(s, **kw):
    v, _ = e.evaluate(s)
    return e.format_value(v, **kw)

def eq(a, b, eps=1e-9):
    ok = True
    if isinstance(a, str) and isinstance(b, str):
        ok = a == b
    elif isinstance(a, (list, tuple)):
        la, lb = list(a), list(b)
        ok = len(la) == len(lb) and all(abs(x - y) < eps for x, y in zip(la, lb))
    else:
        try:
            ok = abs(a - b) < eps
        except TypeError:
            ok = False
    if not ok:
        fails.append(f"{a!r} != {b!r}")

def chk(name, fn):
    try:
        fn()
        print("OK  ", name)
    except CalcError as err:
        fails.append(f"{name}: 意外 CalcError({err.msg})")
        print("FAIL", name, "->", err.msg)
    except Exception as ex:
        fails.append(f"{name}: {ex!r}")
        print("FAIL", name, "->", repr(ex))

def chk_err(name, expr):
    try:
        e.evaluate(expr)
        fails.append(f"{name}: 应报错但未报错")
        print("FAIL", name)
    except CalcError:
        print("OK  ", name)

# ---- 基本四则与优先级 ----
chk("四则优先级", lambda: eq(ev("1+2×3"), 7))
chk("括号", lambda: eq(ev("(1+2)×3"), 9))
chk("隐式乘法", lambda: eq(ev("2(3+4)"), 14))
chk("隐式乘法2π", lambda: eq(ev("2π"), 2 * math.pi))
chk("一元负号", lambda: eq(ev("−2+3"), 1))
chk("负号与幂", lambda: eq(ev("−2²"), -4))
chk("负底数偶次幂", lambda: eq(ev("(−2)²"), 4))
chk("幂右结合", lambda: eq(ev("2^3^2"), 512))
chk("负指数", lambda: eq(ev("2^−3"), 0.125))
chk_err("除零", "1÷0")
chk("科学记数", lambda: eq(ev("2×10^3"), 2000))
chk("科学记数负指数", lambda: eq(ev("1.5×10^−3"), 0.0015))
chk("科学记数绑定", lambda: eq(ev("2×10^3+1"), 2001))

# ---- 分数 ----
chk("分数相加", lambda: eq(ev("2/3+1/6"), 5 / 6))
chk("分数显示", lambda: eq(fmt("2/3"), "2⁄3"))
chk("分数整化", lambda: eq(fmt("1/2+1/2"), "1"))
chk("带分数", lambda: eq(ev("1∟2/3+1/3"), 2))
chk("带分数显示", lambda: eq(fmt("1∟2/3"), "5⁄3"))
chk("分数连除", lambda: eq(ev("1/2/3"), 1 / 6))

# ---- 六十进制 ----
chk("度分秒", lambda: eq(ev("2°30′15″"), 2.504166666666667))
chk("度分", lambda: eq(ev("1°30′"), 1.5))
chk("度分秒相加", lambda: eq(ev("2°30′+1°30′"), 4))

# ---- 函数 ----
chk("sin30", lambda: eq(ev("sin(30)"), 0.5))
chk("sin+cos", lambda: eq(ev("sin(30)+cos(60)"), 1.0))
chk("反正弦", lambda: eq(ev("sin⁻¹(0.5)"), 30, 1e-6))
chk("sqrt", lambda: eq(ev("√(9)"), 3))
chk("sqrt分数", lambda: eq(ev("√(4/9)"), 2 / 3))
chk("立方根负数", lambda: eq(ev("³√(−8)"), -2))
chk("x次方根", lambda: eq(ev("3ˣ√(8)"), 2))
chk("幂与后置", lambda: eq(ev("√(9)+3²+3³+2⁻¹+5!"), 159.5))
chk("log", lambda: eq(ev("log(100)"), 2))
chk("ln", lambda: eq(ev("ln(e^2)"), 2))
chk("底数对数", lambda: eq(ev("logᵦ(2,8)"), 3))
chk("abs", lambda: eq(ev("Abs(−5)"), 5))
chk("int", lambda: eq(ev("Int(−3.7)"), -3))
chk("intg", lambda: eq(ev("Intg(−3.7)"), -4))
chk("百分", lambda: eq(ev("200×10%"), 20))
chk("阶乘小数", lambda: eq(ev("4.5!"), math.gamma(5.5), 1e-6))
chk("排列", lambda: eq(ev("10P3"), 720))
chk("组合", lambda: eq(ev("5C2"), 10))
chk("隐式函数", lambda: eq(ev("sin(30)cos(60)"), 0.25))
chk("根号隐式", lambda: eq(ev("2√(9)"), 6))
chk("常数πe", lambda: eq(ev("e^(1)"), math.e, 1e-12))
chk("圆周率", lambda: eq(ev("π"), math.pi))

# ---- 角度单位 ----
def rad_test():
    e.settings.angle = "RAD"
    eq(ev("sin(π/2)"), 1.0)
    eq(ev("sin⁻¹(1)"), math.pi / 2, 1e-9)
    e.settings.angle = "DEG"
chk("弧度模式", rad_test)

# ---- 变量与 Ans ----
def var_test():
    e.vars["A"] = 5
    eq(ev("A+1"), 6)
    eq(ev("a+1"), 6)   # 小写兼容
    ev("1+1")
    eq(ev("Ans+1"), 3)
chk("变量与Ans", var_test)

# ---- 用户函数 ----
def fn_test():
    e.f_expr = "X^(2)+1"
    eq(ev("f(3)"), 10)
    e.g_expr = "2X+1"
    eq(ev("g(4)"), 9)
chk("用户函数 f/g", fn_test)

# ---- Pol/Rec ----
def pol_test():
    e.settings.angle = "DEG"
    ev("Pol(1,1)")
    eq(e.vars["Y"], 45, 1e-6)
    v, _ = e.evaluate("Rec(√(2),45)")
    eq(v, 1, 1e-9)
    eq(e.vars["Y"], 1, 1e-9)
chk("Pol/Rec", pol_test)

# ---- 复数 ----
def cplx_test():
    e.settings.complex_mode = True
    z, _ = e.evaluate("(3+4i)(1+i)")
    eq(z, -1 + 7j)
    eq(fmt("(3+4i)(1+i)"), "−1+7i")
    z, _ = e.evaluate("3∠45")
    eq(z, complex(3 * math.cos(math.radians(45)), 3 * math.sin(math.radians(45))), 1e-9)
    eq(fmt("3∠45", polar=True), "3∠45")
    eq(e.format_value(3 + 4j), "3+4i")
    eq(e.format_value(3 + 4j, polar=True), "5∠53.13010235")
    eq(e.format_value(1j), "i")
    e.settings.complex_mode = False
chk("复数运算", cplx_test)

# ---- 实数模式禁止复数 ----
def real_guard():
    e.settings.complex_mode = False
    try:
        e.evaluate("√(−1)")
        fails.append("√(−1) 实数模式应报错")
    except CalcError:
        pass
    try:
        e.evaluate("ln(−1)")
        fails.append("ln(−1) 实数模式应报错")
    except CalcError:
        pass
    try:
        e.evaluate("(−8)^0.5")
        fails.append("(−8)^0.5 应报错")
    except CalcError:
        pass
    eq(ev("(−8)^(1/3)"), -2)
chk("实数域限制", real_guard)

# ---- 格式化 ----
def fmt_test():
    eq(fmt("1÷3"), "0.3333333333")
    eq(fmt("1+1"), "2")
    eq(fmt("sin(30)"), "0.5")
    eq(e.format_value(12345.678, display="SCI", digits=3), "1.23×10⁴")
    eq(e.format_value(1000, display="SCI", digits=3), "1.00×10³")
    eq(e.format_value(1.005, display="FIX", digits=2), "1.01")
    eq(e.format_value(2, display="FIX", digits=2), "2.00")
    eq(e.format_value(1e-10, display="NORM1"), "1×10⁻¹⁰")
    eq(e.format_value(0.001, display="NORM2"), "1×10⁻³")
    eq(e.format_value(0.001, display="NORM1"), "0.001")
    eq(e.format_sexa(2.5041666667), "2°30′15″")
    eq(e.format_sexa(4.0), "4°0′0″")
chk("显示格式", fmt_test)

# ---- Rnd 舍入与显示一致 ----
def rnd_test():
    e.settings.display = "FIX"
    e.settings.digits = 2
    eq(ev("Rnd(1.005)"), 1.01)
    eq(ev("Rnd(1.004)"), 1.0)
    e.settings.digits = 0
    eq(ev("Rnd(0.5)"), 1.0)
    e.settings.display = "SCI"
    e.settings.digits = 3
    eq(ev("Rnd(12345.678)"), 12300.0, 1e-6)
    e.settings.display = "NORM1"
    e.settings.digits = 2
chk("Rnd舍入", rnd_test)

# ---- 方程 ----
def eq_test():
    r = e.solve_quadratic(1, -5, 6)
    eq(sorted(x.real for x in r), [2, 3])
    r = e.solve_quadratic(1, 0, 1)
    eq(sorted(x.imag for x in r), [-1, 1])
    r = e.solve_cubic(1, -6, 11, -6)
    eq(sorted(round(x.real, 6) for x in r), [1, 2, 3])
    r = e.solve_cubic(1, 0, 0, -27)
    real_roots = [x.real for x in r if abs(x.imag) < 1e-9]
    eq(sorted(round(x, 6) for x in real_roots), [3])
    r = e.gauss_solve([[2, 1, 5], [1, -1, 1]])
    eq(r, [2, 1])
chk("方程求解", eq_test)

# ---- 不等式 ----
def ineq_test():
    eq(e.solve_inequality([1, -5, 6], ">"), "x<2 或 x>3")
    eq(e.solve_inequality([1, -5, 6], "<="), "2≤x≤3")
    eq(e.solve_inequality([1, 0, 1], ">"), "全体实数")
    eq(e.solve_inequality([-1, 0, -1], ">"), "无解")
    eq(e.solve_inequality([1, 0, -1, 0], ">="), "−1≤x≤0 或 x≥1")
chk("不等式求解", ineq_test)

# ---- 统计 ----
def stat_test():
    r = e.stats_1var([(1, 1), (2, 2), (3, 1)])
    eq(r["n"], 4)
    eq(r["mean"], 2)
    eq(r["min"], 1)
    eq(r["max"], 3)
    r2 = e.stats_lin([(1, 2, 1), (2, 4, 1), (3, 6, 1)])
    eq(r2["a"], 0)
    eq(r2["b"], 2)
    eq(r2["r"], 1)
chk("统计计算", stat_test)

# ---- 单位换算 ----
def unit_test():
    eq(e.convert_unit("长度", 1, "m", "cm"), 100)
    eq(e.convert_unit("温度", 100, "℃", "℉"), 212)
    eq(e.convert_unit("速度", 36, "km/h", "m/s"), 10)
chk("单位换算", unit_test)

# ---- 数据完整性 ----
def data_test():
    assert len(CATALOG) >= 5 and len(CONSTANTS) >= 10 and len(UNITS) >= 10
chk("目录数据", data_test)

print()
if fails:
    print(f"共 {len(fails)} 处失败:")
    for f in fails:
        print(" -", f)
    raise SystemExit(1)
print("全部测试通过 OK")
