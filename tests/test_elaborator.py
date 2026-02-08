"""
Tests for AST → Netlist elaboration.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate, ElaborationError
from fpga_synth.ir.types import CellOp


def test_simple_module():
    """Test: Elaborate simple empty module"""
    verilog = """
    module test;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    assert netlist.name == "test"
    assert len(netlist.cells) == 0
    print("✓ test_simple_module")


def test_module_with_ports():
    """Test: Elaborate module with I/O ports"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire c
    );
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    assert netlist.name == "test"
    assert len(netlist.inputs) == 2
    assert len(netlist.outputs) == 1
    assert "a" in netlist.inputs
    assert "b" in netlist.inputs
    assert "c" in netlist.outputs

    print("✓ test_module_with_ports")


def test_simple_assign():
    """Test: Elaborate simple continuous assignment"""
    verilog = """
    module test;
        wire a;
        wire b;
        assign b = a;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have 2 nets (a and b)
    assert len(netlist.nets) >= 2

    # Net 'b' should be driven by net 'a'
    # (In reality, since b = a, the elaborator connects them)
    print("✓ test_simple_assign")


def test_and_gate():
    """Test: Elaborate AND operation"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire c
    );
        assign c = a & b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have an AND cell
    and_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.AND]
    assert len(and_cells) >= 1

    and_cell = and_cells[0]
    assert "A" in and_cell.inputs
    assert "B" in and_cell.inputs
    assert "Y" in and_cell.outputs

    print("✓ test_and_gate")


def test_or_gate():
    """Test: Elaborate OR operation"""
    verilog = """
    module test;
        wire a;
        wire b;
        wire c;
        assign c = a | b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    or_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.OR]
    assert len(or_cells) >= 1

    print("✓ test_or_gate")


def test_multiple_operations():
    """Test: Elaborate multiple operations"""
    verilog = """
    module test(
        input wire a,
        input wire b,
        output wire c
    );
        wire and_result;
        assign and_result = a & b;
        assign c = and_result | a;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have AND and OR cells
    and_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.AND]
    or_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.OR]

    assert len(and_cells) >= 1
    assert len(or_cells) >= 1

    print("✓ test_multiple_operations")


def test_const_value():
    """Test: Elaborate constant values"""
    verilog = """
    module test;
        wire result;
        assign result = 1;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should have a CONST cell
    const_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.CONST]
    assert len(const_cells) >= 1

    const_cell = const_cells[0]
    assert "value" in const_cell.attributes
    assert const_cell.attributes["value"] == 1

    print("✓ test_const_value")


def test_not_gate():
    """Test: Elaborate NOT operation"""
    verilog = """
    module test;
        wire a;
        wire b;
        assign b = ~a;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    not_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.NOT]
    assert len(not_cells) >= 1

    print("✓ test_not_gate")


def test_mux():
    """Test: Elaborate ternary (MUX) operation"""
    verilog = """
    module test;
        wire sel;
        wire a;
        wire b;
        wire out;
        assign out = sel ? a : b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    mux_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.MUX]
    assert len(mux_cells) >= 1

    mux_cell = mux_cells[0]
    assert "S" in mux_cell.inputs  # Select
    assert "A" in mux_cell.inputs  # False value
    assert "B" in mux_cell.inputs  # True value
    assert "Y" in mux_cell.outputs

    print("✓ test_mux")


def test_concat():
    """Test: Elaborate concatenation"""
    verilog = """
    module test;
        wire [3:0] a;
        wire [3:0] b;
        wire [7:0] c;
        assign c = {a, b};
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    concat_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.CONCAT]
    assert len(concat_cells) >= 1

    print("✓ test_concat")


def test_parameter_resolution():
    """Test: Resolve parameters"""
    verilog = """
    module test #(
        parameter WIDTH = 8
    )(
        input wire [WIDTH-1:0] data
    );
        localparam DEPTH = 16;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    # Should successfully elaborate without errors
    assert netlist.name == "test"
    assert len(netlist.inputs) == 1

    print("✓ test_parameter_resolution")


def test_arithmetic():
    """Test: Elaborate arithmetic operations"""
    verilog = """
    module test;
        wire [7:0] a;
        wire [7:0] b;
        wire [7:0] sum;
        wire [7:0] diff;
        assign sum = a + b;
        assign diff = a - b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    add_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.ADD]
    sub_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.SUB]

    assert len(add_cells) >= 1
    assert len(sub_cells) >= 1

    print("✓ test_arithmetic")


def test_comparison():
    """Test: Elaborate comparison operations"""
    verilog = """
    module test;
        wire [7:0] a;
        wire [7:0] b;
        wire eq;
        wire lt;
        assign eq = a == b;
        assign lt = a < b;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast)

    eq_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.EQ]
    lt_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.LT]

    assert len(eq_cells) >= 1
    assert len(lt_cells) >= 1

    print("✓ test_comparison")


def run_all():
    """Run all elaborator tests"""
    tests = [
        test_simple_module,
        test_module_with_ports,
        test_simple_assign,
        test_and_gate,
        test_or_gate,
        test_multiple_operations,
        test_const_value,
        test_not_gate,
        test_mux,
        test_concat,
        test_parameter_resolution,
        test_arithmetic,
        test_comparison,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"Elaborator Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running elaborator tests...\n")
    run_all()
