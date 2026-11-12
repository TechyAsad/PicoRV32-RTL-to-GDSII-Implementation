
#!/usr/bin/env python3
"""
PicoRV32 / LibreLane PPA extractor.

Usage:
    python3 scripts/extract_ppa.py runs/good

Optional:
    python3 scripts/extract_ppa.py runs/good \
        --config config.json \
        --synth-report out/stat_sky130.txt

Sources:
    config.json
    out/stat_sky130.txt
    runs/<tag>/final/metrics.json
    runs/<tag>/**/*.log

Important:
    - Yosys mapped area is from the standalone Yosys report.
    - Physical standard-cell area is read from metrics.json.
    - Configured utilization and actual reported utilization
      are deliberately reported separately.
    - Power metrics are converted from W to mW.
    - Missing metrics are never assumed to be zero.
"""

import argparse
import json
import re
import sys
from pathlib import Path


# ------------------------------------------------------------
# Arguments and paths
# ------------------------------------------------------------

parser = argparse.ArgumentParser(description="Extract LibreLane PPA metrics")
parser.add_argument("run", nargs="?", default="runs/good",
                    help="LibreLane run directory (default: runs/good)")
parser.add_argument("--config", default="config.json",
                    help="Design configuration JSON")
parser.add_argument("--synth-report", default="out/stat_sky130.txt",
                    help="Standalone Yosys mapped synthesis report")
args = parser.parse_args()

ROOT = Path.cwd()
RUN = Path(args.run)
if not RUN.is_absolute():
    RUN = ROOT / RUN

CONFIG_FILE = Path(args.config)
if not CONFIG_FILE.is_absolute():
    CONFIG_FILE = ROOT / CONFIG_FILE

SYNTH_FILE = Path(args.synth_report)
if not SYNTH_FILE.is_absolute():
    SYNTH_FILE = ROOT / SYNTH_FILE

METRICS_FILE = RUN / "final" / "metrics.json"


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def load_json(path):
    if not path.is_file():
        print(f"WARNING: File not found: {path}")
        return {}

    try:
        with path.open() as f:
            return json.load(f)
    except Exception as exc:
        print(f"WARNING: Could not read {path}: {exc}")
        return {}


def metric(key):
    """Return exact metric value; never use fuzzy matching."""
    return METRICS.get(key)


def show(label, value, unit="", precision=4):
    if value is None:
        print(f"{label:42s}: NOT FOUND")
        return

    if isinstance(value, (int, float)):
        print(f"{label:42s}: {value:,.{precision}f} {unit}".rstrip())
    else:
        print(f"{label:42s}: {value} {unit}".rstrip())


def show_key(label, key, unit="", precision=4):
    value = metric(key)
    show(label, value, unit, precision)
    if value is not None:
        print(f"    Metric key: {key}")
    return value


def parse_yosys_area(path):
    """
    Parse the exact Yosys 'Chip area for module' line.
    This is standalone mapped synthesis area, not final P&R area.
    """
    if not path.is_file():
        return None

    text = path.read_text(errors="ignore")

    matches = re.findall(
        r"Chip area for module .*?:\s*([0-9.eE+-]+)",
        text
    )

    if not matches:
        return None

    return float(matches[-1])


def print_corner_table():
    """Print setup/hold WNS, TNS and violation count per corner."""

    corners = sorted({
        key.split("__corner:", 1)[1]
        for key in METRICS
        if "__corner:" in key
        and key.startswith("timing__setup__ws__corner:")
    })

    if not corners:
        print("No per-corner timing metrics found.")
        return

    print(
        f"{'Corner':32s}"
        f"{'Setup WNS':>13s}"
        f"{'Setup TNS':>14s}"
        f"{'Setup vio':>12s}"
        f"{'Hold WNS':>13s}"
        f"{'Hold vio':>11s}"
    )
    print("-" * 95)

    for corner in corners:
        suffix = "__corner:" + corner

        setup_wns = metric("timing__setup__ws" + suffix)
        setup_tns = metric("timing__setup__tns" + suffix)
        setup_vio = metric("timing__setup_vio__count" + suffix)

        hold_wns = metric("timing__hold__ws" + suffix)
        hold_vio = metric("timing__hold_vio__count" + suffix)

        def cell(v):
            return "N/A" if v is None else f"{v:.3f}"

        print(
            f"{corner:32s}"
            f"{cell(setup_wns):>13s}"
            f"{cell(setup_tns):>14s}"
            f"{cell(setup_vio):>12s}"
            f"{cell(hold_wns):>13s}"
            f"{cell(hold_vio):>11s}"
        )


