# -*- coding: utf-8 -*-
"""科学计算器 —— 计算引擎(纯 Python,不依赖 Qt,可独立运行自测)

功能:
- 递归下降表达式解析:+ - × ÷ ^ mod、隐式乘法(2π、3(4+5)、2sin30)、
  一元负号、后缀算符(! 阶乘、% 百分比、² 平方、³ 立方、⁻¹ 倒数)
- 函数:sin/cos/tan(含反三角、双曲)、ln/log/log₂/exp/√/∛、abs/int/floor/ceil/sign、
  round/root/gcd/lcm/max/min/rand/randint
- 常量:π、e、φ(黄金比)、τ(2π);变量:ans(上次结果)、m(内存)
- DEG/RAD 角度模式(影响三角与反三角)
- 结果格式化:12 位有效数字,过大/过小自动转科学计数(×10ⁿ 上标显示)

直接运行本文件将执行一批内置自测用例:python engine.py
"""
from __future__ import annotations

import math
import random
import re
import sys
from decimal import Decimal, ROUND_HALF_UP


class CalcError(Exception):
    """用户可见的计算错误(语法 / 除零 / 定义域 / 溢出)"""


# ---------------------------------------------------------------------------
# 归一化:把界面显示用的记号统一转成规范写法
# ---------------------------------------------------------------------------
_NORMALIZE_STEPS = [
    # 反三角与双曲反函数的上标 ⁻¹ 记法要先于通用 ⁻¹ 替换
    (re.compile(r"sinh⁻¹"), "asinh"),
    (re.compile(r"cosh⁻¹"), "acosh"),
    (re.compile(r"tanh⁻¹"), "atanh"),
    (re.compile(r"sin⁻¹"), "asin"),
    (re.compile(r"cos⁻¹"), "acos"),
    (re.compile(r"tan⁻¹"), "atan"),
    # 通用替换
    (re.compile(r"⁻¹"), "^(-1)"),           # 倒数后缀
    (re.compile(r"²"), "^2"),               # 平方后缀
    (re.compile(r"³"), "^3"),               # 立方后缀
    (re.compile(r"∛"), "cbrt"),             # 立方根
    (re.compile(r"(?<![a-zA-Z])pi(?![a-zA-Z])"), "π"),   # 手输 pi
    (re.compile(r"(?<![a-zA-Z])phi(?![a-zA-Z])"), "φ"),  # 手输 phi
    (re.compile(r"(?<![a-zA-Z])tau(?![a-zA-Z])"), "τ"),  # 手输 tau
    (re.compile(r"×|·|✕"), "*"),
    (re.compile(r"÷|∕"), "/"),
    (re.compile(r"−|–|—"), "-"),            # 各类横线统一为减号
    (re.compile(r"%"), "/100"),             # % 一律按百分比;取模请用 mod
]


def _normalize(expr: str) -> str:
    """把显示记号归一化为规范记号(保留空白,空格在词法层充当词分隔符)"""
    s = expr
    for pattern, repl in _NORMALIZE_STEPS:
        s = pattern.sub(repl, s)
    return s


# ---------------------------------------------------------------------------
# 词法分析
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(
    r"""
      (?P<num>\d+\.\d*|\.\d+|\d+)        # 数字(支持 .5 / 5. / 5.2)
    | (?P<name>[A-Za-z₂]+)               # 标识符(函数 / 变量 / mod)
    | (?P<const>[πφτ])                   # 单字符常量
    | (?P<sqrt>√)                        # 平方根符号(按函数名处理)
    | (?P<sym>[-+*/^(),!])               # 运算符与括号
    """,
    re.VERBOSE,
)

# mod 按中缀运算符处理
_NAMES_AS_OP = {"mod"}
# 变量(从外部注入求值环境)
_VARIABLES = {"ans", "m"}


