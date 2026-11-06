# Reference oracle for drn2graph.py.
#
# Runs DRAKON Editor's own geometry-to-graph pipeline (graph2.tcl, auto.tcl)
# and its DrakonTech exporter (generators/drakon_tech.tcl, convert_diagram)
# on every diagram of one .drn file, and prints one JSON object per line:
#   {"diagram_id": N, "name": "...", "is_drakon": true|false,
#    "errors": [{"items": "...", "message": "..."}], "exception": "...",
#    "drakon": { ...widget/DrakonTech JSON... } }
#
# Unlike `drakon_gen.tcl -dt 1`, a failing diagram does not abort the file.
#
# Usage: tclsh drn_reference.tcl DRAKON_EDITOR_DIR FILE.drn
# Needs: tcl8.6, tcllib (json::write), libsqlite3-tcl.

set script_path [ file normalize [ lindex $argv 0 ] ]
set drn_file [ file normalize [ lindex $argv 1 ] ]

package require msgcat
package require json::write
namespace import ::msgcat::mc

foreach script {
	scripts/art.tcl scripts/utils.tcl scripts/generators.tcl scripts/graph.tcl
	scripts/auto.tcl scripts/model.tcl scripts/dedit.tcl scripts/back.tcl
	scripts/version.tcl scripts/search.tcl scripts/colors.tcl scripts/graph2.tcl
	scripts/icon.links.tcl scripts/newfor.tcl scripts/highlight.tcl
	structure/struct.tcl structure/tables.tcl structure/tables_tcl.tcl
	structure/tables_cs.tcl structure/tables_c.tcl
} {
	source [ file join $script_path $script ]
}

load_sqlite
load_generators

namespace eval mw {
	proc set_status { ignored } { }
}

json::write indented 0
json::write aligned 0
fconfigure stdout -encoding utf-8

# Very old .drn files have no tree_nodes table; mwc::is_drakon then fails.
# Treat such diagrams as DRAKON diagrams, which is what the editor shows.
proc safe_is_drakon { diagram_id } {
	if { [ catch { set result [ mwc::is_drakon $diagram_id ] } ] } {
		return 1
	}
	return $result
}

proc emit { diagram_id name is_drakon errors exception drakon } {
	set errs {}
	foreach e $errors {
		lassign $e items message
		lappend errs [ json::write object items [ json::write string $items ] message [ json::write string $message ] ]
	}
	set parts [ list diagram_id $diagram_id name [ json::write string $name ] \
		is_drakon [ expr { $is_drakon ? "true" : "false" } ] \
		errors [ json::write array {*}$errs ] ]
	if { $exception != "" } {
		lappend parts exception [ json::write string $exception ]
	}
	if { $drakon != "" } {
		lappend parts drakon $drakon
	}
	puts [ json::write object {*}$parts ]
}

mod::close db
set result [ mod::open db $drn_file drakon ]
if { [ lindex $result 1 ] != "" } {
	puts stderr [ lindex $result 1 ]
	exit 1
}
mwc::init db
newfor::clear

set diagrams [ db eval { select diagram_id, name from diagrams order by diagram_id } ]
foreach { diagram_id name } $diagrams {
	set is_drakon [ safe_is_drakon $diagram_id ]
	set exception ""
	set drakon ""
	if { [ catch {
		graph::copy_from db
		graph::p.do_build_graph $diagram_id
		if { $is_drakon && ![ graph::p.errors $diagram_id ] } {
			graph::p.do_extract_auto $diagram_id
		}
	} err ] } {
		set exception $err
	}
	set errors [ gdb eval {
		select items, message from errors
		where diagram_id = :diagram_id
		order by items, message } ]
	set error_pairs {}
	foreach { items message } $errors {
		lappend error_pairs [ list $items $message ]
	}
	if { $is_drakon && $exception == "" && [ llength $error_pairs ] == 0 } {
		if { [ catch {
			set drakon [ gen_drakon_tech::convert_diagram $name $diagram_id 0 ]
		} err ] } {
			set exception $err
		}
	}
	emit $diagram_id $name $is_drakon $error_pairs $exception $drakon
}
