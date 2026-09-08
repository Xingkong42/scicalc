# -*- coding: utf-8 -*-
"""CASIO fx-991CN CW 仿真计算器 —— 数学引擎(纯 Python,不依赖 Qt,可独立测试)

功能:
- 表达式解析与求值(递归下降): + - × ÷ ^ ˣ√ P C ∠ 隐式乘法 一元负号 后缀算符(! ² ³ ⁻¹ %)
- 科学记数 ×10^、六十进制 ° ′ ″、分数 ⁄ 与带分数 ∟
- 三角函数/反三角(角度单位 DEG/RAD/GRA)、双曲、对数、指数、复数、随机数
- 变量 A-F X Y Z M(兼容小写)、Ans、用户函数 f(x)/g(x)、科学常数
- 显示格式 NORM1/NORM2/SCI/FIX、分数(假/带)、六十进制、复数极坐标
- 方程求解(联立 2-4 元、二次、三次)、不等式求解、统计计算、单位换算
"""
from __future__ import annotations

import math
import cmath
import random
from fractions import Fraction
from decimal import Decimal, ROUND_HALF_UP


class CalcError(Exception):
    """计算错误(对应 CASIO 的 Math ERROR / Syntax ERROR 等)"""
    def __init__(self, msg="Math ERROR"):
        super().__init__(msg)
        self.msg = msg


# --------------------------------------------------------------------------
# 科学常数(符号 -> 值)
# --------------------------------------------------------------------------
CONSTANTS = {
    "c₀": 299792458.0,          # 真空光速 m/s
    "e₀": 1.602176634e-19,      # 元电荷 C
    "g": 9.80665,               # 重力加速度 m/s²
    "h": 6.62607015e-34,        # 普朗克常数 J·s
    "ℏ": 1.054571817e-34,       # 约化普朗克常数
    "Nₐ": 6.02214076e23,        # 阿伏伽德罗常数
    "k": 1.380649e-23,          # 玻尔兹曼常数 J/K
    "μ₀": 1.25663706212e-6,     # 真空磁导率
    "ε₀": 8.8541878128e-12,     # 真空介电常数
    "mₑ": 9.1093837015e-31,     # 电子质量 kg
    "mₚ": 1.67262192369e-27,    # 质子质量 kg
    "mₙ": 1.67492749804e-27,    # 中子质量 kg
    "R": 8.314462618,           # 摩尔气体常数 J/(mol·K)
    "atm": 101325.0,            # 标准大气压 Pa
    "R∞": 10973731.568,         # 里德伯常数 1/m
    "π": math.pi,               # 圆周率
    "e": math.e,                # 自然常数
}
_CONST_SORTED = sorted(CONSTANTS.keys(), key=len, reverse=True)

VARIABLES = ["A", "B", "C", "D", "E", "F", "X", "Y", "Z", "M"]


# --------------------------------------------------------------------------
# 函数表(名称 -> 参数个数范围)
# --------------------------------------------------------------------------
FUNCTIONS = {
    "sin": (1, 1), "cos": (1, 1), "tan": (1, 1),
    "sin⁻¹": (1, 1), "cos⁻¹": (1, 1), "tan⁻¹": (1, 1),
    "sinh": (1, 1), "cosh": (1, 1), "tanh": (1, 1),
    "sinh⁻¹": (1, 1), "cosh⁻¹": (1, 1), "tanh⁻¹": (1, 1),
    "log": (1, 1), "ln": (1, 1), "logᵦ": (2, 2),
    "√": (1, 1), "³√": (1, 1),
    "e^": (1, 1),
    "Abs": (1, 1), "Int": (1, 1), "Intg": (1, 1), "Rnd": (1, 1),
    "Ran#": (0, 0), "RanInt": (2, 2),
    "Pol": (2, 2), "Rec": (2, 2),
    "GCD": (2, 2), "LCM": (2, 2),
    "Conjg": (1, 1), "Arg": (1, 1), "ReP": (1, 1), "ImP": (1, 1),
    "f": (1, 1), "g": (1, 1),
}
_FUNC_SORTED = sorted(FUNCTIONS.keys(), key=len, reverse=True)

# 供 UI 显示/智能删除使用的多字符记号
DISPLAY_TOKENS = sorted(set(list(FUNCTIONS) + list(CONSTANTS) + ["Ans", "×10^", "⁻¹", "ˣ√"]),
                        key=len, reverse=True)


