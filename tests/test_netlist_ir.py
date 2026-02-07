"""
Test suite for Lexer, Parser, AST, and Netlist IR.

Run with: python3 tests/test_netlist_ir.py
Or:       pytest tests/ -v
"""

import sys
import os
# Add parent of parent directory to path for fpga_synth imports
# This file is at: fpga_synth/tests/test_netlist_ir.py
# We need to add: /home/.../projects/ to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fpga_synth.hdl_parser.lexer import lex, LexerError
from fpga_synth.hdl_parser.parser import parse_verilog, Parser, ParseError
from fpga_synth.hdl_parser.ast_nodes import *
from fpga_synth.ir.types import CellOp, BitWidth, PortDir
from fpga_synth.ir.netlist import Netlist, Cell, Net, Pin, reset_ids


# ============================================================
# Lexer Tests
# ============================================================

def test_lex_basic_tokens():
    tokens = lex("module foo; endmodule")
    types = [t.type.name for t in tokens]
    assert types == ["MODULE", "IDENT", "SEMICOLON", "ENDMODULE", "EOF"]

def test_lex_numbers():
    tokens = lex("42 8'hFF 4'b1010 3'd7 16'h0")
    nums = [t.value for t in tokens if t.type.name == "NUMBER"]
    assert nums == ["42", "8'hFF", "4'b1010", "3'd7", "16'h0"]

def test_lex_operators():
    tokens = lex("a + b == c && d || e")
    types = [t.type.name for t in tokens if t.type.name != "EOF"]
    assert "PLUS" in types
    assert "EQ" in types
    assert "LAND" in types
    assert "LOR" in types

def test_lex_comments():
    tokens = lex("a // comment\nb /* block */ c")
    idents = [t.value for t in tokens if t.type.name == "IDENT"]
    assert idents == ["a", "b", "c"]

def test_lex_shifts():
    tokens = lex("a << b >> c >>> d")
    types = [t.type.name for t in tokens if t.type.name not in ("IDENT", "EOF")]
    assert types == ["LSHIFT", "RSHIFT", "ARSHIFT"]


# ============================================================
# Number Resolution Tests
# ============================================================

def test_resolve_unsized():
    val, width, signed = Parser.resolve_number("42")
    assert val == 42
    assert width == 32

def test_resolve_hex():
    val, width, signed = Parser.resolve_number("8'hFF")
    assert val == 255
    assert width == 8

def test_resolve_binary():
    val, width, signed = Parser.resolve_number("4'b1010")
    assert val == 10
    assert width == 4

def test_resolve_decimal():
    val, width, signed = Parser.resolve_number("3'd7")
    assert val == 7
    assert width == 3


# ============================================================
# Parser Tests
# ============================================================

SIMPLE_MODULE = """
module top(
    input clk,
    input rst,
    input [7:0] data_in,
    output reg [7:0] data_out
);
endmodule
"""

def test_parse_simple_module():
    sf = parse_verilog(SIMPLE_MODULE)
    assert len(sf.modules) == 1
    m = sf.modules[0]
    assert m.name == "top"
    assert len(m.ports) == 4
    assert m.ports[0].name == "clk"
    assert m.ports[0].direction == "input"
    assert m.ports[2].name == "data_in"
    assert m.ports[2].range is not None
    assert m.ports[3].net_type == "reg"

ASSIGN_MODULE = """
module adder(
    input [7:0] a,
    input [7:0] b,
    output [8:0] sum
);
    assign sum = a + b;
endmodule
"""

def test_parse_assign():
    sf = parse_verilog(ASSIGN_MODULE)
    m = sf.modules[0]
    assert m.name == "adder"
    assigns = [item for item in m.body if isinstance(item, ContinuousAssign)]
    assert len(assigns) == 1
    assert isinstance(assigns[0].rhs, BinaryOp)
    assert assigns[0].rhs.op == "+"

ALWAYS_MODULE = """
module counter(
    input clk,
    input rst,
    output reg [7:0] count
);
    always @(posedge clk) begin
        if (rst)
            count <= 8'h00;
        else
            count <= count + 8'd1;
    end
endmodule
"""

