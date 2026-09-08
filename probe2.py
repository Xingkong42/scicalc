# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
samples = ["3²", "2π", "2⁻¹", "2°30′15″", "3³", "5!", "√(9)"]
for s in samples:
    print(repr(s), [hex(ord(c)) for c in s])