def _tokenize(s: str) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    pos = 0
    while pos < len(s):
        if s[pos] in " \t\r\n":              # 空白仅作词分隔符
            pos += 1
            continue
        m = _TOKEN_RE.match(s, pos)
        if m is None:
            raise CalcError(f"无法识别的字符:{s[pos]}")
        pos = m.end()
        if m.lastgroup == "num":
            tokens.append(("num", float(m.group("num"))))
        elif m.lastgroup == "name":
            name = m.group("name").replace("₂", "2").lower()
            if name == "e":                  # 自然常数按常量处理
                tokens.append(("const", "e"))
            elif name in _NAMES_AS_OP:
                tokens.append(("op", name))
            elif name in _VARIABLES:
                tokens.append(("var", name))
            else:
                tokens.append(("func", name))   # 是否为合法函数在语法/求值层校验
        elif m.lastgroup == "const":
            tokens.append(("const", m.group("const")))
        elif m.lastgroup == "sqrt":
            tokens.append(("func", "√"))
        else:
            sym = m.group("sym")
            kind = {"(": "lp", ")": "rp", "!": "fact"}.get(sym, "op")
            tokens.append((kind, sym))
    return tokens


# ---------------------------------------------------------------------------
# 常量与函数实现
# ---------------------------------------------------------------------------
# 常量表(π 恒为弧度数值,角度模式只影响三角函数换算——与 TI 计算器语义一致)
_CONSTANTS = {
    "π": math.pi,
    "e": math.e,
    "φ": (1 + math.sqrt(5)) / 2,   # 黄金分割比
    "τ": 2 * math.pi,              # 2π
}


def _to_rad(x: float, angle: str) -> float:
    """按角度模式把自变量转为弧度"""
    return math.radians(x) if angle == "DEG" else x


def _from_rad(x: float, angle: str) -> float:
    """按角度模式把弧度结果转回显示值"""
    return math.degrees(x) if angle == "DEG" else x


def _fn_sin(x: float, ang: str) -> float:
    return math.sin(_to_rad(x, ang))


def _fn_cos(x: float, ang: str) -> float:
    return math.cos(_to_rad(x, ang))


def _fn_tan(x: float, ang: str) -> float:
    rad = _to_rad(x, ang)
    if abs(math.cos(rad)) < 1e-15:          # 90°/270° 等处正切无定义
        raise CalcError("tan 在此处无定义")
    return math.tan(rad)


def _fn_asin(x: float, ang: str) -> float:
    if not -1.0 <= x <= 1.0:
        raise CalcError("超出 asin 定义域(|x|≤1)")
    return _from_rad(math.asin(x), ang)


def _fn_acos(x: float, ang: str) -> float:
    if not -1.0 <= x <= 1.0:
        raise CalcError("超出 acos 定义域(|x|≤1)")
    return _from_rad(math.acos(x), ang)


def _fn_atan(x: float, ang: str) -> float:
    return _from_rad(math.atan(x), ang)


def _fn_ln(x: float, ang: str) -> float:
    if x <= 0:
        raise CalcError("超出对数定义域(参数须大于 0)")
    return math.log(x)


def _fn_log(args: list[float], ang: str) -> float:
    """log(x) 为常用对数;log(x, b) 为以 b 为底"""
    if len(args) == 2:
        x, b = args
        if x <= 0 or b <= 0 or b == 1:
            raise CalcError("超出对数定义域")
        return math.log(x, b)
    return math.log10(args[0])


def _fn_sqrt(x: float, ang: str) -> float:
    if x < 0:
        raise CalcError("负数没有实平方根")
    return math.sqrt(x)


def _fn_cbrt(x: float, ang: str) -> float:
    # 负数也返回实立方根
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


def _fn_factorial(x: float, ang: str) -> float:
    if x < 0:
        raise CalcError("阶乘要求非负数")
    if x == int(x):
        if x > 500:
            raise CalcError("阶乘参数过大")
        try:
            return float(math.factorial(int(x)))
        except OverflowError:
            raise CalcError("结果超出表示范围")
    try:
        return math.gamma(x + 1.0)          # 非整数阶乘用 Γ(x+1)
    except (ValueError, OverflowError):
        raise CalcError("结果超出表示范围")


