# -*- coding: utf-8 -*-
"""函数图像绘制引擎(纯 Python,不依赖 Qt,可独立运行自测)

支持四类曲线,由表达式自动识别:

1. 显函数    y = f(x)                例:`x^2-2x-3`、`y=sin(x)`、`1/x`
2. 隐函数    F(x,y) = 0              例:`x^2+y^2=25`、`x^2/9-y^2/4=1`、`y^2=2x`
3. 参数方程  x=f(t), y=g(t)          例:`x=3cos(t), y=2sin(t)`
4. 极坐标    r = f(θ)                例:`r=1-sin(θ)`、`r=2cos(3θ)`

可选参数范围后缀:`x=cos(t), y=sin(t), t=-6.28..6.28`、`r=θ, θ=0..12.57`
(范围两端可以是任意常量表达式,如 `2π`、`π/2`)

三角函数的自变量一律按弧度处理(数学绘图惯例)。
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable

from engine import CalcError, compile_expression, evaluate, expression_variables

# 曲线类型
EXPLICIT = "explicit"
IMPLICIT = "implicit"
PARAMETRIC = "parametric"
POLAR = "polar"

KIND_NAMES = {
    EXPLICIT: "显函数",
    IMPLICIT: "隐函数",
    PARAMETRIC: "参数方程",
    POLAR: "极坐标",
}

# 表达式解析中的各种模式
_ASSIGN_RE = re.compile(r"^\s*([^=]+?)\s*=\s*(.+)$", re.S)
_RANGE_RE = re.compile(r",\s*(?:t|θ)\s*=\s*([^,]+?)\s*\.\.\s*([^,]+?)\s*$", re.I)
_PARAM_RE = re.compile(r"^\s*x\s*=\s*(.*)\s*,\s*y\s*=\s*(.*)$", re.S)

DEFAULT_PARAM_RANGE = (-2 * math.pi, 2 * math.pi)   # 参数方程默认 t 范围
DEFAULT_POLAR_RANGE = (0.0, 2 * math.pi)            # 极坐标默认 θ 范围

# 采样时可能遇到的各种数值异常,统一按“该点无定义”处理
_NUMERIC_ERRORS = (CalcError, ValueError, OverflowError, ZeroDivisionError)


# ---------------------------------------------------------------------------
# 曲线描述
# ---------------------------------------------------------------------------
@dataclass
class CurveSpec:
    """一条曲线的描述"""

    text: str                                  # 原始输入
    kind: str                                  # EXPLICIT / IMPLICIT / PARAMETRIC / POLAR
    label: str                                 # 图例标签
    fn: Callable | None = None                 # 显函数 f(x) / 隐函数 F(x,y) / 极坐标 r(θ)
    fn_x: Callable | None = None               # 参数方程 x(t)
    fn_y: Callable | None = None               # 参数方程 y(t)
    t_range: tuple[float, float] | None = None  # 参数 / 极角范围

    @property
    def kind_name(self) -> str:
        return KIND_NAMES.get(self.kind, self.kind)


@dataclass
class SampleResult:
    """一条曲线的采样结果"""

    kind: str
    polylines: list[list[tuple[float, float]]] = field(default_factory=list)
    segments: list[tuple[float, float, float, float]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 表达式解析:自动识别曲线类型
# ---------------------------------------------------------------------------
def _compile(text: str) -> Callable:
    """编译表达式(绘图统一用弧度)"""
    return compile_expression(text, angle="RAD")


def _vars(text: str, context: str) -> set[str]:
    """取表达式中的变量集合,解析失败时给出带上下文的错误"""
    try:
        return expression_variables(text)
    except CalcError as err:
        raise CalcError(f"{context}:{err}") from None


def _require_only(found: set[str], allowed: set[str], context: str) -> None:
    """校验表达式只使用了允许的变量(避免画布静默空白)"""
    extra = found - allowed
    if extra:
        raise CalcError(
            f"{context}不支持变量 {'、'.join(sorted(extra))}"
            f"(可用 {'、'.join(sorted(allowed))})"
        )


def _parse_range(lo_text: str, hi_text: str) -> tuple[float, float]:
    """解析参数范围端点(支持 2π、π/2 之类的常量表达式)"""
    lo = evaluate(lo_text, angle="RAD")
    hi = evaluate(hi_text, angle="RAD")
    if hi <= lo:
        raise CalcError("参数范围的上限必须大于下限")
    return lo, hi


def parse_curve(text: str, default_param_range=DEFAULT_PARAM_RANGE,
                default_polar_range=DEFAULT_POLAR_RANGE) -> CurveSpec:
    """把一行文本解析成 CurveSpec;无法识别时抛 CalcError"""
    raw = text.strip()
    if not raw:
        raise CalcError("表达式为空")
    body = raw

    # ---- 可选参数范围:..., t=-5..5 / θ=0..2π ----
    t_range: tuple[float, float] | None = None
    m_range = _RANGE_RE.search(body)
    if m_range:
        t_range = _parse_range(m_range.group(1), m_range.group(2))
        body = body[: m_range.start()].strip()

    # ---- 参数方程:x=f(t), y=g(t) ----
    m_param = _PARAM_RE.match(body)
    if m_param and re.match(r"^\s*x\s*=", body):
        fx_text, fy_text = m_param.group(1).strip(), m_param.group(2).strip()
        if not fx_text or not fy_text:
            raise CalcError("参数方程格式应为 x=..., y=...")
        for part in (fx_text, fy_text):
            _require_only(_vars(part, "参数方程"), {"t", "θ"}, "参数方程")
        return CurveSpec(
            text=raw, kind=PARAMETRIC, label=raw,
            fn_x=_compile(fx_text), fn_y=_compile(fy_text),
            t_range=t_range or default_param_range,
        )

    # ---- 带等号的单条式子 ----
    m_assign = _ASSIGN_RE.match(body)
    if m_assign:
        left, right = m_assign.group(1), m_assign.group(2).strip()
        left_lower = left.lower()

        # 极坐标 r = f(θ)
        if left_lower == "r":
            _require_only(_vars(right, "极坐标"), {"t", "θ"}, "极坐标")
            return CurveSpec(
                text=raw, kind=POLAR, label=raw,
                fn=_compile(right), t_range=t_range or default_polar_range,
            )

        # 只给了 x=... 而没有 y=...:参数方程需要成对
        if left_lower == "x":
            raise CalcError("参数方程需要写成 x=..., y=... 两部分")

        # 显函数 y = f(x):左边只有 y 且右边不含 y
        if left_lower == "y":
            right_vars = _vars(right, "显函数")
            if "y" not in right_vars:
                _require_only(right_vars, {"x"}, "显函数")
                return CurveSpec(text=raw, kind=EXPLICIT, label=raw, fn=_compile(right))

        # 其余含 y 的等式按隐函数 F(x,y)=0 处理(把右边移到左边)
        implicit_text = f"({left})-({right})"
        _require_only(_vars(implicit_text, "隐函数"), {"x", "y"}, "隐函数")
        return CurveSpec(text=raw, kind=IMPLICIT, label=raw, fn=_compile(implicit_text))

    # ---- 裸表达式:默认显函数 ----
    bare_vars = _vars(body, "显函数")
    if "y" in bare_vars:
        raise CalcError("含 y 的式子请写成等式,例如 x^2+y^2=25")
    _require_only(bare_vars, {"x"}, "显函数")
    return CurveSpec(text=raw, kind=EXPLICIT, label=raw, fn=_compile(body))


def parse_lines(text: str, default_param_range=DEFAULT_PARAM_RANGE,
                default_polar_range=DEFAULT_POLAR_RANGE) -> tuple[list[CurveSpec], list[str]]:
    """解析多行输入(空行与 # 注释跳过),返回 (曲线列表, 错误信息列表)"""
    curves: list[CurveSpec] = []
    errors: list[str] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            curves.append(parse_curve(stripped, default_param_range, default_polar_range))
        except CalcError as err:
            errors.append(f"第 {line_no} 行:{err}")
    return curves, errors


# ---------------------------------------------------------------------------
# 视口(数学坐标 ↔ 屏幕坐标)
# ---------------------------------------------------------------------------
@dataclass
class Viewport:
    x_min: float = -10.0
    x_max: float = 10.0
    y_min: float = -6.0
    y_max: float = 6.0

    @property
    def width(self) -> float:
        return self.x_max - self.x_min

    @property
    def height(self) -> float:
        return self.y_max - self.y_min

    def math_to_px(self, x: float, y: float, w: int, h: int) -> tuple[float, float]:
        """数学坐标 → 屏幕像素(屏幕 y 向下)"""
        px = (x - self.x_min) / self.width * w
        py = (self.y_max - y) / self.height * h
        return px, py

    def px_to_math(self, px: float, py: float, w: int, h: int) -> tuple[float, float]:
        """屏幕像素 → 数学坐标"""
        x = self.x_min + px / max(w, 1) * self.width
        y = self.y_max - py / max(h, 1) * self.height
        return x, y

    def scaled(self, factor: float, cx: float, cy: float) -> "Viewport":
        """以数学坐标 (cx, cy) 为中心按 factor 缩放"""
        return Viewport(
            cx + (self.x_min - cx) * factor,
            cx + (self.x_max - cx) * factor,
            cy + (self.y_min - cy) * factor,
            cy + (self.y_max - cy) * factor,
        )

    def translated(self, dx: float, dy: float) -> "Viewport":
        """按数学坐标平移"""
        return Viewport(self.x_min + dx, self.x_max + dx, self.y_min + dy, self.y_max + dy)

    def with_aspect(self, w: int, h: int) -> "Viewport":
        """调整纵向范围,使数学坐标的纵横比与画布一致(避免图像变形)"""
        if w <= 0 or h <= 0:
            return self
        target_height = self.width * h / w
        cy = (self.y_min + self.y_max) / 2
        return Viewport(self.x_min, self.x_max, cy - target_height / 2, cy + target_height / 2)


# ---------------------------------------------------------------------------
# 采样
# ---------------------------------------------------------------------------
def _safe_call(fn: Callable, env: dict[str, float]) -> float | None:
    """求值,失败或非有限值返回 None"""
    try:
        value = fn(env)
    except _NUMERIC_ERRORS:
        return None
    if isinstance(value, complex) or not math.isfinite(value):
        return None
    return float(value)


def sample_explicit(fn: Callable, view: Viewport, w: int, h: int) -> SampleResult:
    """按屏幕像素列采样显函数 y=f(x),自动断开无定义点与渐近线"""
    result = SampleResult(kind=EXPLICIT)
    cols = max(2, min(int(w), 2400))
    step = view.width / cols
    break_limit = view.height * 4          # 相邻点跳变超过此值视为渐近线,断开
    far_limit = max(abs(view.y_min), abs(view.y_max)) * 1e4 + 1e4

    current: list[tuple[float, float]] = []
    prev_y: float | None = None
    for i in range(cols + 1):
        x = view.x_min + i * step
        y = _safe_call(fn, {"x": x})
        if y is None or abs(y) > far_limit:
            if current:
                result.polylines.append(current)
                current = []
            prev_y = None
            continue
        if prev_y is not None and abs(y - prev_y) > break_limit:
            if current:
                result.polylines.append(current)
            current = []
        current.append((x, y))
        prev_y = y
    if current:
        result.polylines.append(current)
    return result


def _sample_parametric_points(fn_t: Callable, t_range: tuple[float, float],
                              n: int) -> list[tuple[float, float] | None]:
    """在参数区间上均匀取点,无定义处返回 None(用于断段)"""
    t0, t1 = t_range
    points: list[tuple[float, float] | None] = []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        env = {"t": t, "θ": t, "theta": t}
        try:
            x, y = fn_t(env)
        except _NUMERIC_ERRORS:
            points.append(None)
            continue
        if not (math.isfinite(x) and math.isfinite(y)):
            points.append(None)
            continue
        points.append((x, y))
    return points


def _points_to_polylines(points: list[tuple[float, float] | None],
                         view: Viewport) -> list[list[tuple[float, float]]]:
    """把带断点的点序列切成折线段,并丢弃远在视口之外的点"""
    limit = max(view.width, view.height) * 200 + 200
    polylines: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for point in points:
        if point is None or abs(point[0]) > limit or abs(point[1]) > limit:
            if current:
                polylines.append(current)
                current = []
            continue
        current.append(point)
    if current:
        polylines.append(current)
    return polylines


def sample_parametric(fn_x: Callable, fn_y: Callable, t_range: tuple[float, float],
                      view: Viewport, n: int = 2400) -> SampleResult:
    """参数方程 x=f(t), y=g(t)"""
    def fn_t(env: dict[str, float]) -> tuple[float, float]:
        return fn_x(env), fn_y(env)

    points = _sample_parametric_points(fn_t, t_range, n)
    return SampleResult(kind=PARAMETRIC, polylines=_points_to_polylines(points, view))


def sample_polar(fn: Callable, t_range: tuple[float, float],
                 view: Viewport, n: int = 2400) -> SampleResult:
    """极坐标 r=f(θ) → 直角坐标点"""
    def fn_t(env: dict[str, float]) -> tuple[float, float]:
        r = fn(env)
        theta = env["θ"]
        return r * math.cos(theta), r * math.sin(theta)

    points = _sample_parametric_points(fn_t, t_range, n)
    return SampleResult(kind=POLAR, polylines=_points_to_polylines(points, view))


# ---------------------------------------------------------------------------
# 隐函数:网格求值 + Marching Squares 提取等值线
# ---------------------------------------------------------------------------
def _cell_segments(x0: float, y0: float, x1: float, y1: float,
                   v00: float, v10: float, v11: float, v01: float
                   ) -> list[tuple[float, float, float, float]]:
    """单个网格单元内的等值线段(F=0)

    角点顺序:00=(x0,y0) 10=(x1,y0) 11=(x1,y1) 01=(x0,y1)
    """
    for value in (v00, v10, v11, v01):
        if value != value:                 # NaN:该单元跳过
            return []

    edges: list[tuple[int, float, float]] = []
    if (v00 > 0) != (v10 > 0):             # 下边
        t = v00 / (v00 - v10) if v00 != v10 else 0.5
        edges.append((0, x0 + t * (x1 - x0), y0))
    if (v10 > 0) != (v11 > 0):             # 右边
        t = v10 / (v10 - v11) if v10 != v11 else 0.5
        edges.append((1, x1, y0 + t * (y1 - y0)))
    if (v11 > 0) != (v01 > 0):             # 上边
        t = v11 / (v11 - v01) if v11 != v01 else 0.5
        edges.append((2, x1 - t * (x1 - x0), y1))
    if (v01 > 0) != (v00 > 0):             # 左边
        t = v01 / (v01 - v00) if v01 != v00 else 0.5
        edges.append((3, x0, y1 - t * (y1 - y0)))

    if len(edges) == 2:
        a, b = edges
        return [(a[1], a[2], b[1], b[2])]
    if len(edges) == 4:
        # 鞍点:用单元中心值决定连接方式
        center = (v00 + v10 + v11 + v01) / 4
        pairs = ((0, 3), (1, 2)) if (center > 0) == (v00 > 0) else ((0, 1), (2, 3))
        by_id = {e[0]: e for e in edges}
        segments = []
        for a_id, b_id in pairs:
            if a_id in by_id and b_id in by_id:
                ea, eb = by_id[a_id], by_id[b_id]
                segments.append((ea[1], ea[2], eb[1], eb[2]))
        return segments
    return []


def sample_implicit(fn: Callable, view: Viewport, w: int, h: int,
                    quality: str = "full") -> SampleResult:
    """隐函数 F(x,y)=0:在视口上网格求值,再用 Marching Squares 提取轮廓"""
    result = SampleResult(kind=IMPLICIT)
    if w < 2 or h < 2:
        return result

    base = 220 if quality == "full" else 110
    nx = max(40, min(int(w), base))
    ny = max(40, min(int(h), max(40, int(base * h / max(w, 1)))))

    xs = [view.x_min + view.width * i / nx for i in range(nx + 1)]
    ys = [view.y_min + view.height * j / ny for j in range(ny + 1)]

    # 网格求值(行优先,便于取相邻单元)
    values: list[list[float]] = []
    for y in ys:
        row = []
        for x in xs:
            value = _safe_call(fn, {"x": x, "y": y})
            row.append(float("nan") if value is None else value)
        values.append(row)

    segments = result.segments
    for j in range(ny):
        y0, y1 = ys[j], ys[j + 1]
        row0, row1 = values[j], values[j + 1]
        for i in range(nx):
            segments.extend(_cell_segments(
                xs[i], y0, xs[i + 1], y1,
                row0[i], row0[i + 1], row1[i + 1], row1[i],
            ))
    return result


def sample_curve(curve: CurveSpec, view: Viewport, w: int, h: int,
                 quality: str = "full") -> SampleResult:
    """按曲线类型选择采样方式"""
    if curve.kind == EXPLICIT:
        return sample_explicit(curve.fn, view, w, h)
    if curve.kind == IMPLICIT:
        return sample_implicit(curve.fn, view, w, h, quality)
    if curve.kind == PARAMETRIC:
        n = 2400 if quality == "full" else 1200
        return sample_parametric(curve.fn_x, curve.fn_y, curve.t_range, view, n)
    if curve.kind == POLAR:
        n = 2400 if quality == "full" else 1200
        return sample_polar(curve.fn, curve.t_range, view, n)
    raise CalcError(f"未知的曲线类型:{curve.kind}")


# ---------------------------------------------------------------------------
# 坐标刻度
# ---------------------------------------------------------------------------
def nice_step(span: float, target: int = 10) -> float:
    """返回 1/2/5×10ⁿ 形式的“整齐”刻度间距"""
    if span <= 0 or not math.isfinite(span):
        return 1.0
    raw = span / max(target, 1)
    magnitude = 10.0 ** math.floor(math.log10(raw))
    for multiple in (1.0, 2.0, 5.0, 10.0):
        if raw <= multiple * magnitude * (1 + 1e-9):
            return multiple * magnitude
    return 10.0 * magnitude


def tick_values(v_min: float, v_max: float, step: float) -> list[float]:
    """区间内的刻度位置列表"""
    if step <= 0 or not math.isfinite(step):
        return []
    first = math.ceil(v_min / step - 1e-9) * step
    out: list[float] = []
    value = first
    while value <= v_max + step * 1e-9 and len(out) < 500:
        out.append(0.0 if abs(value) < step * 1e-9 else value)
        value += step
    return out


def format_tick(value: float, step: float) -> str:
    """刻度标签:按步长决定小数位,避免 0.30000000000000004 之类的噪音"""
    if value == 0:
        return "0"
    if abs(value) >= 1e5 or abs(value) < 1e-4:
        mantissa, exp = f"{value:.1e}".split("e")
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exp)}"
    decimals = max(0, -int(math.floor(math.log10(step) + 1e-9)))
    text = f"{value:.{decimals}f}"
    if text.endswith(".0"):
        text = text[:-2]
    return text


