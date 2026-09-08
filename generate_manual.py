# -*- coding: utf-8 -*-
"""生成《CASIO fx-991CN CW 模拟器 使用说明书》PDF。

依赖 PySide6 的 QTextDocument + QPrinter,离线生成。
运行:
    python generate_manual.py
输出:
    使用说明书.pdf
"""
import os
import sys

from PySide6.QtGui import QGuiApplication, QTextDocument, QFont, QPageSize, QPageLayout
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF

CSS = """
body { font-family:"Microsoft YaHei","Segoe UI",sans-serif; font-size:10pt; color:#1a1d21; }
h1 { font-size:20pt; color:#145c19; text-align:center; margin:0 0 2pt 0; }
p.subtitle { text-align:center; color:#555; font-size:10pt; margin:0 0 2pt 0; }
p.meta { text-align:center; color:#777; font-size:8.5pt; margin:0 0 10pt 0; }
h2 { font-size:13pt; color:#ffffff; background:#2e7d32; padding:4pt 8pt; margin:14pt 0 6pt 0; }
h3 { font-size:11pt; color:#145c19; margin:10pt 0 3pt 0; }
p { margin:4pt 0; line-height:145%; }
ul, ol { margin:4pt 0 4pt 18pt; }
li { margin:2pt 0; line-height:140%; }
table { border-collapse:collapse; margin:5pt 0; }
th { background:#e4efe4; border:0.5pt solid #8fa88f; padding:3pt 6pt; font-weight:bold; }
td { border:0.5pt solid #8fa88f; padding:3pt 6pt; }
code, .key { font-family:"Consolas","Segoe UI",monospace; background:#eef0ee; color:#143a5c; padding:0 2pt; }
.note { background:#fff6e0; border:0.5pt solid #e0c070; padding:5pt 8pt; margin:5pt 0; }
.warn { background:#fdecec; border:0.5pt solid #d88; padding:5pt 8pt; margin:5pt 0; }
"""