def _fn_pow_exp(base: float, exp: float) -> float:
    """幂运算 base ** exp(负底非整指数报错,避免落入复数)"""
    if base == 0 and exp < 0:
        raise CalcError("除数不能为零")
    if base < 0 and exp != int(exp):
        raise CalcError("负数的非整数次幂没有实数解")
    try:
        return base ** exp
    except OverflowError:
        raise CalcError("结果超出表示范围")


def _fn_round(args: list[float], ang: str) -> float:
    """四舍五入(十进制半进位),round(x) 默认保留 0 位,round(x, n) 保留 n 位"""
    x, n = args[0], (args[1] if len(args) > 1 else 0)
    q = Decimal(1).scaleb(-int(n))
    try:
        return float(Decimal(repr(x)).quantize(q, rounding=ROUND_HALF_UP))
    except Exception:
        return x


def _fn_root(args: list[float], ang: str) -> float:
    """root(x, n):x 的 n 次方根,n 为奇数时支持负数"""
    x, n = args
    if n == 0:
        raise CalcError("根指数不能为 0")
    if x < 0:
        if n == int(n) and int(n) % 2 == 1:
            return -((-x) ** (1.0 / n))
        raise CalcError("负数的偶次方根没有实数解")
    return x ** (1.0 / n)


def _fn_gcd(args: list[float], ang: str) -> float:
    a, b = args
    if a != int(a) or b != int(b):
        raise CalcError("gcd 需要整数参数")
    return float(math.gcd(int(a), int(b)))


def _fn_lcm(args: list[float], ang: str) -> float:
    a, b = args
    if a != int(a) or b != int(b):
        raise CalcError("lcm 需要整数参数")
    return float(math.lcm(int(a), int(b)))


def _fn_randint(args: list[float], ang: str) -> float:
    a, b = args
    if a != int(a) or b != int(b):
        raise CalcError("randint 需要整数参数")
    return float(random.randint(int(a), int(b)))


# 函数表:名称 -> (最少参数, 最多参数, 实现(args, angle))
_FUNCTIONS: dict[str, tuple[int, int, object]] = {
    "sin":   (1, 1, lambda a, ang: _fn_sin(a[0], ang)),
    "cos":   (1, 1, lambda a, ang: _fn_cos(a[0], ang)),
    "tan":   (1, 1, lambda a, ang: _fn_tan(a[0], ang)),
    "asin":  (1, 1, lambda a, ang: _fn_asin(a[0], ang)),
    "acos":  (1, 1, lambda a, ang: _fn_acos(a[0], ang)),
    "atan":  (1, 1, lambda a, ang: _fn_atan(a[0], ang)),
    "sinh":  (1, 1, lambda a, ang: math.sinh(a[0])),
    "cosh":  (1, 1, lambda a, ang: math.cosh(a[0])),
    "tanh":  (1, 1, lambda a, ang: math.tanh(a[0])),
    "asinh": (1, 1, lambda a, ang: math.asinh(a[0])),
    "acosh": (1, 1, lambda a, ang: math.acosh(a[0])),
    "atanh": (1, 1, lambda a, ang: math.atanh(a[0])),
    "ln":    (1, 1, lambda a, ang: _fn_ln(a[0], ang)),
    "log":   (1, 2, _fn_log),
    "log2":  (1, 1, lambda a, ang: math.log2(a[0])),
    "log10": (1, 1, lambda a, ang: math.log10(a[0])),
    "exp":   (1, 1, lambda a, ang: math.exp(a[0])),
    "√":     (1, 1, lambda a, ang: _fn_sqrt(a[0], ang)),
    "sqrt":  (1, 1, lambda a, ang: _fn_sqrt(a[0], ang)),
    "cbrt":  (1, 1, lambda a, ang: _fn_cbrt(a[0], ang)),
    "abs":   (1, 1, lambda a, ang: abs(a[0])),
    "int":   (1, 1, lambda a, ang: float(math.trunc(a[0]))),   # 向零取整
    "floor": (1, 1, lambda a, ang: float(math.floor(a[0]))),
    "ceil":  (1, 1, lambda a, ang: float(math.ceil(a[0]))),
    "sign":  (1, 1, lambda a, ang: float((a[0] > 0) - (a[0] < 0))),
    "round": (1, 2, _fn_round),
    "root":  (2, 2, _fn_root),
    "gcd":   (2, 2, _fn_gcd),
    "lcm":   (2, 2, _fn_lcm),
    "max":   (1, 16, lambda a, ang: max(a)),
    "min":   (1, 16, lambda a, ang: min(a)),
    "rand":  (0, 0, lambda a, ang: random.random()),
    "randint": (2, 2, _fn_randint),
}