def test_parse_always():
    sf = parse_verilog(ALWAYS_MODULE)
    m = sf.modules[0]
    always_blocks = [item for item in m.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1
    ab = always_blocks[0]
    assert len(ab.sensitivity) == 1
    assert ab.sensitivity[0].edge == "posedge"
    assert len(ab.body) == 1
    assert isinstance(ab.body[0], IfStatement)

CASE_MODULE = """
module mux4(
    input [1:0] sel,
    input [7:0] a, b, c, d,
    output reg [7:0] y
);
    always @(*) begin
        case (sel)
            2'b00: y = a;
            2'b01: y = b;
            2'b10: y = c;
            default: y = d;
        endcase
    end
endmodule
"""

def test_parse_case():
    sf = parse_verilog(CASE_MODULE)
    m = sf.modules[0]
    always_blocks = [item for item in m.body if isinstance(item, AlwaysBlock)]
    assert len(always_blocks) == 1
    ab = always_blocks[0]
    assert ab.is_star
    assert isinstance(ab.body[0], CaseStatement)
    cs = ab.body[0]
    assert len(cs.items) == 3
    assert len(cs.default) == 1

TERNARY_ASSIGN = """
module terntest(
    input sel,
    input [3:0] a, b,
    output [3:0] y
);
    assign y = sel ? a : b;
endmodule
"""

def test_parse_ternary():
    sf = parse_verilog(TERNARY_ASSIGN)
    m = sf.modules[0]
    assigns = [item for item in m.body if isinstance(item, ContinuousAssign)]
    assert isinstance(assigns[0].rhs, TernaryOp)

CONCAT_MODULE = """
module conctest(
    input [3:0] a,
    input [3:0] b,
    output [7:0] y
);
    assign y = {a, b};
endmodule
"""

def test_parse_concat():
    sf = parse_verilog(CONCAT_MODULE)
    m = sf.modules[0]
    assigns = [item for item in m.body if isinstance(item, ContinuousAssign)]
    assert isinstance(assigns[0].rhs, Concat)
    assert len(assigns[0].rhs.parts) == 2

INSTANTIATION_MODULE = """
module top(
    input clk,
    input [7:0] a, b,
    output [7:0] sum
);
    adder #(.WIDTH(8)) u_add (
        .a(a),
        .b(b),
        .sum(sum)
    );
endmodule
"""

def test_parse_instantiation():
    sf = parse_verilog(INSTANTIATION_MODULE)
    m = sf.modules[0]
    insts = [item for item in m.body if isinstance(item, ModuleInstance)]
    assert len(insts) == 1
    mi = insts[0]
    assert mi.module_name == "adder"
    assert mi.instance_name == "u_add"
    assert len(mi.params) == 1
    assert mi.params[0].port_name == "WIDTH"
    assert len(mi.ports) == 3

PARAM_MODULE = """
module paramtest #(
    parameter WIDTH = 8,
    parameter DEPTH = 4
)(
    input [WIDTH-1:0] data_in,
    output [WIDTH-1:0] data_out
);
    localparam TOTAL = WIDTH * DEPTH;
    assign data_out = data_in;
endmodule
"""

def test_parse_parameters():
    sf = parse_verilog(PARAM_MODULE)
    m = sf.modules[0]
    assert len(m.params) >= 2
    assert m.params[0].name == "WIDTH"
    assert m.params[1].name == "DEPTH"


# ============================================================
# Netlist IR Tests
# ============================================================

def test_netlist_create_and_connect():
    reset_ids()
    nl = Netlist("test")
    
    # Create a simple: input A -> AND -> output Y
    inp_a = nl.add_module_input("A", BitWidth(0))
    inp_b = nl.add_module_input("B", BitWidth(0))
    
    and_cell = nl.create_cell(CellOp.AND, "and1",
                               input_names=["A", "B"],
                               width=BitWidth(0))
    
    out_y = nl.add_module_output("Y", BitWidth(0))
    
    nl.connect(inp_a.output, and_cell.inputs["A"])
    nl.connect(inp_b.output, and_cell.inputs["B"])
    nl.connect(and_cell.output, out_y.inputs["A"])
    
    assert len(nl.cells) == 4  # 2 inputs + AND + output
    assert len(nl.inputs) == 2
    assert len(nl.outputs) == 1

def test_topological_sort():
    reset_ids()
    nl = Netlist("topo_test")
    
    inp = nl.add_module_input("A", BitWidth(0))
    not_cell = nl.create_cell(CellOp.NOT, "inv", input_names=["A"], width=BitWidth(0))
    out = nl.add_module_output("Y", BitWidth(0))
    
    nl.connect(inp.output, not_cell.inputs["A"])
    nl.connect(not_cell.output, out.inputs["A"])
    
    order = nl.topological_sort()
    cell_names = [c.name for c in order]
    
    # Input must come before NOT, NOT before output
    assert cell_names.index("A") < cell_names.index("inv")
    assert cell_names.index("inv") < cell_names.index("Y")

def test_dead_logic_removal():
    reset_ids()
    nl = Netlist("dead_test")
    
    inp = nl.add_module_input("A", BitWidth(0))
    out = nl.add_module_output("Y", BitWidth(0))
    nl.connect(inp.output, out.inputs["A"])
    
    # Add a dead cell (not connected to output)
    dead = nl.create_cell(CellOp.NOT, "dead_inv", input_names=["A"], width=BitWidth(0))
    nl.connect(inp.output, dead.inputs["A"])
    
    assert len(nl.cells) == 3  # inp + out + dead_inv
    removed = nl.remove_dead_logic()
    assert removed == 1  # dead_inv removed
    assert "dead_inv" not in [c.name for c in nl.cells.values()]

def test_fanin_cone():
    reset_ids()
    nl = Netlist("cone_test")
    
    a = nl.add_module_input("A", BitWidth(0))
    b = nl.add_module_input("B", BitWidth(0))
    and1 = nl.create_cell(CellOp.AND, "and1", input_names=["A", "B"], width=BitWidth(0))
    not1 = nl.create_cell(CellOp.NOT, "not1", input_names=["A"], width=BitWidth(0))
    or1 = nl.create_cell(CellOp.OR, "or1", input_names=["A", "B"], width=BitWidth(0))
    out = nl.add_module_output("Y", BitWidth(0))
    
    nl.connect(a.output, and1.inputs["A"])
    nl.connect(b.output, and1.inputs["B"])
    nl.connect(and1.output, not1.inputs["A"])
    nl.connect(not1.output, or1.inputs["A"])
    nl.connect(b.output, or1.inputs["B"])
    nl.connect(or1.output, out.inputs["A"])
    
    cone = nl.fanin_cone(or1)
    cone_names = {c.name for c in cone}
    assert "or1" in cone_names
    assert "not1" in cone_names
    assert "and1" in cone_names
    assert "A" in cone_names
    assert "B" in cone_names

def test_combinational_loop_detection():
    reset_ids()
    nl = Netlist("loop_test")
    
    # Create a combinational loop: A -> B -> A (illegal!)
    a = nl.create_cell(CellOp.BUF, "a", input_names=["A"], width=BitWidth(0))
    b = nl.create_cell(CellOp.BUF, "b", input_names=["A"], width=BitWidth(0))
    
    nl.connect(a.output, b.inputs["A"])
    nl.connect(b.output, a.inputs["A"])
    
    loops = nl.detect_combinational_loops()
    assert len(loops) >= 1
    loop_names = {c.name for c in loops[0]}
    assert "a" in loop_names
    assert "b" in loop_names


# ============================================================
# Integration: Parse a complex module
# ============================================================

COMPLEX_MODULE = """
module alu #(
    parameter WIDTH = 8
)(
    input clk,
    input rst,
    input [WIDTH-1:0] a,
    input [WIDTH-1:0] b,
    input [2:0] op,
    output reg [WIDTH-1:0] result,
    output reg zero
);
    wire [WIDTH-1:0] sum;
    wire [WIDTH-1:0] diff;

    assign sum = a + b;
    assign diff = a - b;

    always @(posedge clk) begin
        if (rst) begin
            result <= 8'h00;
            zero <= 1'b0;
        end else begin
            case (op)
                3'd0: result <= sum;
                3'd1: result <= diff;
                3'd2: result <= a & b;
                3'd3: result <= a | b;
                3'd4: result <= a ^ b;
                3'd5: result <= ~a;
                3'd6: result <= a << b[2:0];
                default: result <= 8'h00;
            endcase
            zero <= (result == 8'h00) ? 1'b1 : 1'b0;
        end
    end
endmodule
"""

def test_parse_complex_alu():
    sf = parse_verilog(COMPLEX_MODULE)
    m = sf.modules[0]
    assert m.name == "alu"
    assert len(m.params) >= 1
    assert m.params[0].name == "WIDTH"
    
    # Check we got wire decls, assigns, and always block
    assigns = [item for item in m.body if isinstance(item, ContinuousAssign)]
    always_blocks = [item for item in m.body if isinstance(item, AlwaysBlock)]
    net_decls = [item for item in m.body if isinstance(item, NetDecl)]
    
    assert len(assigns) == 2      # sum, diff
    assert len(always_blocks) == 1
    assert len(net_decls) == 2     # sum, diff wire decls


# ============================================================
# Runner
# ============================================================

def run_all():
    tests = [
        (name, obj) for name, obj in globals().items()
        if name.startswith("test_") and callable(obj)
    ]
    
    passed = 0
    failed = 0
    
    for name, func in tests:
        try:
            func()
            print(f"  ✓ {name}")
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {passed+failed} total")
    
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running Chunk 1 tests...\n")
    run_all()
