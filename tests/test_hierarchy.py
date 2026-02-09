"""
Tests for module hierarchy and instantiation.
"""

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from fpga_synth.hdl_parser.parser import parse_verilog
from fpga_synth.hdl_parser.elaborator import elaborate
from fpga_synth.ir.types import CellOp


def test_simple_instantiation():
    """Test: Simple module instantiation"""
    verilog = """
    module inverter(
        input wire a,
        output wire b
    );
        assign b = ~a;
    endmodule

    module top(
        input wire x,
        output wire y
    );
        inverter inv1 (.a(x), .b(y));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="top")

    # Should have NOT cell from the inverter
    not_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.NOT]
    assert len(not_cells) >= 1

    # Cell should be prefixed with instance name
    assert any("inv1." in cell.name for cell in not_cells)

    print("✓ test_simple_instantiation")


def test_multiple_instances():
    """Test: Multiple instances of same module"""
    verilog = """
    module and_gate(
        input wire a,
        input wire b,
        output wire c
    );
        assign c = a & b;
    endmodule

    module top(
        input wire [3:0] in,
        output wire [1:0] out
    );
        and_gate g1 (.a(in[0]), .b(in[1]), .c(out[0]));
        and_gate g2 (.a(in[2]), .b(in[3]), .c(out[1]));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="top")

    # Should have 2 AND cells
    and_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.AND]
    assert len(and_cells) >= 2

    # Cells should be prefixed with different instance names
    cell_names = [cell.name for cell in and_cells]
    assert any("g1." in name for name in cell_names)
    assert any("g2." in name for name in cell_names)

    print("✓ test_multiple_instances")


def test_parameterized_instance():
    """Test: Module with parameter override"""
    verilog = """
    module adder #(
        parameter WIDTH = 8
    ) (
        input wire [WIDTH-1:0] a,
        input wire [WIDTH-1:0] b,
        output wire [WIDTH-1:0] sum
    );
        assign sum = a + b;
    endmodule

    module top(
        input wire [3:0] x,
        input wire [3:0] y,
        output wire [3:0] z
    );
        adder #(.WIDTH(4)) add4 (.a(x), .b(y), .sum(z));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="top")

    # Should have ADD cell
    add_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.ADD]
    assert len(add_cells) >= 1

    print("✓ test_parameterized_instance")


def test_nested_hierarchy():
    """Test: Nested module instantiation (2 levels)"""
    verilog = """
    module inverter(
        input wire a,
        output wire b
    );
        assign b = ~a;
    endmodule

    module buffer(
        input wire x,
        output wire y
    );
        wire tmp;
        inverter i1 (.a(x), .b(tmp));
        inverter i2 (.a(tmp), .b(y));
    endmodule

    module top(
        input wire in,
        output wire out
    );
        buffer buf (.x(in), .y(out));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="top")

    # Should have 2 NOT cells (from 2 inverters)
    not_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.NOT]
    assert len(not_cells) >= 2

    # Cells should have nested prefixes: buf.i1. and buf.i2.
    cell_names = [cell.name for cell in not_cells]
    assert any("buf." in name and "i1." in name for name in cell_names)
    assert any("buf." in name and "i2." in name for name in cell_names)

    print("✓ test_nested_hierarchy")


def test_hierarchical_with_logic():
    """Test: Module hierarchy with mixed logic"""
    verilog = """
    module half_adder(
        input wire a,
        input wire b,
        output wire sum,
        output wire carry
    );
        assign sum = a ^ b;
        assign carry = a & b;
    endmodule

    module full_adder(
        input wire a,
        input wire b,
        input wire cin,
        output wire sum,
        output wire cout
    );
        wire s1;
        wire c1;
        wire c2;
        half_adder ha1 (.a(a), .b(b), .sum(s1), .carry(c1));
        half_adder ha2 (.a(s1), .b(cin), .sum(sum), .carry(c2));
        assign cout = c1 | c2;
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="full_adder")

    # Should have XOR cells (2 from half_adders)
    xor_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.XOR]
    assert len(xor_cells) >= 2

    # Should have AND cells (2 from half_adders)
    and_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.AND]
    assert len(and_cells) >= 2

    # Should have OR cell (from full_adder)
    or_cells = [cell for cell in netlist.cells.values() if cell.op == CellOp.OR]
    assert len(or_cells) >= 1

    print("✓ test_hierarchical_with_logic")


def test_hierarchical_sequential():
    """Test: Module hierarchy with sequential logic"""
    verilog = """
    module dff(
        input wire clk,
        input wire d,
        output reg q
    );
        always @(posedge clk) begin
            q <= d;
        end
    endmodule

    module shift_reg(
        input wire clk,
        input wire din,
        output wire dout
    );
        wire q0;
        dff d0 (.clk(clk), .d(din), .q(q0));
        dff d1 (.clk(clk), .d(q0), .q(dout));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="shift_reg")

    # Should have 2 DFF cells
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]
    assert len(dff_cells) >= 2

    # Cells should be prefixed: d0. and d1.
    cell_names = [cell.name for cell in dff_cells]
    assert any("d0." in name for name in cell_names)
    assert any("d1." in name for name in cell_names)

    print("✓ test_hierarchical_sequential")


def test_array_of_instances():
    """Test: Multiple instances with different connections"""
    verilog = """
    module register(
        input wire clk,
        input wire d,
        output reg q
    );
        always @(posedge clk) begin
            q <= d;
        end
    endmodule

    module register_bank(
        input wire clk,
        input wire [3:0] din,
        output wire [3:0] dout
    );
        register r0 (.clk(clk), .d(din[0]), .q(dout[0]));
        register r1 (.clk(clk), .d(din[1]), .q(dout[1]));
        register r2 (.clk(clk), .d(din[2]), .q(dout[2]));
        register r3 (.clk(clk), .d(din[3]), .q(dout[3]));
    endmodule
    """
    ast = parse_verilog(verilog)
    netlist = elaborate(ast, top_module="register_bank")

    # Should have 4 DFF cells
    dff_cells = [cell for cell in netlist.cells.values()
                 if cell.op in (CellOp.DFF, CellOp.DFFR)]
    assert len(dff_cells) >= 4

    print("✓ test_array_of_instances")


def run_all():
    """Run all hierarchy tests"""
    tests = [
        test_simple_instantiation,
        test_multiple_instances,
        test_parameterized_instance,
        test_nested_hierarchy,
        test_hierarchical_with_logic,
        test_hierarchical_sequential,
        test_array_of_instances,
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
    print(f"Module Hierarchy Tests: {passed} passed, {failed} failed, {passed+failed} total")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    print("Running module hierarchy tests...\n")
    run_all()