# 供界面“智能退格”使用的多字符记号(必须按长度降序匹配)
BACKSPACE_TOKENS = sorted(
    list(_FUNCTIONS.keys())
    + [name + "(" for name in _FUNCTIONS.keys()]
    + ["10^(", "π", "φ", "τ", "ans", "mod", "⁻¹", "²", "³"],
    key=len,
    reverse=True,
)


# ---------------------------------------------------------------------------
# 递归下降解析器
# ---------------------------------------------------------------------------
class _Parser:
    """文法(自上而下):

    expr    := term  (('+'|'-') term)*
    term    := unary (('*'|'/'|'mod' unary) | 隐式乘法 unary)*
    unary   := ('-'|'+') unary | power
    power   := postfix ('^' unary)?          # 右结合,−2^2 = −(2^2)
    postfix := primary ('!')*
    primary := num | const | var | '(' expr ')' | func '(' args ')' | func unary
    """

    def __init__(self, tokens: list[tuple[str, object]], angle: str, env: dict[str, float]) -> None:
        self._tokens = tokens
        self._pos = 0
        self._angle = angle
        self._env = env

    # ---- 游标工具 ----
    def _peek(self) -> tuple[str, object] | None:
        return self._tokens[self._pos] if self._pos < len(self._tokens) else None

    def _next(self) -> tuple[str, object]:
        tok = self._peek()
        if tok is None:
            raise CalcError("表达式不完整")
        self._pos += 1
        return tok

    # ---- 各层级 ----
    def parse(self) -> float:
        value = self._expr()
        if self._pos != len(self._tokens):
            raise CalcError("语法错误")
        return value

    def _expr(self) -> float:
        value = self._term()
        while True:
            tok = self._peek()
            if tok is not None and tok[0] == "op" and tok[1] in ("+", "-"):
                self._pos += 1
                rhs = self._term()
                value = value + rhs if tok[1] == "+" else value - rhs
            else:
                return value

    def _term(self) -> float:
        value = self._unary()
        while True:
            tok = self._peek()
            if tok is None:
                return value
            kind, val = tok
            if kind == "op" and val in ("*", "/"):
                self._pos += 1
                rhs = self._unary()
                if val == "*":
                    value *= rhs
                else:
                    if rhs == 0:
                        raise CalcError("除数不能为零")
                    value /= rhs
            elif kind == "op" and val == "mod":
                self._pos += 1
                rhs = self._unary()
                if rhs == 0:
                    raise CalcError("除数不能为零")
                value %= rhs              # Python 语义:结果符号随除数
            elif kind in ("num", "const", "var", "func", "lp"):
                # 隐式乘法:2π、3(4+5)、2sin(30)、)( 等
                value *= self._unary()
            else:
                return value

    def _unary(self) -> float:
        tok = self._peek()
        if tok is not None and tok[0] == "op" and tok[1] in ("-", "+"):
            self._pos += 1
            value = self._unary()
            return -value if tok[1] == "-" else value
        return self._power()

    def _power(self) -> float:
        base = self._postfix()
        tok = self._peek()
        if tok is not None and tok[0] == "op" and tok[1] == "^":
            self._pos += 1
            exp = self._unary()           # 右结合:2^3^2 = 2^(3^2)
            return _fn_pow_exp(base, exp)
        return base

    def _postfix(self) -> float:
        value = self._primary()
        while True:
            tok = self._peek()
            if tok is not None and tok[0] == "fact":
                self._pos += 1
                value = _fn_factorial(value, self._angle)
            else:
                return value

    def _primary(self) -> float:
        tok = self._next()
        kind, val = tok
        if kind == "num":
            return float(val)
        if kind == "lp":
            value = self._expr()
            nxt = self._next()
            if nxt[0] != "rp":
                raise CalcError("括号不匹配")
            return value
        if kind == "const":
            return _CONSTANTS[val]
        if kind == "var":
            return self._env[val]
        if kind == "func":
            name = val
            if name not in _FUNCTIONS:
                raise CalcError(f"未知函数:{name}")
            lo, hi, fn = _FUNCTIONS[name]
            # 带括号:解析参数列表;不带括号:绑定紧随其后的一个一元项(如 sin30)
            nxt = self._peek()
            if nxt is not None and nxt[0] == "lp":
                self._pos += 1
                args: list[float] = []
                if self._peek() is not None and self._peek()[0] == "rp":
                    self._pos += 1            # 空参数列表
                else:
                    args.append(self._expr())
                    while self._peek() is not None and self._peek()[0] == "op" and self._peek()[1] == ",":
                        self._pos += 1
                        args.append(self._expr())
                    end = self._next()
                    if end[0] != "rp":
                        raise CalcError("括号不匹配")
            else:
                args = [self._unary()]
            if not (lo <= len(args) <= hi):
                raise CalcError(f"{name} 参数个数错误")
            result = fn(args, self._angle)
            return float(result)
        raise CalcError("语法错误")


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------
def evaluate(expr: str, *, angle: str = "DEG", ans: float = 0.0, mem: float = 0.0) -> float:
    """求值一个表达式字符串,返回 float;失败抛 CalcError"""
    s = _normalize(expr)
    if not s:
        raise CalcError("表达式为空")
    tokens = _tokenize(s)
    value = _Parser(tokens, angle, {"ans": ans, "m": mem}).parse()
    if math.isnan(value):
        raise CalcError("结果未定义")
    if math.isinf(value):
        raise CalcError("结果超出表示范围")
    return value