def scan_logs(patterns, folder_keywords):
    """Collect matching lines from relevant implementation logs."""

    results = []

    if not RUN.exists():
        return results

    for path in RUN.rglob("*.log"):
        parent = path.parent.name.lower()

        if not any(word in parent for word in folder_keywords):
            continue

        try:
            for line in path.read_text(errors="ignore").splitlines():
                if any(re.search(pattern, line, re.I)
                       for pattern in patterns):
                    results.append((path, line.strip()))
        except OSError:
            continue

    return results


# ------------------------------------------------------------
# Load data
# ------------------------------------------------------------

if not RUN.is_dir():
    sys.exit(f"ERROR: Run directory does not exist: {RUN}")

CONFIG = load_json(CONFIG_FILE)
METRICS = load_json(METRICS_FILE)

if not METRICS:
    sys.exit(
        f"ERROR: Could not load {METRICS_FILE}. "
        "Check whether the LibreLane run completed."
    )


# ------------------------------------------------------------
# 1. Run information
# ------------------------------------------------------------

section("1. RUN INFORMATION")

print(f"Project directory       : {ROOT}")
print(f"Run directory           : {RUN}")
print(f"Configuration           : {CONFIG_FILE}")
print(f"Metrics file            : {METRICS_FILE}")
print(f"Synthesis report        : {SYNTH_FILE}")


# ------------------------------------------------------------
# 2. Constraints
# ------------------------------------------------------------

section("2. IMPLEMENTATION CONSTRAINTS")

clock_period = CONFIG.get("CLOCK_PERIOD")
target_util = CONFIG.get("FP_CORE_UTIL")

show("Configured clock period", clock_period, "ns")

if isinstance(clock_period, (int, float)) and clock_period > 0:
    show("Equivalent constrained frequency",
         1000.0 / clock_period, "MHz")

show("Configured FP_CORE_UTIL", target_util, "%")
show("MAX_FANOUT_CONSTRAINT",
     CONFIG.get("MAX_FANOUT_CONSTRAINT"))
show("GPL_CELL_PADDING", CONFIG.get("GPL_CELL_PADDING"))
show("DPL_CELL_PADDING", CONFIG.get("DPL_CELL_PADDING"))

print("\nNOTE: CLOCK_PERIOD is a timing constraint,")
print("not proof of the maximum achievable operating frequency.")


# ------------------------------------------------------------
# 3. Standalone Yosys synthesis
# ------------------------------------------------------------

section("3. STANDALONE YOSYS SYNTHESIS")

yosys_area = parse_yosys_area(SYNTH_FILE)

show("Standalone mapped synthesis area", yosys_area, "um^2", 3)

if yosys_area is None:
    print("Could not parse 'Chip area for module' from report.")
    print("Inspect the Yosys report manually.")

print("Source: standalone stat_sky130.txt")
print("Caution: this may not use identical settings to LibreLane synthesis.")


# ------------------------------------------------------------
# 4. Final physical area and utilization
# ------------------------------------------------------------

section("4. FINAL PHYSICAL AREA AND UTILIZATION")

# Do not confuse this alias with standard-cell area.
show_key(
    "design__instance__area (raw metric)",
    "design__instance__area", "um^2", 3
)

show_key(
    "Final standard-cell area",
    "design__instance__area__stdcell", "um^2", 3
)

show_key(
    "Final die area",
    "design__die__area", "um^2", 3
)

