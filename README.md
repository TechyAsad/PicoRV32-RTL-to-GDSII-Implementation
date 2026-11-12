# PicoRV32 RTL-to-GDSII \| Physical Design & PPA Optimization

**RTL-to-GDSII implementation and physical-design characterization of
the PicoRV32 RISC-V processor using LibreLane, OpenROAD, Yosys, OpenSTA
and the Sky130 PDK.**

This project explores the physical implementation of an existing RISC-V
processor, with an emphasis on understanding how floorplan utilization
and timing constraints influence post-route performance. Multiple
implementation experiments were conducted to evaluate timing, area,
buffering, routing and power trade-offs.

## Project Highlights

-   Complete **RTL-to-GDSII implementation** of PicoRV32 using the
    LibreLane flow.
-   Conducted floorplan utilization experiments at **30%, 35% and 40%**.
-   Achieved a **34.4% improvement in setup WNS** and a **67.3%
    reduction in TNS magnitude** at 30% utilization compared with the
    baseline.
-   Reduced routed signal wirelength by **1.3%** in the 30% utilization
    experiment.
-   Investigated reset input-delay sensitivity, reducing reported setup
    violations by **97.6%** in a separate diagnostic experiment.
-   Achieved **zero final routing DRC violations and zero LVS errors**
    across the evaluated runs.

## Design Flow & Technology Stack

  Category                  Tools / Technology
  ------------------------- ---------------------------
  Processor RTL             PicoRV32 (RISC-V)
  RTL synthesis             Yosys
  Physical implementation   OpenROAD
  Timing analysis           OpenSTA
  RTL-to-GDSII flow         LibreLane v3.0.16
  Process Design Kit        Sky130
  Design format             Verilog, DEF, SPEF, GDSII
  Constraints               SDC

### RTL-to-GDSII Implementation Flow

The processor was taken through the complete implementation flow:

1.  **RTL elaboration and synthesis:** Logic synthesis and technology
    mapping using Yosys.
2.  **Floorplanning:** Core sizing, utilization configuration and
    initial physical-design setup.
3.  **Placement:** Global placement, design repair and detailed
    placement.
4.  **Clock Tree Synthesis (CTS):** Clock-tree construction and clock
    distribution.
5.  **Timing optimization:** Post-CTS and post-global-route timing
    repair.
6.  **Global and detailed routing:** Signal routing and physical
    connectivity implementation.
7.  **Signoff checks:** DRC, LVS, antenna and final timing analysis.
8.  **GDSII generation:** Generation of the final layout database.

## Optimization Experiments

Three experiments were performed to investigate physical-design
trade-offs.

### 1. Floorplan Utilization Sweep

The configured floorplan utilization was varied while retaining the
original timing constraints.

  Parameter              Baseline   Experiment A   Experiment B
  -------------------- ---------- -------------- --------------
  Target utilization          35%            30%            40%
  Reset input delay        4.8 ns         4.8 ns         4.8 ns

The 30% utilization configuration provided the best timing and routing
results among these three implementations.

### 2. Reset Input-Delay Sensitivity Analysis

A separate diagnostic experiment changed only the reset input-delay
constraint from **4.8 ns to 0 ns**, keeping the baseline utilization
configuration.

The purpose was to investigate the sensitivity of setup timing to the
reset input timing assumption and understand its contribution to the
reported timing violations.

**Important:** This is a constraint-sensitivity experiment, not a
validated hardware timing optimization. The 0 ns input delay is not
assumed to represent the actual reset interface timing requirement.

### 3. PPA and Physical Metric Evaluation

The implementations were compared using:

-   Worst Negative Slack (WNS) and Total Negative Slack (TNS).
-   Setup and hold violation counts.
-   Standard-cell area and core area.
-   Actual floorplan utilization.
-   Timing-repair buffer count.
-   Routed signal wirelength.
-   Estimated power.
-   Final routing DRC and LVS results.

## Experimental Results

### Overall Comparison

  Metric                       Baseline 35%        Reset0        Util30     Util40
  -------------------------- -------------- ------------- ------------- ----------
  Reset input delay (ns)                4.8             0           4.8        4.8
  Setup WNS (ns)                     -4.020    **-1.011**        -2.639     -2.985
  Setup TNS (ns)                   -803.922   **-10.209**      -262.589   -291.576
  Setup violations                    1,451        **35**           634        658
  Hold WNS (ns)                      0.1063        0.1061         0.888      0.873
  Hold violations                         0             0             0          0
  Standard-cell area (µm²)          133,353       133,368       133,722    132,432
  Core area (µm²)                   251,631       251,631       294,056    221,436
  Actual utilization                 53.00%        53.00%        45.48%     59.81%
  Timing-repair buffers               3,570         3,572         3,537      3,514
  Signal wirelength (µm)            470,363       469,909   **464,155**    497,525
  Estimated power (mW)               11.387        11.376    **11.257**     11.516
  Final routing DRC                       0             0             0          0
  LVS errors                              0             0             0          0