# ---------------------------------------------------------------------------
# 内置示例(供界面“示例”菜单使用)
# ---------------------------------------------------------------------------
EXAMPLES: list[tuple[str, str]] = [
    ("一次函数", "y = 2x + 1"),
    ("二次函数", "y = x^2 - 2x - 3"),
    ("三次函数", "y = x^3 - 3x"),
    ("反比例", "y = 1/x"),
    ("三角函数", "y = sin(x)\ny = cos(x)\ny = 0.5sin(2x)"),
    ("指数与对数", "y = exp(x)\ny = ln(x)"),
    ("圆", "x^2 + y^2 = 25"),
    ("椭圆", "x^2/9 + y^2/4 = 1"),
    ("双曲线", "x^2/4 - y^2/9 = 1"),
    ("抛物线(横向)", "y^2 = 2x"),
    ("参数椭圆", "x = 3cos(t), y = 2sin(t)"),
    ("李萨如图形", "x = sin(3t), y = sin(4t)"),
    ("心形线", "r = 1 - sin(θ)"),
    ("玫瑰线", "r = 2cos(3θ)"),
    ("阿基米德螺线", "r = θ/2, θ = 0..12.57"),
    ("摆线", "x = t - sin(t), y = 1 - cos(t), t = 0..12.57"),
]