# --------------------------------------------------------------------------
# 目录(CATALOG)与单位换算数据
# --------------------------------------------------------------------------
CATALOG = [
    ("基本", [
        ("平方 x²", "²", "对当前值求平方"),
        ("立方 x³", "³", "对当前值求立方"),
        ("倒数 x⁻¹", "⁻¹", "求倒数"),
        ("乘方 xʸ", "^(◦)", "x 的 y 次方,指数写在括号内"),
        ("开方 √", "√(◦)", "平方根"),
        ("开立方 ³√", "³√(◦)", "立方根"),
        ("开 x 次方 ˣ√", "ˣ√(◦)", "x 次方根,根指数写在前面"),
        ("阶乘 x!", "!", "阶乘"),
        ("常用对数 log", "log(◦)", "以 10 为底的对数"),
        ("自然对数 ln", "ln(◦)", "以 e 为底的对数"),
        ("底数对数 logᵦ", "logᵦ(◦,◦)", "logᵦ(底, 真数)"),
        ("e 的 x 次方", "e^(◦)", "指数函数"),
        ("圆周率 π", "π", "圆周率 3.141592654"),
        ("自然常数 e", "e", "自然常数 2.718281828"),
        ("百分数 %", "%", "除以 100"),
        ("绝对值 Abs", "Abs(◦)", "绝对值"),
        ("取整 Int", "Int(◦)", "去掉小数部分(向 0 取整)"),
        ("最大整数 Intg", "Intg(◦)", "不大于 x 的最大整数"),
        ("舍入 Rnd", "Rnd(◦)", "按当前显示位数舍入"),
        ("随机数 Ran#", "Ran#", "0~1 之间的随机数"),
        ("随机整数 RanInt", "RanInt(◦,◦)", "随机整数(起始, 结束)"),
        ("最大公约数 GCD", "GCD(◦,◦)", "两个整数的最大公约数"),
        ("最小公倍数 LCM", "LCM(◦,◦)", "两个整数的最小公倍数"),
        ("排列 nPr", "P", "排列数 nPr"),
        ("组合 nCr", "C", "组合数 nCr"),
        ("分数 a⁄b", "⁄", "分数(输入分子后插入)"),
        ("带分数", "∟", "带分数(整数部分之后插入)"),
        ("度 °", "°", "六十进制度"),
        ("分 ′", "′", "六十进制分"),
        ("秒 ″", "″", "六十进制秒"),
        ("直角转极坐标 Pol", "Pol(◦,◦)", "Pol(x,y) 得 r,θ 存入 Y"),
        ("极坐标转直角 Rec", "Rec(◦,◦)", "Rec(r,θ) 得 x,y 存入 Y"),
        ("答案 Ans", "Ans", "上次计算结果"),
    ]),
    ("三角/双曲", [
        ("反正弦 sin⁻¹", "sin⁻¹(◦)", "反正弦函数"),
        ("反余弦 cos⁻¹", "cos⁻¹(◦)", "反余弦函数"),
        ("反正切 tan⁻¹", "tan⁻¹(◦)", "反正切函数"),
        ("双曲正弦 sinh", "sinh(◦)", "双曲正弦"),
        ("双曲余弦 cosh", "cosh(◦)", "双曲余弦"),
        ("双曲正切 tanh", "tanh(◦)", "双曲正切"),
        ("反双曲正弦 sinh⁻¹", "sinh⁻¹(◦)", "反双曲正弦"),
        ("反双曲余弦 cosh⁻¹", "cosh⁻¹(◦)", "反双曲余弦"),
        ("反双曲正切 tanh⁻¹", "tanh⁻¹(◦)", "反双曲正切"),
    ]),
    ("复数", [
        ("虚数单位 i", "i", "复数单位 i(复数模式下)"),
        ("辐角符号 ∠", "∠", "极坐标输入 a∠θ"),
        ("共轭 Conjg", "Conjg(◦)", "共轭复数"),
        ("辐角 Arg", "Arg(◦)", "辐角(按角度单位)"),
        ("实部 ReP", "ReP(◦)", "实部"),
        ("虚部 ImP", "ImP(◦)", "虚部"),
    ]),
    ("用户函数", [
        ("f(x)", "f(◦)", "已定义的 f(x)"),
        ("g(x)", "g(◦)", "已定义的 g(x)"),
    ]),
    ("科学常数", [
        (f"{sym} = {val:g}", sym, "科学常数(插入符号)") for sym, val in CONSTANTS.items()
    ]),
]

UNITS = {
    "长度": {"m": 1, "cm": 0.01, "mm": 0.001, "km": 1000,
             "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mile": 1609.344, "海里": 1852},
    "质量": {"kg": 1, "g": 0.001, "mg": 1e-6, "t": 1000,
             "lb": 0.45359237, "oz": 0.028349523125},
    "面积": {"m²": 1, "cm²": 1e-4, "mm²": 1e-6, "km²": 1e6,
             "ha": 1e4, "acre": 4046.8564224, "ft²": 0.09290304},
    "体积": {"m³": 1, "cm³": 1e-6, "L": 0.001, "mL": 1e-6,
             "gal(US)": 0.003785411784, "gal(UK)": 0.00454609, "ft³": 0.028316846592},
    "温度": {"℃": None, "K": None, "℉": None},
    "速度": {"m/s": 1, "km/h": 0.2777777778, "mph": 0.44704, "knot": 0.5144444444},
    "能量": {"J": 1, "kJ": 1000, "cal": 4.184, "kcal": 4184, "Wh": 3600, "eV": 1.602176634e-19},
    "功率": {"W": 1, "kW": 1000, "hp": 745.6998716, "PS": 735.49875},
    "压强": {"Pa": 1, "kPa": 1000, "atm": 101325, "mmHg": 133.3223874,
             "bar": 100000, "psi": 6894.757293},
    "时间": {"s": 1, "min": 60, "h": 3600, "day": 86400, "week": 604800, "year": 31557600},
    "角度": {"度": 1, "弧度": 57.29577951, "百分度": 0.9},
}


# --------------------------------------------------------------------------
# 词法分析
# --------------------------------------------------------------------------
TOK_NUM, TOK_VAR, TOK_CONST, TOK_FUNC, TOK_OP, TOK_LP, TOK_RP, TOK_POST, TOK_COMMA, TOK_END = range(10)
_OPS = {"+", "-", "×", "÷", "^", "∠", "P", "C", "/"}
_POST = {"!", "²", "³", "%"}


def _is_ascii_digit(c):
    return "0" <= c <= "9"


class _Tok:
    __slots__ = ("kind", "value")
    def __init__(self, k, v):
        self.kind = k
        self.value = v
    def __repr__(self):
        return f"Tok({self.kind},{self.value!r})"


def _to_frac(x):
    """尽量把数值转成精确分数"""
    if isinstance(x, Fraction):
        return x
    if isinstance(x, float):
        if x.is_integer():
            return Fraction(int(x))
        return Fraction(str(x))
    return Fraction(x)


def _safe_float(s):
    """把十进制字符串转 float,非法输入抛 Syntax ERROR"""
    try:
        return float(s)
    except ValueError:
        raise CalcError("Syntax ERROR")