*Setup violation counts are aggregate counts across timing corners, not
unique violating paths. Power values are flow estimates and depend on
activity assumptions and annotation.*

### Key Findings

**30% Utilization --- Best Timing/Routing Trade-off**

Compared with the 35% baseline:

-   Setup WNS improved from -4.020 ns to -2.639 ns (**34.4%
    improvement**).
-   TNS magnitude decreased by **67.3%**.
-   Signal wirelength decreased by **1.3%**.
-   Estimated power decreased from 11.387 mW to 11.257 mW.

**40% Utilization --- Area-Oriented Alternative**

-   Achieved the smallest core area of **221,436 µm²**.
-   Achieved the smallest standard-cell area of **132,432 µm²**.
-   However, signal wirelength increased to **497,525 µm**, and timing
    was inferior to the 30% configuration.

**Reset Input-Delay Sensitivity --- Diagnostic Result**

-   Setup violations decreased from 1,451 to 35 (**97.6% reduction**).
-   Setup WNS improved from -4.020 ns to -1.011 ns.
-   TNS magnitude decreased by approximately **98.7%**.

This experiment highlights the importance of understanding input timing
assumptions before interpreting STA results or claiming timing closure.

## Critical-Path Investigation

The baseline worst-case setup path was analyzed using the maximum-delay
timing report at the `max_ss_100C_1v60` corner.

Key observations:

-   Worst setup slack: **-4.020 ns**.
-   Startpoint: `resetn` input port.
-   Endpoint: `_10921_`, mapped to a D flip-flop associated with
    `cpuregs[5][9]`.
-   The path included significant delay from
    `sky130_fd_sc_hd__clkdlybuf4s25_1` cells.
-   Standard-cell delay dominated the reported path, while interconnect
    delay contributed comparatively little.

The investigation also examined the post-global-placement design-repair
stage, where a substantial number of delay buffers first appeared.

This helped distinguish between synthesis-level logic and
physical-design repair effects when interpreting the critical path.

## Repository Structure

``` text
.
├── config.json
├── config_util30.json
├── config_util40.json
├── config_reset0.json
├── src/
│   └── picorv32.v
├── scripts/
│   └── extract_ppa.py
├── sdc/
│   └── diagnostic_reset0/
│       ├── pnr.sdc
│       └── signoff.sdc
└── runs/
    ├── good/
    ├── reset0/
    ├── util30/
    └── util40/
```

*Generated run directories may be excluded from Git due to their size.
The configuration files, source RTL and analysis scripts are the primary
reproducibility artifacts.*

## Running the Flow

Install LibreLane and configure the required Sky130 PDK environment.

Run the baseline implementation:

``` bash
librelane config.json --run-tag good
```

Run the utilization experiments:

``` bash
librelane config_util30.json --run-tag util30

librelane config_util40.json --run-tag util40
```

Run the PPA extraction script:

``` bash
python3 scripts/extract_ppa.py runs/good --config config.json

python3 scripts/extract_ppa.py runs/util30 --config config_util30.json

python3 scripts/extract_ppa.py runs/util40 --config config_util40.json
```

The reset0 experiment uses separate PNR and signoff SDC files to
override only the reset input-delay constraint.

## Engineering Takeaways

This project provided practical exposure to:

-   RTL synthesis and standard-cell technology mapping.
-   Floorplan utilization and core-area trade-offs.
-   Placement-driven design repair and buffering.
-   Clock-tree synthesis and timing optimization.
-   Static timing analysis across process-voltage-temperature corners.
-   Setup/hold analysis and timing-constraint sensitivity.
-   Global and detailed routing metrics.
-   Physical verification through DRC and LVS.
-   PPA characterization and experiment-based optimization.

## Conclusion

The experiments demonstrate that physical-design performance is
influenced not only by the synthesized logic but also by floorplan
density, timing constraints and implementation-stage optimization.

Among the three implementations using the original timing constraints,
**30% target utilization provided the best observed timing and routing
trade-off**, while 40% achieved the smallest core area.

The project emphasizes data-driven physical-design analysis,
timing-report interpretation and measurable PPA characterization rather
than treating RTL-to-GDSII as a black-box flow.