HTML = r"""
<h1>CASIO fx-991CN CW 模拟器</h1>
<p class="subtitle">使 用 说 明 书</p>
<p class="meta">版本 v1.0 · 2026 年 8 月</p>

<h2>1. 产品简介</h2>
<p>本软件是一款仿真 CASIO fx-991CN CW 科学计算器的桌面应用程序，基于 <code>Python</code> 与
<code>PySide6</code>(Qt) 开发。它模拟了真实计算器的自然书写表达式、按键布局与屏幕显示，
并实现了从基本四则运算到方程求解、统计回归、复数运算、单位换算等完整功能，可作为日常学习、
工程计算与教学演示的实用工具。</p>
<p>主要特性：</p>
<ul>
  <li>六大计算应用：<b>计算</b> / <b>统计</b> / <b>函数表格</b> / <b>方程</b> / <b>不等式</b> / <b>复数</b>。</li>
  <li>自然书写表达式：支持上下标、根号、分数、科学记数等直观排版。</li>
  <li>完整函数库：三角 / 反三角 / 双曲 / 对数 / 指数 / 取整 / 随机数 / 组合排列 / 坐标转换等。</li>
  <li>变量系统：A–F、X、Y、Z、M 及 Ans，支持记忆与调用。</li>
  <li>用户自定义函数 f(x) / g(x) 与内置科学常数。</li>
  <li>显示格式控制：NORM / SCI / FIX、分数(假 / 带)、度分秒、S⇔D 切换。</li>
  <li>方程求解、不等式求解、统计回归与 11 类单位换算。</li>
</ul>

<h2>2. 安装与启动</h2>
<h3>2.1 环境要求</h3>
<ul>
  <li>操作系统：Windows / macOS / Linux。</li>
  <li>运行环境：Python 3(推荐 3.8 及以上)。</li>
  <li>依赖库：<code>PySide6</code>。</li>
</ul>
<h3>2.2 安装步骤</h3>
<ol>
  <li>安装 Python 并确保 <code>python</code> 命令可用。</li>
  <li>在命令行中安装依赖：<code>pip install PySide6</code>。</li>
</ol>
<h3>2.3 启动程序</h3>
<p>在项目目录下运行：</p>
<p style="margin-left:18pt;"><code>python main.py</code></p>
<p>启动后即进入模拟器主界面，点击顶部“开机”或在关机状态下按 <code>on</code> 键开机。</p>
<h3>2.4 项目文件说明</h3>
<table>
  <tr><th>文件</th><th>作用</th></tr>
  <tr><td><code>main.py</code></td><td>程序入口，初始化 Qt 应用与主窗口。</td></tr>
  <tr><td><code>engine.py</code></td><td>数学引擎（纯 Python，不依赖 Qt），负责解析与求值。</td></tr>
  <tr><td><code>ui_screens.py</code></td><td>各应用屏幕与主窗口、按键路由逻辑。</td></tr>
  <tr><td><code>ui_keypad.py</code></td><td>按键、表达式显示、LCD 屏幕等控件。</td></tr>
  <tr><td><code>test_engine.py</code></td><td>数学引擎单元测试。</td></tr>
  <tr><td><code>test_gui.py</code></td><td>离屏 GUI 冒烟测试（生成各界面截图）。</td></tr>
</table>

<h2>3. 界面概览</h2>
<p>主窗口自上而下依次为：太阳能面板装饰区、型号标识（<code>fx-991CN CW / CLASSWIZ</code>）、
LCD 显示屏、顶部按键行、中部按键行与主键盘区。</p>
<h3>3.1 顶部按键行</h3>
<table>
  <tr><th>按键</th><th>说明</th></tr>
  <tr><td><b>开机</b></td><td>开机 / 从关机状态唤醒。</td></tr>
  <tr><td><b>主屏幕</b></td><td>返回六大应用的主菜单。</td></tr>
  <tr><td><b>设置</b></td><td>打开 / 关闭设置界面。</td></tr>
  <tr><td><b>目录</b></td><td>打开函数与常数目录（CATALOG）。</td></tr>
  <tr><td><b>工具</b></td><td>打开工具菜单（常数、单位换算、函数定义、关于）。</td></tr>
</table>
<h3>3.2 中部按键行</h3>
<table>
  <tr><th>按键</th><th>说明</th></tr>
  <tr><td><b>变量</b></td><td>查看 / 存储 / 调用变量 A–F、X、Y、Z、M。</td></tr>
  <tr><td><b>功能</b></td><td>定义用户函数 f(x) / g(x)。</td></tr>
  <tr><td><b>方向键 + OK</b></td><td>十字导航与确认（方向键选择，OK / EXE 确认）。</td></tr>
  <tr><td><b>▲ ▼（翻页）</b></td><td>浏览计算历史（计算模式）或滚动列表。</td></tr>
</table>
<h3>3.3 主键盘区</h3>
<table>
  <tr><th>按键</th><th>功能</th><th>SHIFT（副功能）</th></tr>
  <tr><td><b>(−)</b></td><td>输入负号</td><td>—</td></tr>
  <tr><td><b>sin / cos / tan</b></td><td>三角函数</td><td>反正弦 / 反余弦 / 反正切</td></tr>
  <tr><td><b>( )</b></td><td>左右括号</td><td>—</td></tr>
  <tr><td><b>0–9</b></td><td>数字</td><td>变量 X/Y/Z/D/E/F/A/B/C</td></tr>
  <tr><td><b>插入</b></td><td>切换插入 / 改写模式</td><td>—</td></tr>
  <tr><td><b>DEL</b></td><td>删除字符</td><td>关机</td></tr>
  <tr><td><b>AC</b></td><td>清除当前输入 / 界面</td><td>清除全部变量与记忆</td></tr>
  <tr><td><b>× ÷ + −</b></td><td>四则运算</td><td>—</td></tr>
  <tr><td><b>SHIFT</b></td><td>切换副功能（锁定）</td><td>—</td></tr>
  <tr><td><b>×10<sup>x</sup></b></td><td>科学记数 ×10^</td><td>—</td></tr>
  <tr><td><b>Ans</b></td><td>引用上次计算结果</td><td>—</td></tr>
  <tr><td><b>格式</b></td><td>打开显示格式设置</td><td>S⇔D（切换分数 / 小数 / 度分秒）</td></tr>
  <tr><td><b>EXE</b></td><td>执行 / 求值 / 确认</td><td>—</td></tr>
</table>
<h3>3.4 状态栏指示</h3>
<ul>
  <li><b>S</b>：SHIFT 已锁定。</li>
  <li><b>D / R / G</b>：角度单位（度 / 弧度 / 百分度）。</li>
  <li><b>NORM1 / NORM2 / SCI / FIX</b>：当前显示格式。</li>
  <li><b>i</b>：复数模式已开启。</li>
  <li><b>改写</b>：处于改写（覆盖）输入模式。</li>
</ul>

<h2>4. 通用操作说明</h2>
<h3>4.1 SHIFT 锁定</h3>
<p>按一次 <b>SHIFT</b> 进入锁定状态（状态栏显示 <b>S</b>），再按其他键即触发其副功能；
再按一次 SHIFT 取消锁定。</p>
<h3>4.2 常用组合键</h3>
<table>
  <tr><th>组合</th><th>功能</th></tr>
  <tr><td><b>SHIFT + DEL</b></td><td>关机。</td></tr>
  <tr><td><b>SHIFT + AC</b></td><td>清除全部变量、Ans 与用户函数定义。</td></tr>
  <tr><td><b>SHIFT + 1~9</b></td><td>输入变量 X / Y / Z / D / E / F / A / B / C。</td></tr>
  <tr><td><b>SHIFT + sin/cos/tan</b></td><td>输入反正弦 / 反余弦 / 反正切。</td></tr>
  <tr><td><b>SHIFT + 格式</b></td><td>S⇔D：在分数 / 小数 / 度分秒显示之间切换。</td></tr>
</table>

<h2>5. 主菜单与六大应用</h2>
<p>开机后进入主屏幕，显示 2×3 的应用入口：</p>
<table>
  <tr><th>图标</th><th>名称</th><th>用途</th></tr>
  <tr><td>＋−×÷</td><td>计算</td><td>基本计算与表达式求值。</td></tr>
  <tr><td>x̄ σ</td><td>统计</td><td>统计计算与回归分析。</td></tr>
  <tr><td>ƒ(x)</td><td>函数表格</td><td>生成函数值表。</td></tr>
  <tr><td>x²</td><td>方程</td><td>联立方程组与二次 / 三次方程求解。</td></tr>
  <tr><td>x²≥</td><td>不等式</td><td>二次 / 三次不等式求解。</td></tr>
  <tr><td>i</td><td>复数</td><td>复数(直角 / 极坐标)运算。</td></tr>
</table>
<p>使用方向键 <b>▲ ▼ ◀ ▶</b> 移动光标选择应用，按 <b>OK</b> 或 <b>EXE</b> 进入；在任何界面按
<b>主屏幕</b> 可随时返回主菜单。</p>

<h2>6. 计算模式（基本计算）</h2>
<h3>6.1 输入与求值</h3>
<p>进入“计算”应用后，直接使用键盘按键或计算机物理键盘输入表达式，按 <b>EXE</b> 求值。
表达式采用自然书写方式显示（分数用分数线、幂用上标、根号用横线等）。</p>
<h3>6.2 基本运算</h3>
<table>
  <tr><th>运算</th><th>输入示例</th><th>说明</th></tr>
  <tr><td>四则运算</td><td><code>1+2×3</code></td><td>遵循先乘除后加减。</td></tr>
  <tr><td>隐式乘法</td><td><code>2(3+1)</code></td><td>省略乘号，等价于 2×(3+1)。</td></tr>
  <tr><td>括号</td><td><code>(2+3)×4</code></td><td>调整运算优先级。</td></tr>
  <tr><td>乘方</td><td><code>2^3</code> → 2<sup>(3)</sup></td><td>x 的 y 次方。</td></tr>
  <tr><td>平方 / 立方</td><td><code>x²</code> <code>x³</code></td><td>后缀运算。</td></tr>
  <tr><td>倒数</td><td><code>x<sup>-1</sup></code></td><td>求 1/x。</td></tr>
  <tr><td>阶乘</td><td><code>5!</code></td><td>支持非整数（伽马函数）。</td></tr>
  <tr><td>百分数</td><td><code>50%</code></td><td>等价于除以 100。</td></tr>
  <tr><td>开平方</td><td><code>√9</code></td><td>平方根。</td></tr>
  <tr><td>开立方</td><td><code>³√8</code></td><td>立方根。</td></tr>
  <tr><td>x 次方根</td><td><code><sup>x</sup>√(n)</code></td><td>根指数写在前面。</td></tr>
  <tr><td>科学记数</td><td><code>3×10^8</code></td><td>3×10⁸。</td></tr>
  <tr><td>分数</td><td><code>1/3</code> 或 <code>1⁄3</code></td><td>以分数形式精确显示。</td></tr>
  <tr><td>带分数</td><td><code>整数 + 分数</code></td><td>如 2∟1/3 表示二又三分之一。</td></tr>
  <tr><td>六十进制</td><td><code>12°30′15″</code></td><td>度分秒输入。</td></tr>
</table>
<h3>6.3 计算结果与历史</h3>
<ul>
  <li>按 <b>AC</b> 清除当前输入；再按一次可继续清空结果。</li>
  <li>使用中部 <b>▲ ▼</b> 翻页键可浏览历史计算记录（最多保留 60 条）。</li>
  <li>使用 <b>Ans</b> 引用上一次计算结果：例如 <code>Ans×2</code>。</li>
  <li>按 <b>SHIFT + 格式（S⇔D）</b> 在 小数 ⇔ 分数 ⇔ 度分秒 之间切换显示形式。</li>
</ul>

<h2>7. 复数模式</h2>
<p>从主菜单进入“复数”应用，或在设置中开启复数后使用。复数模式下可进行含有虚数单位
<code>i</code> 的运算。</p>
<h3>7.1 输入形式</h3>
<ul>
  <li>虚数单位：<code>i</code>（仅复数模式下有效）。</li>
  <li>极坐标：<code>r∠θ</code>，用角度符号 ∠ 连接模与辐角。</li>
</ul>
<h3>7.2 复数运算</h3>
<p>复数支持四则运算、乘方、三角、对数、指数、开方等；相关函数均自动适配复数。</p>
<h3>7.3 复数函数</h3>
<table>
  <tr><th>函数</th><th>输入</th><th>说明</th></tr>
  <tr><td>共轭</td><td><code>Conjg(z)</code></td><td>求共轭复数。</td></tr>
  <tr><td>辐角</td><td><code>Arg(z)</code></td><td>求辐角（按当前角度单位）。</td></tr>
  <tr><td>实部</td><td><code>ReP(z)</code></td><td>取实部。</td></tr>
  <tr><td>虚部</td><td><code>ImP(z)</code></td><td>取虚部。</td></tr>
</table>
<h3>7.4 显示切换</h3>
<p>按 <b>SHIFT + 格式（S⇔D）</b> 可在直角坐标（<code>a+bi</code>）与极坐标（<code>r∠θ</code>）
两种形式之间切换。</p>

<h2>8. 函数目录（CATALOG）</h2>
<p>按 <b>目录</b> 键打开函数目录，可将任意函数或常数插入到当前表达式。目录支持分类浏览与搜索：
左右键切换分类 / 项目面板，上下键选择，直接键入字母或数字可搜索，按 OK 插入。</p>
<p>内置函数按类别整理如下：</p>
<h3>8.1 基本函数</h3>
<table>
  <tr><th>函数</th><th>输入形式</th><th>说明</th></tr>
  <tr><td>平方 / 立方</td><td><code>x²</code> <code>x³</code></td><td>后缀运算。</td></tr>
  <tr><td>倒数</td><td><code>x<sup>-1</sup></code></td><td>1/x。</td></tr>
  <tr><td>乘方</td><td><code>x^y</code></td><td>x 的 y 次方。</td></tr>
  <tr><td>开方</td><td><code>√</code> <code>³√</code> <code><sup>x</sup>√</code></td><td>平方 / 立方 / x 次方根。</td></tr>
  <tr><td>阶乘</td><td><code>x!</code></td><td>阶乘 / 伽马函数。</td></tr>
  <tr><td>常用对数</td><td><code>log(x)</code></td><td>以 10 为底。</td></tr>
  <tr><td>自然对数</td><td><code>ln(x)</code></td><td>以 e 为底。</td></tr>
  <tr><td>任意底对数</td><td><code>log(底, 真数)</code></td><td>任意底对数。</td></tr>
  <tr><td>指数</td><td><code>e^(x)</code></td><td>e 的 x 次方。</td></tr>
  <tr><td>圆周率 / 自然常数</td><td><code>π</code> <code>e</code></td><td>常数。</td></tr>
  <tr><td>绝对值</td><td><code>Abs(x)</code></td><td>取绝对值。</td></tr>
  <tr><td>取整</td><td><code>Int(x)</code></td><td>向 0 取整。</td></tr>
  <tr><td>最大整函数</td><td><code>Intg(x)</code></td><td>不大于 x 的最大整数。</td></tr>
  <tr><td>舍入</td><td><code>Rnd(x)</code></td><td>按当前显示位数舍入。</td></tr>
  <tr><td>随机数</td><td><code>Ran#</code></td><td>0~1 之间随机数。</td></tr>
  <tr><td>随机整数</td><td><code>RanInt(a,b)</code></td><td>a 到 b 之间随机整数。</td></tr>
  <tr><td>最大公约数</td><td><code>GCD(a,b)</code></td><td>两个整数的 GCD。</td></tr>
  <tr><td>最小公倍数</td><td><code>LCM(a,b)</code></td><td>两个整数的 LCM。</td></tr>
  <tr><td>排列</td><td><code>nP r</code></td><td>排列数 nPr。</td></tr>
  <tr><td>组合</td><td><code>nC r</code></td><td>组合数 nCr。</td></tr>
  <tr><td>直角转极</td><td><code>Pol(x,y)</code></td><td>得 r；θ 自动存入变量 Y。</td></tr>
  <tr><td>极转直角</td><td><code>Rec(r,θ)</code></td><td>得 x；y 自动存入变量 Y。</td></tr>
  <tr><td>答案</td><td><code>Ans</code></td><td>上次计算结果。</td></tr>
</table>
<h3>8.2 三角与双曲函数</h3>
<table>
  <tr><th>函数</th><th>输入</th><th>说明</th></tr>
  <tr><td>正弦 / 余弦 / 正切</td><td><code>sin</code> <code>cos</code> <code>tan</code></td><td>三角函数。</td></tr>
  <tr><td>反三角函数</td><td><code>sin<sup>-1</sup></code> 等</td><td>SHIFT + sin / cos / tan。</td></tr>
  <tr><td>双曲函数</td><td><code>sinh</code> <code>cosh</code> <code>tanh</code></td><td>双曲正弦 / 余弦 / 正切。</td></tr>
  <tr><td>反双曲函数</td><td><code>sinh<sup>-1</sup></code> 等</td><td>反双曲函数。</td></tr>
</table>
<p class="note">三角、反三角函数的取值受“角度单位”设置影响（详见解见第 9 节）。</p>

<h2>9. 角度单位</h2>
<p>计算器支持三种角度单位，影响 sin / cos / tan 及其反函数、Arg、Pol / Rec、复数极坐标等：</p>
<table>
  <tr><th>设置</th><th>含义</th></tr>
  <tr><td><b>DEG（度）</b></td><td>1 圆周 = 360°（默认）。</td></tr>
  <tr><td><b>RAD（弧度）</b></td><td>1 圆周 = 2π 弧度。</td></tr>
  <tr><td><b>GRA（百分度）</b></td><td>1 圆周 = 400 百分度。</td></tr>
</table>
<p>在“设置 → 角度单位”中切换，状态栏会显示 <b>D / R / G</b> 以提示当前单位。</p>

<h2>10. 变量、答案与用户函数</h2>
<h3>10.1 变量</h3>
<p>可用的记忆变量为 <code>A B C D E F X Y Z M</code>（共 10 个），初始值均为 0。</p>
<ul>
  <li><b>输入变量</b>：SHIFT + 对应数字键，或在“变量”屏幕中选择并插入。</li>
  <li><b>存储变量</b>：进入“变量”屏幕，选中目标变量后选择“存入”，将当前表达式结果或上一次结果写入该变量。</li>
  <li><b>清零</b>：在“变量”屏幕选择“清零”，或将变量全部清为 0。</li>
  <li><b>批量清除</b>：SHIFT + AC 清除全部变量、Ans 与函数定义。</li>
</ul>
<h3>10.2 答案 Ans</h3>
<p><code>Ans</code> 保存上一次计算的结果，可直接在表达式中引用，例如 <code>Ans + 5</code>。</p>
<h3>10.3 用户自定义函数 f(x) / g(x)</h3>
<p>通过“功能”键或“工具 → f(x)/g(x) 定义”进入定义界面：</p>
<ol>
  <li>自变量使用变量 <b>X</b>，例如定义 <code>f(x) = X² + 2X + 1</code>。</li>
  <li>按 <b>OK / EXE</b> 保存当前行，或点击“保存 f / 保存 g”。</li>
  <li>调用时在目录中选择 <code>f(◦)</code> 或 <code>g(◦)</code>，或直接输入 <code>f(2)</code>。</li>
</ol>
<p class="note">函数未定义时调用会提示“未定义 f(x) / g(x)”；函数递归深度上限为 20 层。</p>

<h2>11. 科学常数</h2>
<p>通过“工具 → 科学常数”或目录的“科学常数”分类，可插入下表所列 17 个内置常数：</p>
<table>
  <tr><th>符号</th><th>名称</th><th>数值</th></tr>
  <tr><td>c<sub>0</sub></td><td>真空光速 (m/s)</td><td>299792458</td></tr>
  <tr><td>e<sub>0</sub></td><td>元电荷 (C)</td><td>1.602176634×10<sup>-19</sup></td></tr>
  <tr><td>g</td><td>重力加速度 (m/s²)</td><td>9.80665</td></tr>
  <tr><td>h</td><td>普朗克常数 (J·s)</td><td>6.62607015×10<sup>-34</sup></td></tr>
  <tr><td>ħ</td><td>约化普朗克常数</td><td>1.054571817×10<sup>-34</sup></td></tr>
  <tr><td>N<sub>A</sub></td><td>阿伏伽德罗常数</td><td>6.02214076×10<sup>23</sup></td></tr>
  <tr><td>k</td><td>玻尔兹曼常数 (J/K)</td><td>1.380649×10<sup>-23</sup></td></tr>
  <tr><td>μ<sub>0</sub></td><td>真空磁导率</td><td>1.25663706212×10<sup>-6</sup></td></tr>
  <tr><td>ε<sub>0</sub></td><td>真空介电常数</td><td>8.8541878128×10<sup>-12</sup></td></tr>
  <tr><td>m<sub>e</sub></td><td>电子质量 (kg)</td><td>9.1093837015×10<sup>-31</sup></td></tr>
  <tr><td>m<sub>p</sub></td><td>质子质量 (kg)</td><td>1.67262192369×10<sup>-27</sup></td></tr>
  <tr><td>m<sub>n</sub></td><td>中子质量 (kg)</td><td>1.67492749804×10<sup>-27</sup></td></tr>
  <tr><td>R</td><td>摩尔气体常数 J/(mol·K)</td><td>8.314462618</td></tr>
  <tr><td>atm</td><td>标准大气压 (Pa)</td><td>101325</td></tr>
  <tr><td>R<sub>∞</sub></td><td>里德伯常数 (1/m)</td><td>10973731.568</td></tr>
  <tr><td>π</td><td>圆周率</td><td>3.141592654</td></tr>
  <tr><td>e</td><td>自然常数</td><td>2.718281828</td></tr>
</table>

<h2>12. 显示格式</h2>
<p>通过“设置 → 显示格式”或按 <b>格式</b> 键进入显示格式设置：</p>
<table>
  <tr><th>格式</th><th>说明</th></tr>
  <tr><td><b>NORM1</b></td><td>常规显示；|x| &lt; 10⁻⁹ 或 ≥ 10¹⁰ 时改用科学记数。</td></tr>
  <tr><td><b>NORM2</b></td><td>常规显示；|x| &lt; 10⁻² 时即改用科学记数（更早切换）。</td></tr>
  <tr><td><b>SCI n</b></td><td>科学记数，n(0~9) 位有效数字。</td></tr>
  <tr><td><b>FIX n</b></td><td>固定小数位，n(0~9) 位。</td></tr>
</table>
<p>选择 SCI 或 FIX 后，按数字键 <b>0~9</b> 设置显示位数。</p>
<h3>12.1 分数显示</h3>
<ul>
  <li><b>假分数 / 带分数</b>：决定结果以假分数还是带分数形式显示。</li>
  <li><b>分数结果 开 / 关</b>：控制结果是否自动以分数形式呈现。</li>
</ul>
<h3>12.2 S⇔D 切换</h3>
<p>按 <b>SHIFT + 格式</b> 可在 小数 ⇔ 分数 ⇔ 度分秒（六十进制）之间循环切换当前结果；
复数结果则在直角坐标与极坐标之间切换。</p>

<h2>13. 统计计算</h2>
<p>从主菜单进入“统计”，提供三种统计模式：</p>
<table>
  <tr><th>模式</th><th>名称</th><th>输入数据</th></tr>
  <tr><td>1-VAR</td><td>单变量统计</td><td>X 与频数。</td></tr>
  <tr><td>a+bx</td><td>线性回归</td><td>X、Y 与频数。</td></tr>
  <tr><td>a+bx+cx²</td><td>二次回归</td><td>X、Y 与频数。</td></tr>
</table>
<p>选择模式后进入数据表格，使用“＋行 / －行”增删数据行，填写完成后按“计算”或 <b>EXE</b> 得到结果。频数小于等于 0 的行会被忽略。</p>
<h3>13.1 单变量统计输出量</h3>
<table>
  <tr><th>符号</th><th>含义</th></tr>
  <tr><td>n</td><td>样本总数。</td></tr>
  <tr><td>均值</td><td>算术平均值。</td></tr>
  <tr><td>Σx</td><td>数据之和。</td></tr>
  <tr><td>Σx²</td><td>数据平方和。</td></tr>
  <tr><td>σx</td><td>总体标准差。</td></tr>
  <tr><td>sx</td><td>样本标准差。</td></tr>
  <tr><td>minX / maxX</td><td>最小值 / 最大值。</td></tr>
  <tr><td>Q1 / Med / Q3</td><td>下四分位数 / 中位数 / 上四分位数。</td></tr>
</table>
<h3>13.2 线性 / 二次回归输出量</h3>
<ul>
  <li><b>线性回归 (a+bx)</b>：得到截距 a、斜率 b、相关系数 r，以及均值、和、平方和、标准差等。</li>
  <li><b>二次回归 (a+bx+cx²)</b>：得到拟合多项式 y = a+bx+cx² 的系数 a、b、c。</li>
</ul>

<h2>14. 方程求解</h2>
<p>从主菜单进入“方程”，提供五种求解模式：</p>
<table>
  <tr><th>模式</th><th>说明</th></tr>
  <tr><td>2 元</td><td>联立一次方程组（2 个未知数）。</td></tr>
  <tr><td>3 元</td><td>联立一次方程组（3 个未知数）。</td></tr>
  <tr><td>4 元</td><td>联立一次方程组（4 个未知数）。</td></tr>
  <tr><td>二次</td><td>一元二次方程 ax²+bx+c=0。</td></tr>
  <tr><td>三次</td><td>一元三次方程 ax³+bx²+cx+d=0。</td></tr>
</table>
<h3>14.1 联立方程组</h3>
<p>按表格填写各方程系数与等号右侧常数（列依次为 a、b、c、d、…、=），按“求解”即可得到各未知数
x、y、z、t 的解。当方程无解或有无数多解时给出相应提示。</p>
<h3>14.2 二次 / 三次方程</h3>
<p>依次输入最高次到常数项系数（二次：a、b、c；三次：a、b、c、d），程序会给出全部根
（含复数根，显示为 x₁、x₂、x₃）。</p>

<h2>15. 不等式求解</h2>
<p>从主菜单进入“不等式”，支持二次与三次多项式不等式。操作流程：</p>
<ol>
  <li>选择次数（二次 ax²+bx+c / 三次 ax³+bx²+cx+d）。</li>
  <li>选择比较符（&gt;、≥、&lt;、≤）。</li>
  <li>填写各项系数，按“求解”。</li>
</ol>
<p>结果以区间或并集形式给出，例如 <code>x&lt;1 或 x&gt;3</code>；无解或全体实数时给出相应提示。</p>

<h2>16. 单位换算</h2>
<p>通过“工具 → 单位换算”进入，选择类别、源单位、目标单位并输入数值，点击“换算”得到结果。
支持的类别与单位如下：</p>
<table>
  <tr><th>类别</th><th>单位</th></tr>
  <tr><td>长度</td><td>m、cm、mm、km、in、ft、yd、mile、海里</td></tr>
  <tr><td>质量</td><td>kg、g、mg、t、lb、oz</td></tr>
  <tr><td>面积</td><td>m²、cm²、mm²、km²、ha、acre、ft²</td></tr>
  <tr><td>体积</td><td>m³、cm³、L、mL、gal(US)、gal(UK)、ft³</td></tr>
  <tr><td>温度</td><td>℃、K、℉（按线性映射换算）</td></tr>
  <tr><td>速度</td><td>m/s、km/h、mph、knot</td></tr>
  <tr><td>能量</td><td>J、kJ、cal、kcal、Wh、eV</td></tr>
  <tr><td>功率</td><td>W、kW、hp、PS</td></tr>
  <tr><td>压强</td><td>Pa、kPa、atm、mmHg、bar、psi</td></tr>
  <tr><td>时间</td><td>s、min、h、day、week、year</td></tr>
  <tr><td>角度</td><td>度、弧度、百分度</td></tr>
</table>

<h2>17. 设置</h2>
<p>按 <b>设置</b> 键进入，可配置以下选项：</p>
<table>
  <tr><th>设置项</th><th>可选值</th></tr>
  <tr><td>角度单位</td><td>度 / 弧度 / 百分度。</td></tr>
  <tr><td>显示格式</td><td>NORM1 / NORM2 / SCI / FIX。</td></tr>
  <tr><td>分数显示</td><td>假分数 / 带分数。</td></tr>
  <tr><td>分数结果</td><td>开 / 关。</td></tr>
  <tr><td>复数</td><td>开 / 关。</td></tr>
  <tr><td>恢复初始设置</td><td>将全部设置重置为默认值。</td></tr>
  <tr><td>关于</td><td>查看软件信息与快捷键提示。</td></tr>
</table>
<p>设置项会自动保存，下次启动时恢复。进入“工具”菜单还可访问：科学常数、单位换算、
f(x)/g(x) 定义与“关于”。</p>

<h2>18. 物理键盘对照表</h2>
<p>本模拟器同时支持计算机物理键盘输入，对照关系如下：</p>
<table>
  <tr><th>物理按键</th><th>对应功能</th></tr>
  <tr><td>0–9、.</td><td>数字与小数点。</td></tr>
  <tr><td>+ - * /</td><td>加、减、乘、除。</td></tr>
  <tr><td>( )</td><td>左右括号。</td></tr>
  <tr><td>^</td><td>乘方（x^y）。</td></tr>
  <tr><td>!</td><td>阶乘。</td></tr>
  <tr><td>%</td><td>百分号。</td></tr>
  <tr><td>Enter / =</td><td>EXE（执行 / 求值）。</td></tr>
  <tr><td>退格 / Delete</td><td>DEL（删除）。</td></tr>
  <tr><td>Esc</td><td>AC（清除）。</td></tr>
  <tr><td>方向键 ↑↓←→</td><td>十字导航。</td></tr>
  <tr><td>PageUp / PageDown</td><td>翻页（历史 / 滚动）。</td></tr>
  <tr><td>Shift</td><td>SHIFT 锁定。</td></tr>
</table>
<p>在目录界面打开时，可直接键入字母 / 数字进行搜索。</p>

<h2>19. 错误信息与常见问题</h2>
<table>
  <tr><th>提示</th><th>原因与处理</th></tr>
  <tr><td><b>Math ERROR</b></td><td>数学错误：除数为 0、负数开偶次方、0^0、结果溢出或超出定义域等。</td></tr>
  <tr><td><b>Syntax ERROR</b></td><td>语法错误：表达式格式不合法、函数参数缺失等。</td></tr>
  <tr><td><b>无解 / 无穷多解</b></td><td>方程或不等式没有解，或有无穷多解。</td></tr>
  <tr><td><b>数据无效 / 系数无效</b></td><td>统计或方程表格中填写了无法解析的数值。</td></tr>
  <tr><td><b>未定义 f(x) / g(x)</b></td><td>调用了尚未定义的用户函数，请先完成定义。</td></tr>
</table>
<h3>常见问题</h3>
<ul>
  <li><b>为什么负数开方报错？</b> 实数模式下负数不能开偶次方；请开启复数模式后重试。</li>
  <li><b>如何切换分数与小数显示？</b> 按 SHIFT + 格式（S⇔D）。</li>
  <li><b>如何清零所有数据？</b> 按 SHIFT + AC。</li>
  <li><b>如何关机？</b> 按 SHIFT + DEL。</li>
</ul>

<h2>20. 注意事项</h2>
<ul>
  <li>输入负数请使用 ASCII 减号 <code>-</code>；从外部粘贴含全角负号（−）的内容时会自动转换。</li>
  <li>数值显示与舍入统一采用四舍五入（ROUND_HALF_UP）规则，以保证显示与计算一致。</li>
  <li>极坐标 / 直角坐标转换函数 Pol、Rec 会自动将结果写入变量 Y，请注意其副作用。</li>
  <li>变量 X 同时被函数表格、用户函数 f(x)/g(x) 使用，计算过程中其值可能被临时修改。</li>
</ul>

<p style="text-align:center;color:#888;margin-top:16pt;">— 说明书完 —</p>
"""


def main():
    app = QGuiApplication(sys.argv)

    doc = QTextDocument()
    doc.setDefaultFont(QFont("Microsoft YaHei", 10))
    doc.setDefaultStyleSheet(CSS)
    doc.setHtml(HTML)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "使用说明书.pdf")

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(out)
    printer.setPageSize(QPageSize(QPageSize.A4))
    layout = QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait,
                         QMarginsF(14, 14, 14, 14), QPageLayout.Millimeter)
    printer.setPageLayout(layout)
    printer.setResolution(300)

    doc.print_(printer)

    size = os.path.getsize(out)
    print(f"OK: {out} ({size} bytes)")


if __name__ == "__main__":
    main()