def tokenize(s, engine):
    toks = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in " \t\u3000":
            i += 1
            continue
        if _is_ascii_digit(c) or c == ".":
            j = i
            while j < n and (_is_ascii_digit(s[j]) or s[j] == "."):
                j += 1
            numstr = s[i:j]
            try:
                val = int(numstr) if "." not in numstr else float(numstr)
            except ValueError:
                raise CalcError("Syntax ERROR")
            while True:
                if s.startswith("×10^", j):
                    k = j + 4
                    sign = 1
                    if k < n and s[k] in "−-":
                        sign = -1
                        k += 1
                    m = k
                    while m < n and _is_ascii_digit(s[m]):
                        m += 1
                    if m > k:
                        val = float(val) * 10 ** (sign * int(s[k:m]))
                        j = m
                        continue
                    break
                if j < n and s[j] == "°":
                    k = j + 1
                    m = k
                    while m < n and (_is_ascii_digit(s[m]) or s[m] == "."):
                        m += 1
                    mins = 0.0
                    secs = 0.0
                    if m < n and s[m] in "′'":
                        if m > k:
                            mins = _safe_float(s[k:m])
                        m += 1
                        p = m
                        while p < n and (_is_ascii_digit(s[p]) or s[p] == "."):
                            p += 1
                        if p > m:
                            secs = _safe_float(s[m:p])
                            m = p
                        if m < n and s[m] in "″\"":
                            m += 1
                    val = float(val) + mins / 60.0 + secs / 3600.0
                    j = m
                    continue
                if j < n and s[j] in "⁄/":
                    k = j + 1
                    p = k
                    while p < n and (_is_ascii_digit(s[p]) or s[p] == "."):
                        p += 1
                    if p > k:
                        den = _to_frac(_safe_float(s[k:p]))
                        if den == 0:
                            raise CalcError("Math ERROR")
                        val = _to_frac(val) / den
                        j = p
                        continue
                    break
                if j < n and s[j] == "∟":
                    k = j + 1
                    p = k
                    while p < n and (_is_ascii_digit(s[p]) or s[p] == "."):
                        p += 1
                    if p > k:
                        num2 = _to_frac(_safe_float(s[k:p]))
                        if p < n and s[p] in "⁄/":
                            q = p + 1
                            r = q
                            while r < n and (_is_ascii_digit(s[r]) or s[r] == "."):
                                r += 1
                            if r > q:
                                den = _to_frac(_safe_float(s[q:r]))
                                if den == 0:
                                    raise CalcError("Math ERROR")
                                whole = _to_frac(val)
                                if whole.denominator != 1:
                                    raise CalcError("Syntax ERROR")
                                val = whole + num2 / den
                                j = r
                                continue
                    break
                break
            toks.append(_Tok(TOK_NUM, val))
            i = j
            continue
        mname = None
        for fn in _FUNC_SORTED:
            if s.startswith(fn, i):
                if fn in ("f", "g") and not (i + 1 < n and s[i + 1] == "("):
                    continue
                mname = fn
                break
        if mname:
            toks.append(_Tok(TOK_FUNC, mname))
            i += len(mname)
            continue
        cname = None
        for cn in _CONST_SORTED:
            if s.startswith(cn, i):
                cname = cn
                break
        if cname:
            toks.append(_Tok(TOK_CONST, CONSTANTS[cname]))
            i += len(cname)
            continue
        if s.startswith("Ans", i):
            toks.append(_Tok(TOK_VAR, "Ans"))
            i += 3
            continue
        if s.startswith("ˣ√", i):
            toks.append(_Tok(TOK_OP, "ˣ√"))
            i += 2
            continue
        if s.startswith("⁻¹", i):
            toks.append(_Tok(TOK_POST, "⁻¹"))
            i += 2
            continue
        if c == "i":
            if not engine.settings.complex_mode:
                raise CalcError("Syntax ERROR")
            toks.append(_Tok(TOK_VAR, "i"))
            i += 1
            continue
        if c in ("P", "C") and toks and toks[-1].kind in (TOK_NUM, TOK_RP, TOK_POST, TOK_VAR, TOK_CONST):
            toks.append(_Tok(TOK_OP, c))
            i += 1
            continue
        if c in "ABCDEFXYZM" or c in "abcdefxyz":
            toks.append(_Tok(TOK_VAR, c.upper()))
            i += 1
            continue
        if c == "(":
            toks.append(_Tok(TOK_LP, c))
            i += 1
            continue
        if c == ")":
            toks.append(_Tok(TOK_RP, c))
            i += 1
            continue
        if c == ",":
            toks.append(_Tok(TOK_COMMA, c))
            i += 1
            continue
        if c == "−":
            c = "-"
        if c in _OPS:
            toks.append(_Tok(TOK_OP, c))
            i += 1
            continue
        if c in _POST:
            toks.append(_Tok(TOK_POST, c))
            i += 1
            continue
        raise CalcError("Syntax ERROR")
    toks.append(_Tok(TOK_END, None))
    return toks


# --------------------------------------------------------------------------
# 递归下降语法分析 + 求值
# --------------------------------------------------------------------------
class _Parser:
    def __init__(self, engine, tokens):
        self.e = engine
        self.t = tokens
        self.p = 0
        self.used_frac = False

    def peek(self, k=0):
        return self.t[min(self.p + k, len(self.t) - 1)]

    def next(self):
        t = self.t[self.p]
        if self.p < len(self.t) - 1:
            self.p += 1
        return t

    def expect(self, kind, value=None):
        t = self.peek()
        if t.kind == kind and (value is None or t.value == value):
            return self.next()
        if kind == TOK_RP and t.kind == TOK_END:
            return None  # 自动补全右括号
        raise CalcError("Syntax ERROR")

    def starts_primary(self, t):
        return t.kind in (TOK_NUM, TOK_VAR, TOK_CONST, TOK_FUNC, TOK_LP)

    def parse(self):
        v = self.expr()
        t = self.peek()
        if t.kind != TOK_END:
            raise CalcError("Syntax ERROR")
        return v

    def expr(self):
        v = self.term()
        while self.peek().kind == TOK_OP and self.peek().value in ("+", "-"):
            op = self.next().value
            r = self.term()
            v = self.e.binop(v, op, r)
        return v

    def term(self):
        v = self.factor()
        while True:
            t = self.peek()
            if t.kind == TOK_OP and t.value in ("×", "÷", "/"):
                op = self.next().value
                r = self.factor()
                v = self.e.binop(v, op, r)
            elif self.starts_primary(t):
                r = self.factor()
                v = self.e.binop(v, "×", r)
            else:
                break
        return v

    def factor(self):
        t = self.peek()
        if t.kind == TOK_OP and t.value == "-":
            self.next()
            v = self.factor()
            return self.e.neg(v)
        return self.power()

    def power(self):
        base = self.postfix()
        t = self.peek()
        if t.kind == TOK_OP and t.value == "^":
            self.next()
            exp = self.factor()
            return self.e.pow(base, exp)
        if t.kind == TOK_OP and t.value == "ˣ√":
            self.next()
            r = self.factor()
            return self.e.pow(r, self.e.recip(base))
        if t.kind == TOK_OP and t.value in ("P", "C"):
            op = self.next().value
            r = self.factor()
            return self.e.npr_ncr(base, r, op)
        if t.kind == TOK_OP and t.value == "∠":
            self.next()
            r = self.factor()
            return self.e.angle(base, r)
        return base

    def postfix(self):
        v = self.primary()
        while self.peek().kind == TOK_POST:
            op = self.next().value
            v = self.e.postfix_op(v, op)
        return v

    def primary(self):
        t = self.next()
        if t.kind == TOK_NUM:
            if isinstance(t.value, Fraction):
                self.used_frac = True
            return t.value
        if t.kind == TOK_CONST:
            return t.value
        if t.kind == TOK_VAR:
            return self.e.get_var(t.value)
        if t.kind == TOK_LP:
            v = self.expr()
            self.expect(TOK_RP)
            return v
        if t.kind == TOK_FUNC:
            return self.call(t.value)
        raise CalcError("Syntax ERROR")

    def call(self, name):
        args = []
        t = self.peek()
        if t.kind == TOK_LP:
            self.next()
            if self.peek().kind != TOK_RP:
                args.append(self.expr())
                while self.peek().kind == TOK_COMMA:
                    self.next()
                    args.append(self.expr())
            self.expect(TOK_RP)
        elif self.starts_primary(t) or (t.kind == TOK_OP and t.value == "-"):
            args.append(self.factor())
        return self.e.apply(name, args)