# 上标数字(科学计数显示用)
_SUPER_MAP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
              "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "-": "⁻"}


def _superscript(n: int) -> str:
    return "".join(_SUPER_MAP[c] for c in str(n))


def _to_sci(x: float) -> str:
    """把浮点数格式化为 “1.23×10⁵” 形式(负号用数学减号 −)"""
    mantissa, exp = f"{x:.9e}".split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    if mantissa in ("0", "-0"):
        return "0"
    return f"{mantissa}×10{_superscript(int(exp))}".replace("-", "−")


def format_result(x: float) -> str:
    """计算器风格的结果格式化:12 位有效数字,过大/过小转科学计数"""
    if x == 0:
        return "0"
    ax = abs(x)
    if ax >= 1e13 or ax < 1e-6:
        return _to_sci(x)
    s = f"{x:.12g}"
    if "e" in s.lower():
        return _to_sci(x)
    return s.replace("-", "−")


# ---------------------------------------------------------------------------
# 内置自测(python engine.py)
# ---------------------------------------------------------------------------
def _selftest() -> None:  # pragma: no cover
    import math as _m

    try:                                   # Windows 控制台默认 GBK,改用 UTF-8 输出
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    cases = [
        # (表达式, 期望值, kwargs)
        ("1+2×3", 7, {}),
        ("(1+2)×3", 9, {}),
        ("2^3^2", 512, {}),
        ("−2^2", -4, {}),
        ("(−2)^2", 4, {}),
        ("2^−2", 0.25, {}),
        ("5!", 120, {}),
        ("3.5!", 11.631728396567448, {}),
        ("−5!", -120, {}),
        ("200×10%", 20, {}),
        ("50%+10%", 0.6, {}),
        ("2π", 6.283185307179586, {}),
        ("2(3+4)", 14, {}),
        ("2sin30", 1, {}),
        ("sin90", 1, {"angle": "DEG"}),
        ("sin(π÷2)", 1, {"angle": "RAD"}),
        ("sin(π)", 0, {"angle": "RAD"}),
        ("cos(60)", 0.5, {}),
        ("asin(0.5)", 30, {"angle": "DEG"}),
        ("sin⁻¹(0.5)", 30, {"angle": "DEG"}),
        ("tan(π÷4)", 1, {"angle": "RAD"}),
        ("ln e", 1, {}),
        ("log 100", 2, {}),
        ("log(8,2)", 3, {}),
        ("log₂(8)", 3, {}),
        ("10^(2)", 100, {}),
        ("√9", 3, {}),
        ("√(−1)", None, {}),               # 应报错
        ("∛27", 3, {}),
        ("∛(−8)", -2, {}),
        ("5÷0", None, {}),                 # 除零
        ("5 mod 3", 2, {}),
        ("−7 mod 3", 2, {}),
        ("(−8)^(1÷3)", None, {}),          # 负底非整指数
        ("ans+1", 42, {"ans": 41}),
        ("m×2", 42, {"mem": 21}),
        ("round(3.14159)", 3, {}),
        ("round(3.14159,2)", 3.14, {}),
        ("max(1,5,3)", 5, {}),
        ("gcd(12,18)", 6, {}),
        ("abs(−3)", 3, {}),
        ("1+2)", None, {}),                # 语法错误
        ("1+", None, {}),
        ("abc", None, {}),
        ("1.5×10^3", 1500, {}),
        ("−(2+3)", -5, {}),
        ("5−−3", 8, {}),
        ("1÷3", 1 / 3, {}),
        ("floor(2.7)", 2, {}),
        ("ceil(2.1)", 3, {}),
        ("sign(−9)", -1, {}),
        ("int(−2.9)", -2, {}),
        ("root(−27,3)", -3, {}),
        ("2sin30cos30", 1 * _m.cos(_m.radians(30)), {}),
        ("e^1", _m.e, {}),
    ]

    failed = 0
    for expr, expected, kw in cases:
        try:
            got = evaluate(expr, **kw)
            if expected is None:
                print(f"[FAIL] {expr!r} 期望报错,实际得到 {got}")
                failed += 1
            elif not _m.isclose(got, expected, rel_tol=1e-11, abs_tol=1e-12):
                print(f"[FAIL] {expr!r} 期望 {expected},实际 {got}")
                failed += 1
        except CalcError as err:
            if expected is not None:
                print(f"[FAIL] {expr!r} 意外报错:{err}")
                failed += 1

    # tan 在 90° 无定义
    try:
        evaluate("tan90")
        print("[FAIL] tan90 应报错")
        failed += 1
    except CalcError:
        pass

    # 格式化
    fmt_cases = [
        (0.1 + 0.2, "0.3"),
        (1 / 3, "0.333333333333"),
        (123456789012.0, "123456789012"),
        (1e20, "1×10²⁰"),
        (-1.5e-7, "−1.5×10⁻⁷"),
        (0.0, "0"),
        (7.0, "7"),
        (-0.000001, "−1×10⁻⁶"),
    ]
    for value, expected in fmt_cases:
        got = format_result(value)
        if got != expected:
            print(f"[FAIL] format_result({value!r}) 期望 {expected!r},实际 {got!r}")
            failed += 1

    if failed:
        raise SystemExit(f"自测失败:{failed} 项")
    print(f"engine.py 自测全部通过({len(cases) + 1} 组求值 + {len(fmt_cases)} 组格式化)")


if __name__ == "__main__":
    _selftest()
