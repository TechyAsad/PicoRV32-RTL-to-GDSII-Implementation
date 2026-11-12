
set pdk [expr {[info exists ::env(PDK_ROOT)] && $::env(PDK_ROOT) ne "" ? $::env(PDK_ROOT) : "$::env(HOME)/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71"}]

# Detect if sky130A is nested or direct parent
if {[file isdirectory $pdk/sky130A]} {
    set pdk_base "$pdk/sky130A"
} else {
    set pdk_base "$pdk"
}

puts "Using verified PDK base path: $pdk_base"

# Add standard cell layout search paths to Magic's internal path
path + "$pdk_base/libs.ref/sky130_fd_sc_hd/mag"

# Read tech LEF and standard cell LEF files
if {[catch {lef read $pdk_base/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__nom.tlef} err]} {
    puts "Warning: Could not read tech LEF: $err"
}
if {[catch {lef read $pdk_base/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef} err]} {
    puts "Warning: Could not read cell LEF: $err"
}

if {[info exists ::env(EXTRA_LEF)]} { catch {lef read $::env(EXTRA_LEF)} }

# Read layout geometry
def read $::env(DEF)
load [file rootname [file tail $::env(DEF)]]
select top cell
puts "Loaded $::env(DEF): [llength [cellname list children [cellname list self]]] different cell types"

