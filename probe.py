# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
from engine import CalcEngine, tokenize, _POST, _OPS, CONSTANTS, _FUNC_SORTED
e = CalcEngine()
print("_POST:", [(c, [hex(ord(x)) for x in c]) for c in sorted(_POST)])
print("_OPS:", [(c, [hex(ord(x)) for x in c]) for c in sorted(_OPS)])
print("CONST keys:", {k: [hex(ord(x)) for x in k] for k in CONSTANTS})
print("FUNCS:", [(f, [hex(ord(x)) for x in f]) for f in _FUNC_SORTED if any(ord(x) > 127 for x in f)])
for s in ["3²", "2π", "³√(−8)", "2⁻¹", "5!", "3ˣ√(8)", "√(9)+3²+3³+2⁻¹+5!", "sin(π/2)", "x^(2)+1", "2°30′15″"]:
    try:
        toks = tokenize(s, e)
        print(repr(s), "->", [(t.kind, t.value) for t in toks])
    except Exception as ex:
        print(repr(s), "-> ERROR:", ex)