show_key(
    "Final core area",
    "design__core__area", "um^2", 3
)

actual_util = metric("design__instance__utilization")

if actual_util is not None:
    show("Actual reported instance utilization",
         actual_util * 100.0, "%", 4)
else:
    show("Actual reported instance utilization", None)

if target_util is not None:
    show("Configured target utilization", target_util, "%")

show_key(
    "Total instance count",
    "design__instance__count", "", 0
)


# ------------------------------------------------------------
# 5. Timing
# ------------------------------------------------------------

section("5. AGGREGATE TIMING METRICS")

show_key("Worst setup slack / WNS",
         "timing__setup__ws", "ns")

show_key("Setup TNS",
         "timing__setup__tns", "ns")

show_key("Aggregate setup violations",
         "timing__setup_vio__count", "", 0)

show_key("Worst hold slack / WNS",
         "timing__hold__ws", "ns")

show_key("Hold TNS",
         "timing__hold__tns", "ns")

show_key("Aggregate hold violations",
         "timing__hold_vio__count", "", 0)

print("\nPER-CORNER TIMING")
print_corner_table()

# Identify worst setup corner from exact per-corner metrics.
setup_corner_values = {
    key.split("__corner:", 1)[1]: value
    for key, value in METRICS.items()
    if key.startswith("timing__setup__ws__corner:")
    and isinstance(value, (int, float))
}

if setup_corner_values:
    worst_corner = min(setup_corner_values, key=setup_corner_values.get)
    show("Worst setup corner", worst_corner)
    show("Worst corner setup WNS",
         setup_corner_values[worst_corner], "ns")


# ------------------------------------------------------------
# 6. Clock tree and timing repair
# ------------------------------------------------------------

section("6. CLOCK TREE AND TIMING REPAIR")

show_key(
    "Final clock-buffer instances",
    "design__instance__count__class:clock_buffer", "", 0
)

show_key(
    "Final clock-inverter instances",
    "design__instance__count__class:clock_inverter", "", 0
)

show_key(
    "Timing-repair buffer instances",
    "design__instance__count__class:timing_repair_buffer", "", 0
)

show_key(
    "Timing-repair buffer area",
    "design__instance__area__class:timing_repair_buffer",
    "um^2", 3
)

show_key(
    "Clock-buffer area",
    "design__instance__area__class:clock_buffer",
    "um^2", 3
)

show_key(
    "Worst setup clock skew",
    "clock__skew__worst_setup", "ns"
)

show_key(
    "Worst hold clock skew",
    "clock__skew__worst_hold", "ns"
)

print("\nCTS LOG DIAGNOSTICS")

cts_lines = scan_logs(
    [r"CTS-0010", r"CTS-0018", r"CTS-0102"],
    ["cts"]
)

if cts_lines:
    for path, line in cts_lines:
        print(f"[{path.name}] {line}")
else:
    print("No matching CTS log lines found.")

print("\nNOTE: CTS-created buffers and final clock-buffer")
print("instances are different measurements. Do not add them together.")


# ------------------------------------------------------------
# 7. Electrical violations
# ------------------------------------------------------------

section("7. ELECTRICAL / DESIGN VIOLATIONS")

show_key(
    "Max slew violations (aggregate)",
    "design__max_slew_violation__count", "", 0
)

show_key(
    "Max fanout violations (aggregate)",
    "design__max_fanout_violation__count", "", 0
)

show_key(
    "Max capacitance violations (aggregate)",
    "design__max_cap_violation__count", "", 0
)


# ------------------------------------------------------------
# 8. Routing
# ------------------------------------------------------------

section("8. ROUTING METRICS")

show_key(
    "Detailed-route signal wirelength",
    "route__wirelength", "um", 3
)

show_key(
    "Estimated route wirelength",
    "route__wirelength__estimated", "um", 3
)

show_key(
    "Global-route wirelength",
    "global_route__wirelength", "um", 3
)

