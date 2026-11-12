#!/usr/bin/env bash
# Synthesize picorv32 by hand with Yosys (run inside the LibreLane shell).
set -e
mkdir -p out
PDK_ROOT=${PDK_ROOT:-$HOME/.ciel}
LIB=$PDK_ROOT/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
if [ ! -f "$LIB" ]; then echo "Liberty file not found: $LIB (run the smoke test first)"; exit 1; fi

echo "=================== PART 1: generic synthesis ==================="
yosys -q -p "read_verilog src/picorv32.v; synth -top picorv32 -flatten; tee -o out/stat_generic.txt stat"
tail -n 40 out/stat_generic.txt

echo
echo "=================== PART 2: mapped to Sky130 cells ==================="
yosys -p "read_liberty -lib $LIB; read_verilog src/picorv32.v; hierarchy -check -top picorv32; \
synth -top picorv32 -flatten; dfflibmap -liberty $LIB; abc -liberty $LIB; \
opt_clean -purge; tee -o out/stat_sky130.txt stat -liberty $LIB; \
tee -o out/check.txt check; write_verilog -noattr out/picorv32_yosys.v" > out/yosys.log

tail -n 60 out/stat_sky130.txt
echo
echo "Flip-flops: $(grep -cE 'sky130_fd_sc_hd__e?df' out/picorv32_yosys.v)"
grep -oE 'sky130_fd_sc_hd__e?df[a-z0-9_]+' out/picorv32_yosys.v | sort | uniq -c
echo "Design check: $(grep 'Found and reported' out/check.txt)"
