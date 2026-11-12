#!/usr/bin/env python3
"""One-screen signoff summary for a LibreLane run: python3 scripts/show_metrics.py runs/good

Uses the same rules LibreLane itself signs off with on Sky130:
setup must pass in the typical (tt) corners, hold in every corner;
max slew / max cap are reported as warnings."""
import json, sys
from pathlib import Path

run = Path(sys.argv[1] if len(sys.argv) > 1 else "runs/good")
f = run / "final" / "metrics.json"
if not f.exists():
 sys.exit(f"No {f}. Did the run finish? Check: ls {run}/final/")
m = json.loads(f.read_text())

def corners(prefix, match=""):
 return {k.split("corner:")[1]: v for k, v in m.items()
 if k.startswith(prefix + "__corner:") and match in k}

tt_setup = corners("timing__setup__ws", "_tt_")
tt_setup_vio = corners("timing__setup_vio__count", "_tt_")
checks = [
 ("Setup slack, typical corners", min(tt_setup.values()), lambda v: v >= 0),
 ("Setup violations, typical", sum(tt_setup_vio.values()), lambda v: v == 0),
 ("Hold slack, all 9 corners", m["timing__hold__ws"], lambda v: v >= 0),
 ("Hold violations, all corners", m["timing__hold_vio__count"], lambda v: v == 0),
 ("Routing DRC errors", m["route__drc_errors"], lambda v: v == 0),
 ("Magic DRC errors", m["magic__drc_error__count"], lambda v: v == 0),
 ("KLayout DRC errors", m["klayout__drc_error__count"], lambda v: v == 0),
 ("LVS errors", m["design__lvs_error__count"], lambda v: v == 0),
 ("Antenna violating nets", m["antenna__violating__nets"], lambda v: v == 0),
]
info = [
 ("Setup slack, worst corner (ss)", m["timing__setup__ws"]),
 ("Max slew violations (warn)", m["design__max_slew_violation__count"]),
 ("Max cap violations (warn)", m["design__max_cap_violation__count"]),
 ("Cell instances", m["design__instance__count"]),
 ("Die area (um^2)", m["design__die__area"]),
 ("Instance utilization", m["design__instance__utilization"]),
]

print(f"\nSignoff summary for {run}\n" + "=" * 60)
ok_all = True
for label, val, rule in checks:
 ok = rule(val)
 ok_all &= ok
 shown = f"{val:.3f}" if isinstance(val, float) else str(val)
 print(f"{label:32s} {shown:>14s} {'PASS' if ok else 'FAIL'}")
print("-" * 60)
for label, val in info:
 shown = f"{val:.3f}" if isinstance(val, float) else str(val)
 print(f"{label:32s} {shown:>14s}")
print("=" * 60)
print("RESULT:", "ALL SIGNOFF CHECKS PASS." if ok_all
 else "Something needs attention, read the FAIL lines above.")