# ---------------------------------------------------------------------------
# 自测(python plot.py)
# ---------------------------------------------------------------------------
def _selftest() -> None:  # pragma: no cover
    import sys

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    failed = 0

    def check(cond: bool, msg: str) -> None:
        nonlocal failed
        if not cond:
            print(f"[FAIL] {msg}")
            failed += 1

    # ---- 类型识别 ----
    kind_cases = [
        ("x^2-2x-3", EXPLICIT),
        ("y = sin(x)", EXPLICIT),
        ("y=x^2", EXPLICIT),
        ("x^2+y^2=25", IMPLICIT),
        ("x^2/9-y^2/4=1", IMPLICIT),
        ("y^2=2x", IMPLICIT),
        ("x=3cos(t), y=2sin(t)", PARAMETRIC),
        ("x=t^2, y=t^3", PARAMETRIC),
        ("r=1-sin(θ)", POLAR),
        ("r=2cos(3θ)", POLAR),
    ]
    for text, expected in kind_cases:
        try:
            curve = parse_curve(text)
            check(curve.kind == expected, f"{text!r} 识别为 {curve.kind},期望 {expected}")
        except CalcError as err:
            check(False, f"{text!r} 解析失败:{err}")

    # ---- 显函数求值 ----
    curve = parse_curve("x^2-2x-3")
    check(abs(curve.fn({"x": 4.0}) - 5.0) < 1e-9, "显函数 x^2-2x-3 在 x=4 应为 5")

    # ---- 隐函数:圆上的点应满足 F≈0 ----
    circle = parse_curve("x^2+y^2=25")
    for angle in (0.0, 1.0, 2.5, 4.0):
        px, py = 5 * math.cos(angle), 5 * math.sin(angle)
        check(abs(circle.fn({"x": px, "y": py})) < 1e-9, "圆的隐函数在圆上应为 0")

    # ---- 参数方程:椭圆 ----
    ellipse = parse_curve("x=3cos(t), y=2sin(t)")
    check(ellipse.t_range is not None and ellipse.t_range[0] < 0, "参数方程默认范围应包含负值")
    ex, ey = ellipse.fn_x({"t": 0.0, "θ": 0.0}), ellipse.fn_y({"t": 0.0, "θ": 0.0})
    check(abs(ex - 3) < 1e-9 and abs(ey) < 1e-9, "参数椭圆 t=0 应为 (3,0)")

    # ---- 极坐标:心形线 ----
    heart = parse_curve("r=1-sin(θ)")
    check(abs(heart.fn({"θ": math.pi / 2}) - 0.0) < 1e-9, "心形线 θ=π/2 时 r=0")

    # ---- 参数范围解析 ----
    ranged = parse_curve("r=θ, θ=0..2π")
    check(ranged.t_range is not None and abs(ranged.t_range[1] - 2 * math.pi) < 1e-9,
          "范围 0..2π 应解析为 2π")

    # ---- 变量校验:不支持的变量应明确报错(而不是静默空白)----
    bad_cases = ["x^2+y^2", "y = x + t", "r = 1 + x", "x=cos(t), y=sin(x)", "x = cos(t)"]
    for text in bad_cases:
        try:
            parse_curve(text)
            check(False, f"{text!r} 应报变量 / 格式错误")
        except CalcError:
            pass

    # ---- 视口换算 ----
    view = Viewport(-10, 10, -6, 6)
    px, py = view.math_to_px(0.0, 0.0, 800, 600)
    check(abs(px - 400) < 1e-9 and abs(py - 300) < 1e-9, "原点应在画布中心")
    mx, my = view.px_to_math(px, py, 800, 600)
    check(abs(mx) < 1e-9 and abs(my) < 1e-9, "像素坐标往返一致")

    # ---- 显函数采样 ----
    sampled = sample_explicit(parse_curve("sin(x)").fn, view, 400, 300)
    total = sum(len(seg) for seg in sampled.polylines)
    check(total > 380, f"sin(x) 采样点数 {total} 偏少")
    check(len(sampled.polylines) == 1, "sin(x) 应为一整段折线")

    # 1/x 在 0 处断开 → 至少两段
    hyperbola = sample_explicit(parse_curve("1/x").fn, view, 400, 300)
    check(len(hyperbola.polylines) >= 2, "1/x 应在 x=0 处断为两段")

    # ---- 隐函数采样:圆应产生大量线段 ----
    circle_sample = sample_implicit(circle.fn, view, 400, 300)
    check(len(circle_sample.segments) > 100,
          f"圆应产生较多轮廓线段,实际 {len(circle_sample.segments)}")

    # 线段端点应落在圆附近
    if circle_sample.segments:
        ok = True
        for x1, y1, x2, y2 in circle_sample.segments[:50]:
            for px_, py_ in ((x1, y1), (x2, y2)):
                if abs(math.hypot(px_, py_) - 5.0) > 0.2:
                    ok = False
        check(ok, "圆轮廓线段端点应落在圆周附近")

    # ---- 参数/极坐标采样 ----
    param_sample = sample_parametric(ellipse.fn_x, ellipse.fn_y, ellipse.t_range, view)
    check(len(param_sample.polylines) == 1 and len(param_sample.polylines[0]) > 1000,
          "参数椭圆应采样出足够多的点")

    polar_sample = sample_polar(heart.fn, heart.t_range, view)
    check(len(polar_sample.polylines) >= 1, "心形线应采样出折线")

    # ---- 刻度 ----
    check(abs(nice_step(20, 10) - 2.0) < 1e-9, "区间 20 的整齐步长应为 2")
    check(abs(nice_step(1, 10) - 0.1) < 1e-9, "区间 1 的整齐步长应为 0.1")
    check(format_tick(0.30000000000000004, 0.1) == "0.3", "刻度标签应消除浮点噪音")
    check(format_tick(0.0, 1.0) == "0", "零点刻度应为 0")
    check(len(tick_values(-10, 10, 2)) == 11, "[-10,10] 步长 2 应有 11 个刻度")

    # ---- 多行解析 ----
    curves, errors = parse_lines("y=x^2\n\n# 注释\nr=1+cos(θ)\n乱写乱写")
    check(len(curves) == 2 and len(errors) == 1,
          f"多行解析应得到 2 条曲线 1 个错误,实际 {len(curves)}/{len(errors)}")

    # ---- 示例全部可解析 ----
    for name, text in EXAMPLES:
        try:
            parsed, errs = parse_lines(text)
            check(len(parsed) >= 1 and not errs, f"示例「{name}」应能正常解析:{errs}")
        except CalcError as err:
            check(False, f"示例「{name}」解析异常:{err}")

    if failed:
        raise SystemExit(f"plot.py 自测失败:{failed} 项")
    print(f"plot.py 自测全部通过({len(kind_cases)} 组类型识别 + 采样 / 视口 / 刻度 / 示例)")


if __name__ == "__main__":
    _selftest()