# --------------------------------------------------------------------------
# 设置与引擎
# --------------------------------------------------------------------------
class _Settings:
    def __init__(self):
        self.angle = "DEG"            # DEG / RAD / GRA
        self.display = "NORM1"        # NORM1 / NORM2 / SCI / FIX
        self.digits = 2               # SCI/FIX 的位数(0~9)
        self.fraction = True          # 分数结果自动显示
        self.fraction_type = "improper"  # improper / mixed
        self.complex_mode = False     # 复数开/关


class CalcEngine:
    def __init__(self):
        self.settings = _Settings()
        self.vars = {k: 0.0 for k in VARIABLES}
        self.ans = 0.0
        self.rng = random.Random()
        self.f_expr = None
        self.g_expr = None
        self.last_store = None   # Pol/Rec 写入变量的提示 (名称, 值)
        self._depth = 0

    def reset_memory(self):
        self.vars = {k: 0.0 for k in VARIABLES}
        self.ans = 0.0
        self.f_expr = None
        self.g_expr = None
        self.last_store = None

    def reset_all(self):
        self.settings = _Settings()
        self.reset_memory()

    def set_setting(self, name, value):
        setattr(self.settings, name, value)

    # ---------------- 求值入口 ----------------
    def evaluate(self, expr, complex_override=None):
        old = None
        if complex_override is not None:
            old = self.settings.complex_mode
            self.settings.complex_mode = complex_override
        self.last_store = None
        try:
            if not expr or not expr.strip():
                raise CalcError("Syntax ERROR")
            toks = tokenize(expr, self)
            p = _Parser(self, toks)
            v = p.parse()
            v = self._real(v)
            if isinstance(v, float) and not math.isfinite(v):
                raise CalcError("Math ERROR")
            self.ans = v
            return v, {"frac": p.used_frac}
        finally:
            if old is not None:
                self.settings.complex_mode = old

    # ---------------- 基础运算 ----------------
    def _real(self, v):
        if not isinstance(v, complex):
            return v
        if self.settings.complex_mode:
            return v
        if abs(v.imag) < 1e-12 * max(1.0, abs(v.real)):
            return v.real
        raise CalcError("Math ERROR")

    def _real_float(self, v):
        """仅接受实数并转 float,复数参数视为 Math ERROR"""
        if isinstance(v, complex):
            raise CalcError("Math ERROR")
        return float(v)

    def get_var(self, name):
        if name == "Ans":
            return self.ans if self.ans is not None else 0.0
        if name == "i":
            return 1j
        return self.vars.get(name, 0.0)

    def neg(self, a):
        return -a

    def recip(self, a):
        if a == 0:
            raise CalcError("Math ERROR")
        return 1 / a

    def binop(self, a, op, b):
        if isinstance(a, complex) or isinstance(b, complex):
            if op == "+":
                return self._real(a + b)
            if op == "-":
                return self._real(a - b)
            if op == "×":
                return self._real(a * b)
            if op == "÷":
                if b == 0:
                    raise CalcError("Math ERROR")
                return self._real(a / b)
            raise CalcError("Math ERROR")
        if op == "/":
            try:
                fa, fb = _to_frac(a), _to_frac(b)
                if fb == 0:
                    raise ZeroDivisionError
                return fa / fb
            except (ZeroDivisionError, ValueError):
                raise CalcError("Math ERROR")
        use_frac = isinstance(a, Fraction) or isinstance(b, Fraction)
        if use_frac:
            try:
                fa, fb = _to_frac(a), _to_frac(b)
                if op == "+":
                    return fa + fb
                if op == "-":
                    return fa - fb
                if op == "×":
                    return fa * fb
                if op == "÷":
                    if fb == 0:
                        raise ZeroDivisionError
                    return fa / fb
            except (ZeroDivisionError, ValueError):
                raise CalcError("Math ERROR")
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "×":
            return a * b
        if op == "÷":
            if b == 0:
                raise CalcError("Math ERROR")
            return a / b
        raise CalcError("Syntax ERROR")

    def pow(self, a, b):
        if isinstance(b, Fraction) and b.denominator == 1:
            b = b.numerator
        if self.settings.complex_mode or isinstance(a, complex) or isinstance(b, complex):
            try:
                return self._real(complex(a) ** complex(b))
            except (ValueError, ZeroDivisionError, OverflowError):
                raise CalcError("Math ERROR")
        if isinstance(a, Fraction) and isinstance(b, int):
            try:
                return a ** b
            except ZeroDivisionError:
                raise CalcError("Math ERROR")
        af, bf = float(a), float(b)
        if af == 0 and bf == 0:
            raise CalcError("Math ERROR")   # CASIO: 0^0 报错
        if af < 0 and not isinstance(b, int):
            pq = Fraction(bf).limit_denominator(1000)
            if pq.denominator > 1 and abs(bf - float(pq)) <= 1e-10 and pq.denominator % 2 == 1:
                try:
                    r = (-af) ** bf
                except (ValueError, ZeroDivisionError, OverflowError):
                    raise CalcError("Math ERROR")
                return -r if pq.numerator % 2 else r
            raise CalcError("Math ERROR")
        try:
            r = af ** bf
        except (ValueError, ZeroDivisionError, OverflowError):
            raise CalcError("Math ERROR")
        if isinstance(r, complex):
            raise CalcError("Math ERROR")
        return r

    def npr_ncr(self, n, r, op):
        if isinstance(n, complex) or isinstance(r, complex):
            raise CalcError("Math ERROR")
        nf, rf = float(n), float(r)
        if nf < 0 or rf < 0 or rf > nf + 1e-12:
            raise CalcError("Math ERROR")
        if nf == int(nf) and rf == int(rf) and nf <= 2000:
            ni, ri = int(nf), int(rf)
            return math.perm(ni, ri) if op == "P" else math.comb(ni, ri)
        try:
            v = math.gamma(nf + 1) / (math.gamma(rf + 1) * math.gamma(nf - rf + 1))
        except (ValueError, OverflowError, ZeroDivisionError):
            raise CalcError("Math ERROR")
        return v

    def angle(self, r, th):
        if not self.settings.complex_mode:
            raise CalcError("Math ERROR")
        if isinstance(r, complex) or isinstance(th, complex):
            raise CalcError("Math ERROR")
        rr = float(r)
        t = self._angle_to_rad(float(th))
        return self._real(complex(rr * math.cos(t), rr * math.sin(t)))

    def postfix_op(self, v, op):
        if op == "²":
            return self.pow(v, 2)
        if op == "³":
            return self.pow(v, 3)
        if op == "⁻¹":
            return self.recip(v)
        if op == "%":
            return self.binop(v, "/", 100)
        if op == "!":
            return self.factorial(v)
        raise CalcError("Syntax ERROR")

    def factorial(self, v):
        if isinstance(v, complex):
            raise CalcError("Math ERROR")
        x = float(v)
        try:
            return math.gamma(x + 1)
        except (ValueError, OverflowError):
            raise CalcError("Math ERROR")

    # ---------------- 角度换算 ----------------
    def _angle_factors(self):
        a = self.settings.angle
        if a == "RAD":
            return 1.0, 1.0
        if a == "GRA":
            return math.pi / 200.0, 200.0 / math.pi
        return math.pi / 180.0, 180.0 / math.pi

    def _angle_to_rad(self, x):
        return x * self._angle_factors()[0]

    def _angle_from_rad(self, x):
        return x * self._angle_factors()[1]

    # ---------------- 函数 ----------------
    def apply(self, name, args):
        lo, hi = FUNCTIONS[name]
        if not (lo <= len(args) <= hi):
            raise CalcError("Syntax ERROR")
        cmplx = self.settings.complex_mode or any(isinstance(a, complex) for a in args)
        x = args[0] if args else None

        if name in ("sin", "cos", "tan", "sin⁻¹", "cos⁻¹", "tan⁻¹"):
            f_in, f_out = self._angle_factors()
            inv = name.endswith("⁻¹")
            base = {"sin": "sin", "cos": "cos", "tan": "tan",
                    "sin⁻¹": "asin", "cos⁻¹": "acos", "tan⁻¹": "atan"}[name]
            if cmplx:
                f = getattr(cmath, base)
                try:
                    if inv:
                        return self._real(f(complex(x)) * f_out)
                    return self._real(f(complex(x) * f_in))
                except (ValueError, OverflowError):
                    raise CalcError("Math ERROR")
            f = getattr(math, base)
            try:
                if inv:
                    v = f(float(x))
                    return v * f_out
                v = f(float(x) * f_in)
            except (ValueError, OverflowError):
                raise CalcError("Math ERROR")
            return v

        if name in ("sinh", "cosh", "tanh", "sinh⁻¹", "cosh⁻¹", "tanh⁻¹"):
            base = {"sinh": "sinh", "cosh": "cosh", "tanh": "tanh",
                    "sinh⁻¹": "asinh", "cosh⁻¹": "acosh", "tanh⁻¹": "atanh"}[name]
            if cmplx:
                try:
                    return self._real(getattr(cmath, base)(complex(x)))
                except (ValueError, OverflowError):
                    raise CalcError("Math ERROR")
            try:
                return getattr(math, base)(float(x))
            except (ValueError, OverflowError):
                raise CalcError("Math ERROR")

        if name == "log":
            if cmplx:
                try:
                    return self._real(cmath.log10(complex(x)))
                except (ValueError, OverflowError):
                    raise CalcError("Math ERROR")
            if float(x) <= 0:
                raise CalcError("Math ERROR")
            return math.log10(float(x))

        if name == "ln":
            if cmplx:
                try:
                    return self._real(cmath.log(complex(x)))
                except (ValueError, OverflowError):
                    raise CalcError("Math ERROR")
            if float(x) <= 0:
                raise CalcError("Math ERROR")
            return math.log(float(x))

        if name == "logᵦ":
            b, xx = args[0], args[1]
            if cmplx:
                try:
                    return self._real(cmath.log(complex(xx)) / cmath.log(complex(b)))
                except (ValueError, ZeroDivisionError, OverflowError):
                    raise CalcError("Math ERROR")
            bf, xf = float(b), float(xx)
            if bf <= 0 or bf == 1 or xf <= 0:
                raise CalcError("Math ERROR")
            return math.log(xf, bf)

        if name == "√":
            if isinstance(x, Fraction) and not cmplx:
                n = math.isqrt(x.numerator)
                d = math.isqrt(x.denominator)
                if n * n == x.numerator and d * d == x.denominator:
                    return Fraction(n, d)
            if cmplx:
                return self._real(cmath.sqrt(complex(x)))
            if float(x) < 0:
                raise CalcError("Math ERROR")
            return math.sqrt(float(x))

        if name == "³√":
            if cmplx:
                return self._real(complex(x) ** (1.0 / 3.0))
            v = float(x)
            return math.copysign(abs(v) ** (1.0 / 3.0), v)

        if name == "e^":
            if cmplx:
                try:
                    return self._real(cmath.exp(complex(x)))
                except OverflowError:
                    raise CalcError("Math ERROR")
            try:
                return math.exp(float(x))
            except OverflowError:
                raise CalcError("Math ERROR")

        if name == "Abs":
            return abs(x)

        if name in ("Int", "Intg", "Rnd"):
            if isinstance(x, complex):
                raise CalcError("Math ERROR")
            v = float(x)
            if name == "Int":
                return float(math.trunc(v))
            if name == "Intg":
                return float(math.floor(v))
            return self._round_to_display(v)

        if name == "Ran#":
            return self.rng.random()

        if name == "RanInt":
            a = int(round(self._real_float(args[0])))
            b = int(round(self._real_float(args[1])))
            if a > b:
                a, b = b, a
            return float(self.rng.randint(a, b))

        if name == "GCD":
            a = int(round(self._real_float(args[0])))
            b = int(round(self._real_float(args[1])))
            return math.gcd(abs(a), abs(b))

        if name == "LCM":
            a = int(round(self._real_float(args[0])))
            b = int(round(self._real_float(args[1])))
            return math.lcm(abs(a), abs(b))

        if name in ("Conjg", "Arg", "ReP", "ImP"):
            z = complex(x)
            if name == "Conjg":
                return self._real(z.conjugate())
            if name == "Arg":
                return self._angle_from_rad(cmath.phase(z))
            if name == "ReP":
                return z.real
            return z.imag

        if name == "Pol":
            xr, yr = self._real_float(args[0]), self._real_float(args[1])
            r = math.hypot(xr, yr)
            th = self._angle_from_rad(math.atan2(yr, xr))
            self.vars["Y"] = th
            self.last_store = ("Y", th)
            return r

        if name == "Rec":
            r = self._real_float(args[0])
            th = self._angle_to_rad(self._real_float(args[1]))
            xv = r * math.cos(th)
            yv = r * math.sin(th)
            self.vars["Y"] = yv
            self.last_store = ("Y", yv)
            return xv

        if name in ("f", "g"):
            expr = self.f_expr if name == "f" else self.g_expr
            if not expr:
                raise CalcError("未定义 f(x)" if name == "f" else "未定义 g(x)")
            self._depth += 1
            if self._depth > 20:
                self._depth -= 1
                raise CalcError("Math ERROR")
            old = self.vars.get("X")
            self.vars["X"] = x
            try:
                v, _meta = self.evaluate(expr)
            finally:
                self.vars["X"] = old
                self._depth -= 1
            return v

        raise CalcError("Syntax ERROR")

    # ---------------- 舍入 ----------------
    def _round_to_display(self, v):
        if self.settings.display == "FIX":
            try:
                return float(Decimal(str(v)).quantize(
                    _dec_scale(self.settings.digits), rounding=ROUND_HALF_UP))
            except Exception:
                return round(v, self.settings.digits)
        if self.settings.display == "SCI":
            return self._round_sig_float(v, self.settings.digits)
        return self._round_sig_float(v, 10)

    @staticmethod
    def _round_sig_float(v, d):
        if v == 0:
            return 0.0
        try:
            return float(_round_sig(Decimal(str(v)), d))
        except Exception:
            e = math.floor(math.log10(abs(v)))
            return round(v, d - 1 - e)

    # ---------------- 显示格式化 ----------------
    _SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")

    @staticmethod
    def _sup(e):
        return str(e).translate(CalcEngine._SUP)

    def _frac_ok(self, f):
        if not self.settings.fraction:
            return False
        a = abs(f)
        if a.denominator == 1:
            return True
        return len(str(a.numerator)) + len(str(a.denominator)) <= 14

    def _fmt_frac(self, f):
        if f.denominator == 1:
            return str(f.numerator)
        neg = f < 0
        f = abs(f)
        w = f.numerator // f.denominator
        rem = f - w
        if w == 0:
            s = f"{rem.numerator}⁄{rem.denominator}"
        elif self.settings.fraction_type == "mixed" and rem:
            s = f"{w}∟{rem.numerator}⁄{rem.denominator}"
        else:
            s = f"{f.numerator}⁄{f.denominator}"
        return ("−" + s) if neg else s

    def _fmt_fix(self, v, d):
        try:
            dec = Decimal(str(v)).quantize(_dec_scale(d), rounding=ROUND_HALF_UP)
            s = str(dec)
            if "." not in s and d > 0:
                s += "." + "0" * d
        except Exception:
            s = f"{v:.{d}f}"
        if s.startswith("-0") and set(s[1:]).issubset(set("0.")):
            s = s[1:]
        return s

    def _fmt_sci(self, v, d, strip=False):
        if v == 0:
            return "0×10⁰"
        try:
            e = math.floor(math.log10(abs(v)))
            m = Decimal(str(v)) / (Decimal(10) ** e)
            m = m.quantize(_dec_scale(d - 1), rounding=ROUND_HALF_UP)
            if m >= 10:
                m = m / 10
                e += 1
                m = m.quantize(_dec_scale(d - 1), rounding=ROUND_HALF_UP)
            s = str(m)
            if strip:
                s = s.rstrip("0").rstrip(".") if "." in s else s
            else:
                if "." not in s and d > 1:
                    s += "." + "0" * (d - 1)
            if s.startswith("-0") and set(s[1:]).issubset(set("0.")):
                s = s[1:]
            return s + "×10" + self._sup(e)
        except Exception:
            return f"{v:.{d}e}"

    def _fmt_dec(self, v):
        try:
            dec = _round_sig(Decimal(str(v)), 10)
            s = format(dec.normalize(), "f")
        except Exception:
            s = f"{v:.10g}"
        if s.startswith("-0") and set(s[1:]).issubset(set("0.")):
            s = s[1:]
        return s

    def _fmt_norm(self, v, display):
        av = abs(v)
        if av != 0 and (av < 1e-9 or av >= 1e10):
            return self._fmt_sci(v, 10, strip=True)
        if display == "NORM2" and 0 < av < 1e-2:
            return self._fmt_sci(v, 10, strip=True)
        return self._fmt_dec(v)

    @staticmethod
    def _dash(s):
        return "−" + s[1:] if s.startswith("-") else s

    def _fmt_any_float(self, v, display, digits):
        if display == "FIX":
            return self._dash(self._fmt_fix(v, digits))
        if display == "SCI":
            return self._dash(self._fmt_sci(v, digits))
        if v.is_integer() and abs(v) < 1e12:
            return self._dash(str(int(v)))
        return self._dash(self._fmt_norm(v, display))

    def _fmt_complex(self, z, display, digits, polar):
        if polar:
            r = abs(z)
            th = self._angle_from_rad(cmath.phase(z))
            return (self._fmt_any_float(r, display, digits) + "∠"
                    + self._fmt_any_float(th, display, digits))
        re, im = z.real, z.imag
        if abs(im) < 1e-12 * max(1.0, abs(re)):
            return self._fmt_any_float(re, display, digits)
        res = self._fmt_any_float(re, display, digits)
        if abs(abs(im) - 1.0) < 1e-12:
            ims = ""
        else:
            ims = self._fmt_any_float(abs(im), display, digits)
        if abs(re) < 1e-12 * max(1.0, abs(im)):
            return ("−" if im < 0 else "") + ims + "i"
        return res + ("+" if im >= 0 else "−") + ims + "i"

    def format_value(self, v, display=None, digits=None, frac="auto", polar=False):
        if display is None:
            display = self.settings.display
        if digits is None:
            digits = self.settings.digits
        if v is None:
            return ""
        if isinstance(v, complex):
            return self._fmt_complex(v, display, digits, polar)
        if isinstance(v, Fraction):
            if frac in ("frac", "auto") and self._frac_ok(v):
                return self._fmt_frac(v)
            v = float(v)
        if isinstance(v, float):
            if not math.isfinite(v):
                raise CalcError("Math ERROR")
            if frac == "frac":
                f = _to_frac(v)
                if self._frac_ok(f):
                    return self._fmt_frac(f)
            return self._fmt_any_float(v, display, digits)
        if isinstance(v, int):
            if frac == "frac" and abs(v) <= 10 ** 12:
                return self._fmt_frac(Fraction(v))
            if display in ("SCI", "FIX"):
                return self._fmt_any_float(float(v), display, digits)
            return self._dash(str(v))
        return str(v)

    def format_sexa(self, v):
        if isinstance(v, complex) or v is None:
            return None
        f = float(v)
        if not (0 <= f < 10000):
            return None
        d = int(f)
        rem = (f - d) * 60
        m = int(rem)
        s = (rem - m) * 60
        s = round(s, 6)
        if s >= 60 - 1e-9:
            s = 0
            m += 1
        if m >= 60:
            m -= 60
            d += 1
        ss = str(int(s)) if abs(s - int(s)) < 1e-9 else f"{s:.6f}".rstrip("0").rstrip(".")
        return f"{d}°{m}′{ss}″"

    # ---------------- 方程求解 ----------------
    @staticmethod
    def solve_quadratic(a, b, c):
        if abs(a) < 1e-15:
            if abs(b) < 1e-15:
                raise CalcError("无解" if abs(c) > 1e-12 else "无穷多解")
            return [complex(-c / b, 0)]
        d = b * b - 4 * a * c
        if d >= 0:
            sq = math.sqrt(d)
            return [complex((-b + sq) / (2 * a), 0), complex((-b - sq) / (2 * a), 0)]
        sq = math.sqrt(-d)
        return [complex(-b / (2 * a), sq / (2 * a)), complex(-b / (2 * a), -sq / (2 * a))]

    @staticmethod
    def _cbrt(x):
        return math.copysign(abs(x) ** (1.0 / 3.0), x)

    @staticmethod
    def solve_cubic(a, b, c, d):
        if abs(a) < 1e-15:
            return CalcEngine.solve_quadratic(b, c, d)
        p = (3 * a * c - b * b) / (3 * a * a)
        q = (2 * b ** 3 - 9 * a * b * c + 27 * a * a * d) / (27 * a ** 3)
        delta = (q / 2) ** 2 + (p / 3) ** 3
        off = b / (3 * a)
        if delta > 1e-18:
            u = CalcEngine._cbrt(-q / 2 + math.sqrt(delta))
            v = CalcEngine._cbrt(-q / 2 - math.sqrt(delta))
            y1 = u + v
            yr = -(u + v) / 2
            yi = math.sqrt(3) * (u - v) / 2
            return [complex(y1 - off, 0), complex(yr - off, yi), complex(yr - off, -yi)]
        if delta < -1e-18:
            r = 2 * math.sqrt(-p / 3)
            th = math.acos((-q / 2) / math.sqrt(-(p / 3) ** 3))
            return [complex(r * math.cos((th + 2 * math.pi * k) / 3) - off, 0) for k in range(3)]
        u = CalcEngine._cbrt(-q / 2)
        return [complex(2 * u - off, 0), complex(-u - off, 0), complex(-u - off, 0)]

    @staticmethod
    def gauss_solve(aug):
        n = len(aug)
        a = [row[:] for row in aug]
        for col in range(n):
            piv = max(range(col, n), key=lambda r: abs(a[r][col]))
            if abs(a[piv][col]) < 1e-12:
                incon = any(
                    abs(a[r][n]) > 1e-9 and all(abs(a[r][c]) < 1e-12 for c in range(n))
                    for r in range(col, n))
                raise CalcError("无解" if incon else "无穷多解")
            a[col], a[piv] = a[piv], a[col]
            pv = a[col][col]
            for r in range(n):
                if r != col and abs(a[r][col]) > 1e-15:
                    f = a[r][col] / pv
                    for c in range(col, n + 1):
                        a[r][c] -= f * a[col][c]
        return [a[i][n] / a[i][i] for i in range(n)]

    # ---------------- 不等式 ----------------
    @staticmethod
    def _real_roots_quad(a, b, c):
        if abs(a) < 1e-15:
            if abs(b) < 1e-15:
                return []
            return [-c / b]
        d = b * b - 4 * a * c
        if d < -1e-12:
            return []
        sq = math.sqrt(max(d, 0.0))
        return [(-b - sq) / (2 * a), (-b + sq) / (2 * a)]

    @staticmethod
    def _real_roots_cubic(a, b, c, d):
        if abs(a) < 1e-15:
            return CalcEngine._real_roots_quad(b, c, d)
        roots = CalcEngine.solve_cubic(a, b, c, d)
        out = []
        for z in roots:
            if abs(z.imag) < 1e-9 * max(1.0, abs(z.real)):
                out.append(z.real)
        return out

    @staticmethod
    def _poly_eval(coeffs, x):
        v = 0.0
        for c in coeffs:
            v = v * x + c
        return v

    @staticmethod
    def _sign_of(x):
        if x > 1e-9:
            return 1
        if x < -1e-9:
            return -1
        return 0

    @staticmethod
    def _rel_ok(sgn, rel):
        return {"<": sgn < 0, "<=": sgn <= 0, ">": sgn > 0, ">=": sgn >= 0}[rel]

    def solve_inequality(self, coeffs, rel):
        roots = (self._real_roots_quad(*coeffs) if len(coeffs) == 3
                 else self._real_roots_cubic(*coeffs))
        roots = sorted(set(round(r, 10) for r in roots))
        strict = rel in (">", "<")
        lt, gt = ("<", ">") if strict else ("≤", "≥")
        if not roots:
            if all(abs(c) < 1e-15 for c in coeffs):
                return "全体实数" if not strict else "无解"
            sgn = self._sign_of(coeffs[0])
            return "全体实数" if self._rel_ok(sgn, rel) else "无解"
        samples = [roots[0] - 1]
        for a, b in zip(roots, roots[1:]):
            samples.append((a + b) / 2)
        samples.append(roots[-1] + 1)
        intervals = []
        lo = None
        for idx, r in enumerate(roots):
            if self._rel_ok(self._sign_of(self._poly_eval(coeffs, samples[idx])), rel):
                intervals.append((lo, r))
            lo = r
        if self._rel_ok(self._sign_of(self._poly_eval(coeffs, samples[-1])), rel):
            intervals.append((lo, None))
        if not intervals:
            return "无解"
        parts = []
        for a, b in intervals:
            fb = self._fmt_any_float(b, "NORM1", None) if b is not None else None
            fa = self._fmt_any_float(a, "NORM1", None) if a is not None else None
            if a is None and b is None:
                return "全体实数"
            if a is None:
                parts.append(f"x{lt}{fb}")
            elif b is None:
                parts.append(f"x{gt}{fa}")
            else:
                parts.append(f"{fa}{lt}x{lt}{fb}")
        return " 或 ".join(parts)

    # ---------------- 统计 ----------------
    @staticmethod
    def _med(lst):
        if not lst:
            return 0.0
        m = len(lst)
        if m % 2:
            return float(lst[m // 2])
        return (lst[m // 2 - 1] + lst[m // 2]) / 2.0

    def stats_1var(self, data):
        n = 0.0
        sx = sx2 = 0.0
        xs = []
        for x, f in data:
            f = float(f)
            if f <= 0:
                continue
            n += f
            sx += f * x
            sx2 += f * x * x
            xs.append((float(x), int(round(f))))
        if n == 0:
            raise CalcError("无数据")
        mean = sx / n
        varp = max(0.0, sx2 / n - mean * mean)
        expanded = []
        for x, f in xs:
            expanded.extend([x] * min(f, 100000))
        expanded.sort()
        half = len(expanded) // 2
        return {
            "n": n, "mean": mean, "sx": sx, "sx2": sx2,
            "sdp": math.sqrt(varp),
            "sds": math.sqrt(varp * n / (n - 1)) if n > 1 else 0.0,
            "min": expanded[0], "max": expanded[-1],
            "q1": self._med(expanded[:half]),
            "med": self._med(expanded),
            "q3": self._med(expanded[half + (len(expanded) % 2):]),
        }

    def stats_lin(self, data):
        n = sx = sy = sxx = syy = sxy = 0.0
        for x, y, f in data:
            f = float(f)
            if f <= 0:
                continue
            n += f
            sx += f * x
            sy += f * y
            sxx += f * x * x
            syy += f * y * y
            sxy += f * x * y
        if n < 2:
            raise CalcError("无数据")
        den = n * sxx - sx * sx
        if abs(den) < 1e-15:
            raise CalcError("无解")
        b = (n * sxy - sx * sy) / den
        a = (sy - b * sx) / n
        rden = math.sqrt((n * sxx - sx * sx) * (n * syy - sy * sy))
        r = (n * sxy - sx * sy) / rden if rden > 1e-15 else 0.0
        meanx, meany = sx / n, sy / n
        varx = max(0.0, sxx / n - meanx * meanx)
        vary = max(0.0, syy / n - meany * meany)
        return {
            "n": n, "a": a, "b": b, "r": r,
            "meanx": meanx, "meany": meany,
            "sx": sx, "sy": sy, "sxx": sxx, "syy": syy, "sxy": sxy,
            "sdx": math.sqrt(varx), "sdy": math.sqrt(vary),
        }

    def stats_quad(self, data):
        n = sx = sx2 = sx3 = sx4 = sy = sxy = sx2y = 0.0
        for x, y, f in data:
            f = float(f)
            if f <= 0:
                continue
            n += f
            sx += f * x
            sx2 += f * x * x
            sx3 += f * x ** 3
            sx4 += f * x ** 4
            sy += f * y
            sxy += f * x * y
            sx2y += f * x * x * y
        if n < 3:
            raise CalcError("无数据")
        aug = [
            [n, sx, sx2, sy],
            [sx, sx2, sx3, sxy],
            [sx2, sx3, sx4, sx2y],
        ]
        a, b, c = self.gauss_solve(aug)
        return {"n": n, "a": a, "b": b, "c": c,
                "meanx": sx / n, "meany": sy / n,
                "sx": sx, "sy": sy, "sxx": sx2, "sxy": sxy}

    # ---------------- 单位换算 ----------------
    @staticmethod
    def convert_unit(cat, v, frm, to):
        if cat == "温度":
            if frm == "℃":
                k = v + 273.15
            elif frm == "℉":
                k = (v + 459.67) * 5 / 9
            else:
                k = v
            if to == "℃":
                return k - 273.15
            if to == "℉":
                return k * 9 / 5 - 459.67
            return k
        u = UNITS.get(cat, {})
        if frm not in u or to not in u:
            raise CalcError("单位错误")
        return v * u[frm] / u[to]


def _dec_scale(k):
    return Decimal(1) if k <= 0 else Decimal("1." + "0" * k)


def _round_sig(dec, sig):
    if dec == 0:
        return Decimal(0)
    e = dec.adjusted()
    return dec.quantize(Decimal("1e%d" % (e - sig + 1)), rounding=ROUND_HALF_UP)