show_key(
    "Final routing DRC errors",
    "route__drc_errors", "", 0
)

print("\nDETAILED ROUTING ITERATION HISTORY")

iterations = sorted(
    [
        key for key in METRICS
        if key.startswith("route__drc_errors__iter:")
    ],
    key=lambda key: int(key.rsplit(":", 1)[1])
)

if iterations:
    print(f"{'Iteration':>12s} {'DRC errors':>15s} {'Wirelength (um)':>20s}")

    for drc_key in iterations:
        iteration = drc_key.rsplit(":", 1)[1]
        wire_key = "route__wirelength__iter:" + iteration

        drc = METRICS[drc_key]
        wire = metric(wire_key)

        wire_str = "N/A" if wire is None else f"{wire:,.3f}"

        print(f"{iteration:>12s} {drc:>15} {wire_str:>20s}")
else:
    print("No per-iteration routing metrics found.")

print("\nDETAILED ROUTING LOG DIAGNOSTICS")

route_lines = scan_logs(
    [r"DRT-0199"],
    ["detailedrouting"]
)

if route_lines:
    for path, line in route_lines:
        print(f"[{path.name}] {line}")
else:
    print("No DRT-0199 lines found.")


# ------------------------------------------------------------
# 9. Physical signoff
# ------------------------------------------------------------

section("9. PHYSICAL SIGNOFF")

signoff_metrics = [
    ("Routing DRC errors", "route__drc_errors"),
    ("Magic DRC errors", "magic__drc_error__count"),
    ("KLayout DRC errors", "klayout__drc_error__count"),
    ("LVS errors", "design__lvs_error__count"),
    ("Antenna violating nets", "antenna__violating__nets"),
    ("Power-grid violations", "design__power_grid_violation__count"),
]

for label, key in signoff_metrics:
    show_key(label, key, "", 0)


# ------------------------------------------------------------
# 10. Power
# ------------------------------------------------------------

section("10. POWER ESTIMATES")

power_metrics = [
    ("Internal power", "power__internal__total"),
    ("Switching power", "power__switching__total"),
    ("Leakage power", "power__leakage__total"),
    ("Total power", "power__total"),
]

for label, key in power_metrics:
    value = metric(key)

    # LibreLane power metrics in this run are in watts.
    if value is None:
        show(label, None)
    else:
        show(label, value * 1000.0, "mW", 6)
        print(f"    Source: {key} (W converted to mW)")

print("\nCaution: reported flow power is not automatically")
print("a workload-validated power measurement. Check activity annotation.")


# ------------------------------------------------------------
# 11. Baseline summary
# ------------------------------------------------------------

section("11. BASELINE SUMMARY")

summary = [
    ("Standalone Yosys mapped area (um^2)", yosys_area),
    ("Final physical std-cell area (um^2)",
     metric("design__instance__area__stdcell")),
    ("Die area (um^2)", metric("design__die__area")),
    ("Core area (um^2)", metric("design__core__area")),
    ("Actual utilization (%)",
     actual_util * 100.0 if actual_util is not None else None),
    ("Configured utilization target (%)", target_util),
    ("Clock period constraint (ns)", clock_period),
    ("Worst setup WNS (ns)", metric("timing__setup__ws")),
    ("Setup TNS (ns)", metric("timing__setup__tns")),
    ("Worst hold WNS (ns)", metric("timing__hold__ws")),
    ("Final clock buffers",
     metric("design__instance__count__class:clock_buffer")),
    ("Timing-repair buffers",
     metric("design__instance__count__class:timing_repair_buffer")),
    ("Signal wirelength (um)", metric("route__wirelength")),
    ("Routing DRC", metric("route__drc_errors")),
    ("Total reported power (mW)",
     metric("power__total") * 1000.0
     if metric("power__total") is not None else None),
]

for label, value in summary:
    show(label, value)

section("EXTRACTION COMPLETE")

print("All values above are taken from the listed source files.")
print("NOT FOUND means the exact metric was absent.")
print("Do not replace missing values with zero.")
