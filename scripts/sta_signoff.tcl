set run  runs/good
set pdk [expr {[info exists ::env(PDK_ROOT)] && $::env(PDK_ROOT) ne "" ? $::env(PDK_ROOT) : "$::env(HOME)/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71"}]
set lib  $pdk/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib

puts "== 1. Cell library (typical corner)"
read_liberty $lib
puts "== 2. Final routed netlist"
read_verilog $run/final/nl/picorv32.nl.v
link_design picorv32
puts "== 3. Wire parasitics (SPEF, nominal extraction)"
read_spef $run/final/spef/nom/picorv32.nom.spef
puts "== 4. The constraints LibreLane signed off with"
read_sdc $run/final/sdc/picorv32.sdc

puts "\n######## SETUP: slowest path ########"
report_checks -path_delay max -fields {slew cap fanout} -digits 3
puts "\n######## HOLD: fastest path ########"
report_checks -path_delay min -digits 3
puts "\n######## SUMMARY ########"
report_worst_slack -max -digits 3
report_worst_slack -min -digits 3
report_tns -digits 3
